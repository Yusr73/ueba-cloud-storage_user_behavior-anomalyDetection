
                    UEBA CLOUD STORAGE PLATFORM


ARCHITECTURE

L'application suit une architecture MVC2 (Model-View-Controller) adaptee aux APIs:

Route (endpoint) → Controller (logique + logs) → Service (fichiers) → Model (BDD)

- routes/: Definissent les endpoints HTTP (ex: POST /login, GET /files/list)
- controllers/: Orchestrent les actions et appellent write_log()
- services/: Gerent les fichiers (upload, download, edition)
- models/: Accedent a PostgreSQL
- utils/: Contiennent logger.py (CLUE) et security.py (JWT)

Pourquoi?
- Separation claire: chaque couche a un role unique
- Reutilisable: les services n'ont pas besoin des routes
- Testable: on peut tester chaque composant isolement

TECHNOLOGIES

- FastAPI (Python 3.11): Framework asynchrone, auto-documentation /docs
- PostgreSQL 15: Stockage des utilisateurs, logs, metadonnees fichiers
- Docker Compose: Orchestration (API + PostgreSQL + Adminer)
- JWT: Authentification stateless (valide 60 minutes)
- SHA256: Hachage des mots de passe (pas de sel pour POC)

FONCTIONNALITES

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

LOGGING CLUE

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

12 types d'evenements CLUE et leur declenchement:

file_accessed
→ declenche quand: utilisateur voit OU telecharge un fichier
→ params contient: {"filename": "xxx", "action": "view" ou "download"}

file_written
→ declenche quand: utilisateur edite et sauvegarde un fichier texte
→ params contient: {"filename": "xxx", "action": "edit"}

file_created
→ declenche quand: utilisateur uploade un nouveau fichier (qui n'existait pas)
→ params contient: {"filename": "xxx", "size": 1234, "hash": "md5..."}

file_updated
→ declenche quand: utilisateur uploade un fichier qui remplace un existant
→ declenche aussi quand: utilisateur restaure un fichier depuis la corbeille
→ params contient: {"filename": "xxx", "action": "overwrite" ou "restored"}

file_deleted
→ declenche quand: utilisateur supprime un fichier (mettre a la corbeille)
→ params contient: {"filename": "xxx"}

deleted_from_trashbin
→ declenche quand: utilisateur supprime definitivement un fichier (vider corbeille)
→ params contient: {"filename": "xxx"}

file_renamed
→ declenche quand: utilisateur renomme un fichier
→ params contient: {"old_filename": "xxx", "new_filename": "yyy"}

shared_user
→ declenche quand: utilisateur genere un lien de partage pour un fichier
→ params contient: {"filename": "xxx", "share_token": "token16"}

login_attempt
→ declenche quand: utilisateur tente de se connecter (reussi ou echoue)
→ params contient: {"username": "xxx", "success": true/false}

login_successful
→ declenche quand: utilisateur se connecte avec succes
→ params contient: {"username": "xxx"}

logout_occured
→ declenche quand: utilisateur se deconnecte
→ params contient: {"username": "xxx"}

user_created
→ declenche quand: utilisateur cree un compte
→ params contient: {"username": "xxx", "email": "xxx"}

DOUBLE STOCKAGE DES LOGS

Chaque write_log() fait deux choses:
1. INSERT dans PostgreSQL (pour requeter facilement)
2. Append dans /app/logs/logs.json (pour backup et export SIEM)

Avantage: on peut faire des analyses SQL et aussi envoyer le fichier JSON a un outil externe.


================================================================================
