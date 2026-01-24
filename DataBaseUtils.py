import sqlite3

class GameDatabase:
    def __init__(self, db_name="game_records.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
        # Index pour accélérer les counts et jointures
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_player_id ON records(player_id)")
        self.conn.commit()

    def _create_tables(self):
        # Table des joueurs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        """)
        # Table des records
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                player_id INTEGER,
                map_id TEXT,
                score INTEGER DEFAULT 0,
                PRIMARY KEY (player_id, map_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)
        self.conn.commit()

    # --------------------
    # Gestion des joueurs
    # --------------------
    def add_player(self, name):
        """Ajoute un joueur et retourne son ID. Si le joueur existe déjà, retourne son ID."""
        self.cursor.execute("SELECT player_id FROM players WHERE name = ?", (name,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        self.cursor.execute("INSERT INTO players (name) VALUES (?)", (name,))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_player_id(self, name):
        self.cursor.execute("SELECT player_id FROM players WHERE name = ?", (name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_player_name(self, player_id):
        self.cursor.execute("SELECT name FROM players WHERE player_id = ?", (player_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    # --------------------
    # Gestion des records
    # --------------------
    def set_record(self, player_identifier, map_id, score):
        player_id = self._resolve_player_id(player_identifier)
        if player_id is None:
            raise ValueError(f"Le joueur '{player_identifier}' n'existe pas.")
        self.cursor.execute("""
            INSERT INTO records (player_id, map_id, score)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, map_id) DO UPDATE SET score=excluded.score
        """, (player_id, map_id, score))
        self.conn.commit()

    def get_player_records(self, player_identifier):
        player_id = self._resolve_player_id(player_identifier)
        if player_id is None:
            return []
        self.cursor.execute("SELECT map_id, score FROM records WHERE player_id = ?", (player_id,))
        return self.cursor.fetchall()

    def get_map_records(self, map_id):
        self.cursor.execute("""
            SELECT p.name, r.score
            FROM records r
            JOIN players p ON r.player_id = p.player_id
            WHERE r.map_id = ?
        """, (map_id,))
        return self.cursor.fetchall()

    def get_player_record_count(self, player_identifier):
        player_id = self._resolve_player_id(player_identifier)
        if player_id is None:
            return 0
        self.cursor.execute("""
            SELECT COUNT(*) FROM records WHERE player_id = ?
        """, (player_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    # --------------------
    # Pagination optimisée
    # --------------------
    def get_players_by_record_count_cursor(self, last_count=None, last_id=None, limit=50, ascending=True):
        """
        Pagination basée sur un curseur pour éviter OFFSET.
        :param last_count: record_count du dernier joueur de la page précédente
        :param last_id: player_id du dernier joueur de la page précédente
        :param limit: nombre de joueurs à récupérer
        :param ascending: True = tri croissant, False = tri décroissant
        """
        order = "ASC" if ascending else "DESC"
        comparator_count = ">" if ascending else "<"
        comparator_id = ">" if ascending else "<"

        if last_count is None:
            # première page
            query = f"""
                SELECT p.player_id, p.name, COUNT(r.map_id) AS record_count
                FROM players p
                LEFT JOIN records r ON p.player_id = r.player_id
                GROUP BY p.player_id, p.name
                ORDER BY record_count {order}, p.player_id {order}
                LIMIT ?
            """
            self.cursor.execute(query, (limit,))
        else:
            # pages suivantes
            query = f"""
                SELECT p.player_id, p.name, COUNT(r.map_id) AS record_count
                FROM players p
                LEFT JOIN records r ON p.player_id = r.player_id
                GROUP BY p.player_id, p.name
                HAVING (COUNT(r.map_id) {comparator_count} ?) 
                       OR (COUNT(r.map_id) = ? AND p.player_id {comparator_id} ?)
                ORDER BY record_count {order}, p.player_id {order}
                LIMIT ?
            """
            self.cursor.execute(query, (last_count, last_count, last_id, limit))
        return self.cursor.fetchall()

    # --------------------
    # Utilitaires internes
    # --------------------
    def _resolve_player_id(self, player_identifier):
        if isinstance(player_identifier, int):
            return player_identifier
        return self.get_player_id(player_identifier)

    # --------------------
    # Fermeture de la DB
    # --------------------
    def close(self):
        self.conn.close()

# --------------------
# Exemple d'utilisation
# --------------------
if __name__ == "__main__":
    db = GameDatabase("test.dbn")

    # Ajouter quelques joueurs
    alice_id = db.add_player("Alice")
    bob_id = db.add_player("Bob")
    charlie_id = db.add_player("Charlie")

    # Ajouter des records (par name ou player_id)
    db.set_record("Alice", "map1", 500)
    db.set_record("Alice", "map2", 300)
    db.set_record(bob_id, "map1", 400)
    db.set_record("Charlie", "map1", 48048)

    # Vérifier les records par name ou ID
    print("Records Alice :", db.get_player_records("Alice"))
    print("Records Bob :", db.get_player_records(bob_id))

    # Tous les joueurs et leur nombre de records
    all_counts = db.get_all_players_record_counts()
    print("\nNombre de records par joueur :")
    for player_id, name, record_count in all_counts:
        print(f"{name} (ID {player_id}) a {record_count} record(s)")

    # Compter les records d'un joueur
    alice_count = db.get_player_record_count("Alice")
    print("\nAlice a", alice_count, "records")

    # Records d'une map
    map1_records = db.get_map_records("map1")
    print("\nRecords Map1 :", map1_records)

    # Première page (50 joueurs avec le moins de records)
    page1 = db.get_players_by_record_count_cursor(limit=50, ascending=True)
    print("Page 1 :", page1)

    # Pour la page suivante, on récupère le dernier joueur de la page 1
    last_count = page1[-1][2]  # record_count
    last_id = page1[-1][0]     # player_id

    page2 = db.get_players_by_record_count_cursor(last_count=last_count, last_id=last_id, limit=50, ascending=True)
    print("Page 2 :", page2)


    db.close()

