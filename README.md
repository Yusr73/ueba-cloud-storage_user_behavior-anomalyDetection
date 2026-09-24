# UEBA Cloud Storage Platform

<img width="1891" height="814" alt="Dashboard" src="https://github.com/user-attachments/assets/acf41944-3065-4216-81f7-f0ee1390d0f1" />

## The problem

You cannot build a UEBA system on synthetic data.

Behavioral baselines require real, varied, long-duration activity. Generating fake user behavior produces fake anomalies, and a detector tuned on fabricated behavior detects nothing real. So this project was built in reverse: instead of inventing a system and bolting on logging, we started from a real dataset of CLUE-formatted audit logs (a Dropbox-replica's behavioral trace) and inferred the platform that would have produced them.

The cloud storage application exists because the logs describe it. The detection engine exists because the application needs real behavior to analyze.

## The constraint that shaped everything

The dataset contained raw logs only. It had:

- **No ground-truth labels.** No annotations saying "this day was an attack."
- **No peer groups.** No departments, roles, or behavioral clusters to compare users against.

These two absences determined the entire detection approach, and the reasoning matters more than the code:

**No labels means no supervised learning.** A classifier trained on our own rule-derived classifications would only reproduce those rules through a model. That is ML as decoration. We rejected it explicitly rather than dressing up a rule engine as machine learning.

**No peer groups means no peer-group comparison.** Peer-group detection — flagging behavior that is rare across similar users — is one of the strongest UEBA techniques. It was structurally unavailable. The data contained no group structure to exploit, and inventing pseudo-groups from two users would have been dishonest.

What remained viable was **per-user, unsupervised anomaly detection**: comparing each user against their own history. That is the strongest detector possible under these constraints, and it is what was built.

The dataset gave us two users, chosen for contrast:

- **alice** — stable, consistent activity profile
- **bob** — volatile, irregular activity profile

The contrast was not incidental. A detector that only sees one user cannot be tested for over-sensitivity. Comparing a stable user against a volatile one shows whether the detection logic picks up genuine anomalies or just noise.

## The platform

A functional cloud storage application: upload, view, edit, download, rename, share, soft-delete, restore, permanent delete. JWT authentication with role-based access. File version tracking with hashes. Security headers.

Every user action emits a **CLUE-format log entry** with 8 fields:

    id, time, uid, uid_type, type, params (JSONB), is_local_ip, role, location (JSONB)

Twelve event types are logged, from `file_accessed` and `file_written` through `login_attempt`, `login_successful`, and `user_created`. Logs are written to PostgreSQL for querying and mirrored to `logs.json` in real time.

<img width="1648" height="700" alt="CLUE logs" src="https://github.com/user-attachments/assets/d5eae21e-2a41-4dfd-ab28-65f08a4f28e9" />

## The detection layer

### Daily analysis

Raw logs are aggregated into **daily feature vectors** per user across 14 features spanning volume, temporal patterns, path diversity, file activity, authentication, and path reuse.

Two complementary detectors run every night at midnight:

**Probabilistic baseline.** Computes a p95 threshold per feature across the user's history. Each day is scored as the sum of excess ratios for every feature exceeding its threshold, and produces a `top_contributors` string explaining which features deviated and by how much.

**Isolation Forest.** 100 estimators, contamination 5%, on standardized feature vectors. Flags days whose feature *combinations* are structurally unusual, catching anomalies that no single feature threshold would reveal.

The two are complementary by design. The baseline catches explicit violations. Isolation Forest catches unusual combinations of individually normal features. A day flagged by both is HIGH confidence; a day flagged by the baseline alone is MEDIUM; a day flagged only by Isolation Forest is LOW and recommends manual investigation.

### Attack classification

Because the data has no labels, the step from "anomalous" to "what kind of attack" is inherently rule-based. This is not a shortcut — it is the state of the art for label-free detection. The classifier maps feature spikes to attack types in order of specificity:

- **RANSOMWARE** — simultaneous spike in `file_written` and `unique_paths`
- **DATA_THEFT** — simultaneous spike in `file_accessed` and `unique_paths`
- **ACCOUNT_TAKEOVER** — `login_attempt` spike with success rate below 50%
- **BRUTE_FORCE** — `login_attempt` spike with 0% success rate
- **BUSY_DAY** — `login_attempt` spike with 80%+ success rate
- **DIRECTORY_TRAVERSAL** — spike in `unique_dir1` or `unique_dir2`
- **OFF_HOURS** — spike in `night_fraction`
- **MASS_ACTIVITY** — spike in `events_total` alone

The **BUSY_DAY** class deserves a note. High login volume with high success rate is legitimate activity, not an attack. Without this class, the detector would mislabel ordinary busy days as brute force — one of the most common false positives in naive anomaly detection. Building a category for it means the system knows the difference between "unusual" and "hostile."

Before any flagged day is confirmed, verification functions cross-check it against the user's own historical median rather than a fixed threshold. A day is only confirmed if it is anomalous *relative to that user's own normal variation*.

<img width="1562" height="863" alt="Detection" src="https://github.com/user-attachments/assets/a67ca12f-7932-45d7-8a00-745152ff77d0" />

### Real-time detection

Alongside the nightly batch analysis, a real-time layer detects attacks as they happen using **sliding windows**, triggered on every log write:

- **Ransomware** — `file_written` events in a 60-second window (encryption is fast)
- **Mass Deletion** — `file_deleted` events in a 300-second window (deletion spreads over minutes)
- **Malicious Upload** — `file_created` events in a 300-second window
- **Account Takeover** — `file_accessed` events within 60 seconds of a `login_successful` (takeover happens immediately after login)

Window lengths were chosen by reasoning about attack mechanics, not by parameter search — there is no theoretically correct window, only windows that match the timescale of the behavior being detected.

Each window fires when the event count exceeds the user's historical maximum multiplied by a per-user multiplier (alice: ×2, bob: ×3). The historical maximum comes from the logs table; alerts are stored with a seven-day sliding retention.

<img width="1589" height="847" alt="Real-time panel" src="https://github.com/user-attachments/assets/1eba1b8f-82ff-4fea-97d9-dae7a9c7eec1" />

## Evaluation under no labels

Because the dataset has no ground truth, precision and recall cannot be reported honestly. Evaluation instead relies on:

- **Injection testing.** Six calibrated attack patterns (ransomware, data theft, account takeover, brute force, directory traversal, mass activity) are generated against the live system to verify each is detected.
- **Consistency analysis.** The same anomalies should be flagged across different contamination parameters.
- **Interpretability.** Every flagged day carries its `top_contributors`, explaining exactly why it was flagged.

This is weaker than supervised evaluation. It is also the only honest option given the data, and it is documented as such rather than papered over with metrics that would not mean anything.

## What this project demonstrates

- Full-stack engineering with clean layered architecture (routes → controllers → services → models) on FastAPI, PostgreSQL, Docker, and JWT
- Designing an unsupervised detection system that combines a probabilistic baseline with Isolation Forest, and reasoning about when each catches what
- Making methodological choices under real constraints — no labels, no peer groups — and refusing to fake what the data cannot support
- Distinguishing legitimate high-volume activity from attack behavior through an explicit false-positive class
- Building real-time detection with sliding windows and per-user adaptive thresholds on top of a batch pipeline

## Known limitations

- Sliding window state is in memory and lost on restart; production needs Redis
- Per-user multipliers are hardcoded rather than derived from each user's historical variance
- Attack classification is rule-based (a consequence of label-free data, not of method)
- No peer-group analysis (the dataset has no group structure)
- JWT stored in localStorage; production should use httpOnly cookies with CSRF protection
- No rate limiting on auth or upload endpoints
- `--reload` in the Dockerfile; production should use Gunicorn with Uvicorn workers
- Schema managed with `CREATE TABLE IF NOT EXISTS`; production should use Alembic migrations

## Running it

    docker compose up -d

- Application: http://localhost:8000
- API docs: http://localhost:8000/docs
- Adminer (database): http://localhost:8080

Demo accounts: `alice / password123`, `bob / password456`

## Method note

This project began with raw CLUE logs from a Dropbox-replica system and inferred the platform that would produce them. The platform was built to match that behavioral trace, and the detection layer was built on top. The logs are therefore not a side effect of the application — they are its starting point.
