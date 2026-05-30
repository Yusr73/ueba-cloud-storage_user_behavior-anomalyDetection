# UEBA Cloud Storage Platform

## Architecture

Route -> Controller -> Service -> Model -> Database

- routes: Endpoints HTTP
- controllers: Logique metier + logs CLUE
- services: Operations fichiers + detection
- models: Acces PostgreSQL
- utils: Logger, JWT, bcrypt

## Technologies

- Backend: FastAPI (Python 3.11)
- Database: PostgreSQL 15
- Frontend: HTML/CSS/JS + Jinja2
- Container: Docker Compose
- Auth: JWT (60 min)
- Hash: bcrypt
- Detection: Isolation Forest + Baseline probabiliste + Real-time sliding windows

## Logging CLUE

Table logs:
- id, time, uid, uid_type, type, params, is_local_ip, role, location

Types d'evenements:
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
- logs.json: backup temps reel

## Detection d'anomalies

### Phase 1: Detection Journaliere (Batch)

Deux methodes complementaires analysees chaque nuit a minuit:

**Baseline probabiliste**
- Calcule le 95eme percentile de chaque feature sur les donnees historiques
- Compare chaque jour avec cette baseline
- Un jour est flagge si une feature depasse son seuil
- Score = somme des depassements

**Isolation Forest**
- Modele non supervise base sur des arbres de decision aleatoires
- Contamination fixee a 5%
- Detecte les patterns structurellement anormaux
- Produit un score d'anomalie continu

**Regles de classification** (ordre de specificite):

- RANSOMWARE: pic simultane de file_written et unique_paths
- DATA_THEFT: pic simultane de file_accessed et unique_paths
- ACCOUNT_TAKEOVER: pic de login_attempt avec taux de succes inferieur a 50%
- BRUTE_FORCE: pic de login_attempt avec taux de succes a 0%
- DIRECTORY_TRAVERSAL: pic de unique_dir1 ou unique_dir2
- OFF_HOURS: pic de night_fraction
- MASS_ACTIVITY: pic de events_total uniquement

**Niveaux de confiance:**
- HIGH: Flagge par les deux methodes
- MEDIUM: Flagge uniquement par la baseline
- LOW: Flagge uniquement par Isolation Forest (investigation manuelle recommandee)

### Phase 2: Detection Temps Reel (Sliding Windows)

Detection instantanee sur fenetres glissantes, declenchee a chaque ecriture de log:

- Ransomware: file_written dans une fenetre d'une minute
- Mass Deletion: file_deleted dans une fenetre de cinq minutes
- Malicious Upload: file_created dans une fenetre de cinq minutes
- Account Takeover: file_accessed dans les soixante secondes apres un login_successful

**Multiplicateurs adaptatifs:**
- Utilisateur stable (Alice): seuil = historique_max x 2
- Utilisateur instable (Bob): seuil = historique_max x 3

Le maximum historique est calcule sur les donnees de la table des logs. Les alertes sont stockees dans une table avec une fenetre glissante de sept jours.

### Features Journalieres

- events_total: nombre total d'evenements
- active_hours: nombre d'heures differentes avec activite
- night_fraction: proportion d'evenements entre 0h et 5h
- unique_types: nombre de types d'evenements differents
- file_accessed: nombre d'acces fichiers
- file_written: nombre d'ecritures fichiers
- login_attempt: nombre de tentatives de connexion
- login_successful: nombre de connexions reussies
- login_success_rate: taux de reussite des connexions
- unique_paths: nombre de chemins fichiers differents
- path_depth_mean: profondeur moyenne des chemins
- unique_dir1: nombre de dossiers de niveau 1 differents
- unique_dir2: nombre de dossiers de niveau 2 differents
- path_reuse_ratio: ratio de reutilisation des chemins

### Base de donnees Detection

**daily_anomalies**
- Stocke les resultats de l'analyse quotidienne (minuit)
- Uniquement les jours anormaux
- Contient: date, user_id, scores, attack_type, confidence, analyst_notes

**rare_events_alerts**
- Stocke les alertes temps reel
- Fenetre glissante de sept jours
- Contient: user_id, event_type, count_value, threshold_value, multiplier

### Jobs Automatises

- Minuit: analyse de la veille (baseline + Isolation Forest)
- Trente secondes: rafraichissement du panneau Real-Time
- Quotidien: nettoyage des alertes de plus de sept jours

## Interface Admin Detection

Quatre panneaux par utilisateur:

1. Real-Time - Alertes fenetres glissantes (auto-refresh)
2. Today - Analyse cumulative de la journee (bouton manuel)
3. Yesterday - Resultat final de la veille
4. Historical - Historique des jours anormaux

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

Admin Detection (role admin requis):
- GET /admin/detection
- GET /admin/detection/history/{user}
- GET /admin/detection/yesterday/{user}
- GET /admin/detection/today/cumulative/{user}
- POST /admin/detection/today/trigger
- GET /admin/detection/realtime/alerts

Admin Database (role admin requis):
- GET /admin/database
- GET /admin/api/stats
- GET /admin/api/table/{name}
- DELETE /admin/api/table/{name}/{id}

## Securite

- Mots de passe: bcrypt avec sel
- Tokens JWT: localStorage + header Authorization
- Headers de securite: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- Roles: user (standard), admin (acces detection + database)

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
- Adminer: http://localhost:8080 (postgres / ueba_user / ueba_pass / ueba_db)

## Structure du projet

    ppp/
    ├── app/
    │   ├── controllers/      # Logique metier (AuthController, FileController)
    │   ├── services/         # Operations (FileService, DetectionService, RealtimeDetection)
    │   ├── models/           # Acces base de donnees (UserModel, FileModel)
    │   ├── routes/           # Endpoints HTTP (auth, files, admin, detection, web)
    │   ├── utils/            # Utilitaires (logger, security)
    │   ├── templates/        # Pages HTML Jinja2
    │   ├── scripts/          # Scripts utilitaires (import, simulation, backfill)
    │   ├── static/           # Fichiers statiques (images, CSS)
    │   ├── uploads/          # Fichiers utilisateurs (volume Docker)
    │   ├── logs/             # Logs JSON (volume Docker)
    │   ├── main.py           # Point d'entree FastAPI
    │   ├── config.py         # Configuration (base de donnees, secrets)
    │   ├── Dockerfile        # Build image Docker
    │   └── requirements.txt  # Dependances Python
    ├── logs/                 # Volume externe pour logs.json
    ├── uploads/              # Volume externe pour fichiers utilisateurs
    ├── docker-compose.yml    # Orchestration Docker
    └── README.md             # Documentation
## Scripts Disponibles

- import_clue_logs.py: Importe le dataset CLUE
- insert_notebook_results.py: Insere les resultats du notebook
- simulate_daily_attacks.py: Simule les attaques pour la detection journaliere
- test_realtime.py: Teste la detection temps reel
- get_thresholds.py: Affiche les seuils historiques
