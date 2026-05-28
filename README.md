# UEBA Cloud Storage Platform

## Architecture

Route → Controller → Service → Model → Database

- routes/ : Endpoints HTTP
- controllers/ : Logique metier + logs CLUE
- services/ : Operations fichiers + detection
- models/ : Acces PostgreSQL
- utils/ : Logger, JWT, bcrypt

## Technologies

- Backend: FastAPI (Python 3.11)
- Database: PostgreSQL 15
- Frontend: HTML/CSS/JS + Jinja2
- Container: Docker Compose
- Auth: JWT (60 min)
- Hash: bcrypt
- Detection: Isolation Forest + Baseline probabiliste

## Logging CLUE

Table logs (8 colonnes):
- id, time, uid, uid_type, type, params, is_local_ip, role, location

12 types d'evenements:
- file_accessed (voir/telecharger)
- file_written (editer/sauvegarder)
- file_created (nouveau fichier)
- file_updated (remplacer/restaurer)
- file_deleted (corbeille)
- deleted_from_trashbin (suppression definitive)
- file_renamed (renommer)
- shared_user (partager)
- login_attempt (tentative)
- login_successful (reussi)
- logout_occured (deconnexion)
- user_created (inscription)

Double stockage:
- PostgreSQL: requetes SQL
- logs.json: backup temps reel (dans ./logs/)

## Detection d'anomalies

Methodes:
- Baseline probabiliste (seuil p95, score = somme des depassements)
- Isolation Forest (contamination 5%)

Features journalieres:
- events_total, active_hours, night_fraction, unique_types
- file_events, login_attempt, login_successful, login_success_rate
- unique_paths, path_depth_mean, unique_dir1, unique_dir2, path_reuse_ratio

Classification:
- DATA_THEFT = file_events + unique_paths
- DIRECTORY_TRAVERSAL = unique_dir1 ou unique_dir2
- LOGIN_ACTIVITY = login_attempt
- OFF_HOURS = night_fraction
- BOT_OR_MASS_ACTIVITY = events_total + active_hours
- PATH_REUSE_ANOMALY = path_reuse_ratio seul

## API Endpoints

Authentification:
- POST /register
- POST /login
- POST /logout
- GET /me

Fichiers (JWT requis):
- POST /files/upload
- GET /files/list
- GET /files/view/{filename}
- POST /files/edit/{filename}
- GET /files/download/{filename}
- PUT /files/rename/{old}
- POST /files/{filename}/share
- DELETE /files/{filename}
- POST /files/{filename}/restore
- GET /files/trash

Admin (role admin requis):
- GET /admin/database
- GET /admin/detection
- GET /admin/detection/alice
- GET /admin/detection/bob
- GET /admin/api/stats
- GET /admin/api/tables
- GET /admin/api/table/{name}
- DELETE /admin/api/table/{name}/{id}

## Securite

- Mots de passe: bcrypt avec sel
- Tokens JWT: localStorage + header Authorization
- Headers: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection

Limitations (POC): Pas de HTTPS, pas de rate limiting, localStorage visible

## Commandes Docker

Demarrer: docker compose up -d
Arreter: docker compose down
Logs API: docker logs ppp_api --tail 50
Redemarrer API: docker compose restart api
Reconstruire: docker compose build api
Entrer PostgreSQL: docker exec -it ppp_postgres psql -U ueba_user -d ueba_db

## URLs

- Application: http://localhost:8000
- Documentation API: http://localhost:8000/docs
- Adminer (DB): http://localhost:8080 (postgres / ueba_user / ueba_pass / ueba_db)

## Structure du projet

ppp/
├── app/
│   ├── controllers/      # AuthController, FileController
│   ├── services/         # FileService, DetectionService
│   ├── models/           # UserModel, FileModel, database.py
│   ├── routes/           # auth_routes, file_routes, admin_routes, detection_routes, web_routes
│   ├── utils/            # logger.py, security.py
│   ├── templates/        # Pages HTML
│   ├── uploads/          # Fichiers utilisateurs
│   ├── logs/             # logs.json
│   ├── main.py
│   ├── config.py
│   ├── Dockerfile
│   └── requirements.txt
├── logs/                 # logs.json (volume local)
├── uploads/              # Fichiers utilisateurs (volume local)
├── docker-compose.yml
└── README.md