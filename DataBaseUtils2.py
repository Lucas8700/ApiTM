import sqlite3

class GameDatabase:
    def __init__(self, db_name="medal_tracker_2.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        # Players
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT UNIQUE NOT NULL
            )
        """)

        # Maps
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Maps (
                map_id TEXT PRIMARY KEY,
                map_name TEXT NOT NULL,
                map_author TEXT NOT NULL,
                release_date DATE NOT NULL,
                author_time INTEGER NOT NULL,
                gold_time INTEGER NOT NULL,
                author_count INTEGER DEFAULT 0,
                gold_count INTEGER DEFAULT 0
            )
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_release_date
            ON Maps(release_date)
        """)

        # Player times
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Player_Times (
                time_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                map_id TEXT NOT NULL,
                player_time INTEGER NOT NULL,
                UNIQUE(player_id, map_id),
                FOREIGN KEY (player_id) REFERENCES Players(player_id),
                FOREIGN KEY (map_id) REFERENCES Maps(map_id)
            )
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_player_id
            ON Player_Times(player_id)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_map_id
            ON Player_Times(map_id)
        """)

        self.conn.commit()

    # --------------------
    # Gestion des joueurs
    # --------------------
    def add_player(self, name):
        self.cursor.execute(
            "SELECT player_id FROM Players WHERE player_name = ?", (name,)
        )
        result = self.cursor.fetchone()
        if result:
            return result[0]

        self.cursor.execute(
            "INSERT INTO Players (player_name) VALUES (?)", (name,)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_player_id(self, name):
        self.cursor.execute(
            "SELECT player_id FROM Players WHERE player_name = ?", (name,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_player_name(self, player_id):
        self.cursor.execute(
            "SELECT player_name FROM Players WHERE player_id = ?", (player_id,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None

    # --------------------
    # Gestion des records (temps)
    # --------------------
    def set_record(self, player_identifier, map_id, score):
        """
        score = player_time (ms)
        """
        player_id = self._resolve_player_id(player_identifier)
        if player_id is None:
            raise ValueError(f"Le joueur '{player_identifier}' n'existe pas.")

        self.cursor.execute("""
            INSERT INTO Player_Times (player_id, map_id, player_time)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, map_id)
            DO UPDATE SET player_time = excluded.player_time
        """, (player_id, map_id, score))

        self.conn.commit()

    def get_player_records(self, player_identifier):
        player_id = self._resolve_player_id(player_identifier)
        if player_id is None:
            return []

        self.cursor.execute("""
            SELECT map_id, player_time
            FROM Player_Times
            WHERE player_id = ?
        """, (player_id,))
        return self.cursor.fetchall()

    def get_map_records(self, map_id):
        self.cursor.execute("""
            SELECT p.player_name, pt.player_time
            FROM Player_Times pt
            JOIN Players p ON pt.player_id = p.player_id
            WHERE pt.map_id = ?
            ORDER BY pt.player_time ASC
        """, (map_id,))
        return self.cursor.fetchall()

    def get_player_record_count(self, player_identifier):
        player_id = self._resolve_player_id(player_identifier)
        if player_id is None:
            return 0

        self.cursor.execute("""
            SELECT COUNT(*) FROM Player_Times WHERE player_id = ?
        """, (player_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    # --------------------
    # Pagination optimisée
    # --------------------
    def get_players_by_record_count_cursor(
        self, last_count=None, last_id=None, limit=50, ascending=True
    ):
        order = "ASC" if ascending else "DESC"
        cmp = ">" if ascending else "<"

        if last_count is None:
            query = f"""
                SELECT p.player_id, p.player_name, COUNT(pt.map_id) AS record_count
                FROM Players p
                LEFT JOIN Player_Times pt ON p.player_id = pt.player_id
                GROUP BY p.player_id
                ORDER BY record_count {order}, p.player_id {order}
                LIMIT ?
            """
            self.cursor.execute(query, (limit,))
        else:
            query = f"""
                SELECT p.player_id, p.player_name, COUNT(pt.map_id) AS record_count
                FROM Players p
                LEFT JOIN Player_Times pt ON p.player_id = pt.player_id
                GROUP BY p.player_id
                HAVING (COUNT(pt.map_id) {cmp} ?)
                   OR (COUNT(pt.map_id) = ? AND p.player_id {cmp} ?)
                ORDER BY record_count {order}, p.player_id {order}
                LIMIT ?
            """
            self.cursor.execute(
                query, (last_count, last_count, last_id, limit)
            )

        return self.cursor.fetchall()

    # --------------------
    # Gestion des maps
    # --------------------
    def get_map_id(self, map_uid):
        self.cursor.execute("SELECT map_id FROM Maps WHERE map_id = ?", (map_uid,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_map_if_not_exists(self, map_uid, map_name, map_author, release_date, author_time, gold_time):
        if self.get_map_id(map_uid) is None:
            self.cursor.execute("""
                INSERT INTO Maps (map_id, map_name, map_author, release_date, author_time, gold_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (map_uid, map_name, map_author, release_date, author_time, gold_time))
            self.conn.commit()

    def increment_author_count(self, map_id):
        self.cursor.execute("UPDATE Maps SET author_count = author_count + 1 WHERE map_id = ?", (map_id,))
        self.conn.commit()

    def fill_map_with_author_medals(self, map_row, api):
        map_uid = map_row["mapUid"]
        map_info = api.get_map_info(map_uid)
        release_date = f"{map_row['year']}-{map_row['month']:02d}-{map_row['monthDay']:02d}"
        self.add_map_if_not_exists(map_uid, map_info["name"], map_info["author"], release_date, map_info["authorTime"], map_info["goldTime"])
        fb_players = api.get_players_with_author("Personal_Best", map_uid)
        for _, player_row in fb_players.iterrows():
            self.add_player(player_row["player"])
            self.set_record(player_row["player"], map_uid, player_row["score"])
            self.increment_author_count(map_uid)

    def get_total_maps(self):
        self.cursor.execute("SELECT COUNT(*) FROM Maps")
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def get_players_by_author_count(self, limit=50, offset=0):
        self.cursor.execute("""
            SELECT p.player_id, p.player_name, COUNT(pt.map_id) AS author_count
            FROM Players p
            LEFT JOIN Player_Times pt ON p.player_id = pt.player_id
            GROUP BY p.player_id
            ORDER BY author_count DESC, p.player_id
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return self.cursor.fetchall()

    def get_player_maps(self, player_id):
        self.cursor.execute("""
            SELECT m.release_date, m.map_name, m.map_author, m.author_count, m.author_time, pt.player_time
            FROM Maps m
            LEFT JOIN Player_Times pt ON m.map_id = pt.map_id AND pt.player_id = ?
            ORDER BY m.release_date DESC
        """, (player_id,))
        return self.cursor.fetchall()

    def search_players(self, query, limit=50):
        self.cursor.execute("""
            SELECT player_id, player_name
            FROM Players
            WHERE player_name LIKE ?
            ORDER BY player_name
            LIMIT ?
        """, (f"%{query}%", limit))
        return self.cursor.fetchall()

    # --------------------
    # Utilitaires internes
    # --------------------
    def _resolve_player_id(self, player_identifier):
        if isinstance(player_identifier, int):
            return player_identifier
        return self.get_player_id(player_identifier)

    # --------------------
    # Fermeture DB
    # --------------------
    def close(self):
        self.conn.close()