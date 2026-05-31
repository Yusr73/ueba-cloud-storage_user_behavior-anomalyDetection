import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import os

# Mapping des UIDs vers alice et bob
UID_MAPPING = {
    "spectacular-copper-cheetah-postman": "alice",
    "ready-silver-angelfish-quarryworker": "bob"
}

# Mapping des types d'événements CLUE vers ton format
# (déjà compatible, garde les mêmes noms)

def convert_to_log_format(event):
    """Convertit un événement CLUE au format de la table logs"""
    
    time_str = event.get("time", "")
    if time_str:
        # Convertir "2017-07-07T08:57:57Z" en datetime
        time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    else:
        time = datetime.now()
    
    uid = event.get("uid", "")
    uid_type = event.get("uidType", "name")
    
    # Renommer l'UID si nécessaire
    if uid in UID_MAPPING:
        uid = UID_MAPPING[uid]
        uid_type = "name"  # alice et bob sont des noms
    
    event_type = event.get("type", "")
    params = event.get("params", {})
    
    # is_local_ip : par défaut True pour les logs historiques
    is_local_ip = event.get("isLocalIP", True)
    if isinstance(is_local_ip, str):
        is_local_ip = is_local_ip.lower() == "true"
    
    role = event.get("role", None)
    location = event.get("location", None)
    
    return (time, uid, uid_type, event_type, json.dumps(params), is_local_ip, role, json.dumps(location) if location else None)

def import_clue_logs():
    """Importe les logs CLUE pour alice et bob dans PostgreSQL"""
    
    # Connexion à PostgreSQL
    conn = psycopg2.connect(
        host="postgres",
        database="ueba_db",
        user="ueba_user",
        password="ueba_pass"
    )
    cur = conn.cursor()
    
    # Vérifier si les logs existent déjà
    cur.execute("SELECT COUNT(*) FROM logs WHERE uid IN ('alice', 'bob')")
    count = cur.fetchone()[0]
    
    if count > 0:
        print(f"Des logs existent déjà pour alice/bob ({count} lignes).")
        response = input("Voulez-vous les supprimer avant d'importer ? (o/n): ")
        if response.lower() == 'o':
            cur.execute("DELETE FROM logs WHERE uid IN ('alice', 'bob')")
            conn.commit()
            print("Anciens logs supprimés.")
        else:
            print("Import annulé.")
            cur.close()
            conn.close()
            return
    
    print("Import des logs CLUE en cours...")
    
    file_path = "/app/clue_sample_1GB.jsonl"
    
    if not os.path.exists(file_path):
        print(f"Fichier non trouvé: {file_path}")
        cur.close()
        conn.close()
        return
    
    batch = []
    batch_size = 10000
    total = 0
    
    with open(file_path, 'r') as f:
        for line in f:
            try:
                event = json.loads(line)
                uid = event.get("uid", "")
                
                # Garder seulement les deux utilisateurs
                if uid not in UID_MAPPING:
                    continue
                
                log_tuple = convert_to_log_format(event)
                batch.append(log_tuple)
                total += 1
                
                if len(batch) >= batch_size:
                    execute_values(cur,
                        """INSERT INTO logs (time, uid, uid_type, type, params, is_local_ip, role, location)
                           VALUES %s""",
                        batch
                    )
                    conn.commit()
                    print(f"  Importé {total} lignes...")
                    batch = []
                    
            except Exception as e:
                print(f"Erreur sur une ligne: {e}")
                continue
        
        # Dernier batch
        if batch:
            execute_values(cur,
                """INSERT INTO logs (time, uid, uid_type, type, params, is_local_ip, role, location)
                   VALUES %s""",
                batch
            )
            conn.commit()
    
    print(f"Import terminé. {total} lignes insérées pour alice et bob.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    import_clue_logs()