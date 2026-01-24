import sqlite3

db_name = "game_records.db"
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# 1️⃣ Créer une nouvelle table temporaire avec map_id en TEXT
cursor.execute("""
    CREATE TABLE IF NOT EXISTS records_new (
        player_id INTEGER,
        map_id TEXT,
        score INTEGER DEFAULT 0,
        PRIMARY KEY (player_id, map_id),
        FOREIGN KEY (player_id) REFERENCES players(player_id)
    )
""")

# 2️⃣ Copier les données de l'ancienne table vers la nouvelle
cursor.execute("""
    INSERT INTO records_new (player_id, map_id, score)
    SELECT player_id, map_id, score FROM records
""")

# 3️⃣ Supprimer l'ancienne table
cursor.execute("DROP TABLE records")

# 4️⃣ Renommer la nouvelle table pour qu'elle devienne "records"
cursor.execute("ALTER TABLE records_new RENAME TO records")

conn.commit()
conn.close()

print("Table 'records' corrigée avec map_id en TEXT ✅")
