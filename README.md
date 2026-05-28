# UEBA CLOUD STORAGE PLATFORM

## Architecture
Route → Controller → Service → Model → Database

- routes: endpoints HTTP
- controllers: logique metier + logs
- services: operations fichiers
- models: acces base de donnees
- utils: logger CLUE, JWT, bcrypt

## Technologies
- FastAPI (Python 3.11)
- PostgreSQL 15
- Docker Compose
- JWT (60 minutes)
- bcrypt (mots de passe)

## Securite
- Mots de passe: bcrypt avec sel
- Tokens: localStorage + header Authorization
- Headers: X-Frame-Options, X-XSS-Protection

## Fonctionnalites
- Inscription / Connexion / Deconnexion
- Upload / Download / Visualisation
- Edition fichiers texte
- Renommage / Corbeille / Restauration
- Partage de fichiers
- Interface admin (statistiques, tables)

## Logging CLUE

8 colonnes: id, time, uid, uid_type, type, params, is_local_ip, role, location

12 evenements:
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

Double stockage: PostgreSQL + /app/logs/logs.json

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

Admin (role admin):
- GET /admin/database
- GET /admin/api/stats
- GET /admin/api/tables
- GET /admin/api/table/{name}
- DELETE /admin/api/table/{name}/{id}

## Commandes Docker

```powershell
docker compose up -d
docker compose down
docker logs ppp_api --tail 50
docker compose restart api
docker compose build api
