# UEBA Cloud Storage - Etat actuel du projet

## Conteneurs Docker

Trois conteneurs tournent en parallele :

- postgres (port 5432) : stocke les logs et les utilisateurs
- api (port 8000) : application FastAPI avec authentification et gestion des fichiers
- adminer (port 8080) : outil pour visualiser la base de donnees

## Ce qui est implemente

- Authentification JWT (register, login, logout)
- Upload / download / suppression de fichiers
- Logs au format CLUE (PostgreSQL + fichier JSON)
- Interface web (dashboard, login, register)

## Ce qui n'est pas encore integre a l'API

Le code de detection d'anomalies (notebook) n'est pas encore connecte. Il tourne independamment.

## Pour lancer

docker-compose up -d

## Pour tester

1. http://localhost:8000/register
2. Creer un compte (avec ou sans email)
3. Se connecter
4. Uploader un fichier
5. Le voir apparaitre dans "Mes fichiers"

## Logs

Les logs sont dans PostgreSQL (table logs) et dans app/logs/logs.json
