# UEBA CLOUD STORAGE PLATFORM

## ARCHITECTURE

L'application suit une architecture MVC2 (Model-View-Controller) adaptee aux APIs:

Route (endpoint) → Controller (logique + logs) → Service (fichiers) → Model (BDD)

- routes/: Definissent les endpoints HTTP (ex: POST /login, GET /files/list)
- controllers/: Orchestrent les actions et appellent write_log()
- services/: Gerent les fichiers (upload, download, edition)
- models/: Accedent a PostgreSQL
- utils/: Contiennent logger.py (CLUE) et security.py (JWT, bcrypt)

Pourquoi?
- Separation claire: chaque couche a un role unique
- Reutilisable: les services n'ont pas besoin des routes
- Testable: on peut tester chaque composant isolement

## TECHNOLOGIES

- FastAPI (Python 3.11): Framework asynchrone, auto-documentation /docs
- PostgreSQL 15: Stockage des utilisateurs, logs, metadonnees fichiers
- Docker Compose: Orchestration (API + PostgreSQL + Adminer)
- JWT: Authentification stateless (valide 60 minutes)
- bcrypt: Hachage des mots de passe avec sel (standard industriel)
- Cookies httpOnly: Stockage securise du token JWT

## SECURITE

### Mots de passe
- Hachage avec bcrypt (sel automatique, cout ajustable)
- Remplace SHA256 (trop rapide, sans sel)

### Tokens JWT
- Stockes dans cookies httpOnly (inaccessibles au JavaScript)
- Fallback vers header Authorization pour les requetes fetch
- Valides 60 minutes

### Headers de securite
- X-Frame-Options: DENY (anti-clickjacking)
- X-Content-Type-Options: nosniff (anti-MIME sniffing)
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin

### Limitations (pour POC)
- Pas de HTTPS (localhost)
- Pas de rate limiting
- Utilisation de localStorage en complement (pour compatibilite frontend)

## FONCTIONNALITES

Utilisateurs:
- Inscription / Connexion / Deconnexion
- Roles: user et admin

Fichiers:
- Upload (simple ou multiple)
- Download
- Visualisation en ligne (texte, images, PDF)
- Edition de fichiers texte (avec auto-save Ctrl+S)
- Renommage
- Corbeille (deplacer, restaurer, suppression definitive)
- Partage (generation de lien)

Admin:
- Interface web pour voir toutes les tables
- Statistiques (nombre d'enregistrements par table)
- Suppression d'enregistrements
- Verification du role cote JavaScript + API backend

## LOGGING CLUE

Format CLUE (Cloud Log UEBA) = standard pour detection d'anomalies.

8 colonnes obligatoires dans la table logs:

1. id          : Identifiant unique
2. time        : Horodatage UTC
3. uid         : Identifiant utilisateur (ex: "alice-6384e2b2")
4. uid_type    : Soit "uid" soit "name"
5. type        : Type d'evenement (voir ci-dessous)
6. params      : Details de l'action (JSON)
7. is_local_ip : IP interne ou externe? (true/false)
8. role        : Role de l'utilisateur ("user" ou "admin")
9. location    : Geolocalisation (JSON, pour UEBA)

### 12 types d'evenements CLUE

| evenement | declenchement |
|-----------|---------------|
| file_accessed | utilisateur voit OU telecharge un fichier |
| file_written | utilisateur edite et sauvegarde un fichier texte |
| file_created | utilisateur uploade un nouveau fichier |
| file_updated | upload remplace existant OU restauration depuis corbeille |
| file_deleted | utilisateur supprime un fichier (corbeille) |
| deleted_from_trashbin | suppression definitive depuis corbeille |
| file_renamed | utilisateur renomme un fichier |
| shared_user | utilisateur genere un lien de partage |
| login_attempt | tentative de connexion (reussie ou echouee) |
| login_successful | connexion reussie |
| logout_occured | deconnexion |
| user_created | creation de compte |

## DOUBLE STOCKAGE DES LOGS

Chaque write_log() fait deux choses:
1. INSERT dans PostgreSQL (pour requeter facilement)
2. Append dans /app/logs/logs.json (pour backup et export SIEM)

Avantage: analyses SQL + export vers outils externes

## API ENDPOINTS

### Authentification
- POST /register
- POST /login (retourne token + cookie httpOnly)
- POST /logout (supprime cookie)
- GET /me

### Fichiers (JWT requis)
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

### Admin (role admin requis)
- GET /admin/database (page HTML)
- GET /admin/api/stats
- GET /admin/api/tables
- GET /admin/api/table/{name}
- DELETE /admin/api/table/{name}/{id}

## DOCKER COMMANDES

Demarrer: docker compose up -d
Arreter: docker compose down
Logs API: docker logs ppp_api --tail 50
Entrer PostgreSQL: docker exec -it ppp_postgres psql -U ueba_user -d ueba_db
Redemarrer API: docker compose restart api
Reconstruire: docker compose build api

## URLS

- Application: http://localhost:8000
- Documentation API: http://localhost:8000/docs
- Adminer (interface DB): http://localhost:8080
  (System: PostgreSQL, Server: postgres, User: ueba_user, Password: ueba_pass, Database: ueba_db)

