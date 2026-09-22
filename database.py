import sqlite3
import threading


class Database:
    def __init__(self, path="caos.db"):
        self.path = path
        self.lock = threading.Lock()
        self.init()

    def connect(self):
        conn = sqlite3.connect(
            self.path,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        return conn

    def init(self):
        with self.lock:
            conn = self.connect()

            conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    energy INTEGER DEFAULT 100,
                    fragments INTEGER DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    actions INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id INTEGER PRIMARY KEY,
                    round INTEGER DEFAULT 1,
                    world_energy INTEGER DEFAULT 100,
                    chaos INTEGER DEFAULT 0,
                    event TEXT DEFAULT '🌌 NORMAL',
                    round_started INTEGER DEFAULT 0,
                    round_ends INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS memberships (
                    chat_id INTEGER,
                    user_id INTEGER,
                    PRIMARY KEY(chat_id, user_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS round_actions (
                    chat_id INTEGER,
                    round INTEGER,
                    user_id INTEGER,
                    action TEXT,
                    PRIMARY KEY(chat_id, round, user_id)
                )
            """)

            conn.commit()
            conn.close()

    def create_player(self, user_id, username, name):
        with self.lock:
            conn = self.connect()

            conn.execute("""
                INSERT INTO players(
                    user_id,
                    username,
                    name
                )
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    username=excluded.username,
                    name=excluded.name
            """, (
                user_id,
                username,
                name
            ))

            conn.commit()
            conn.close()

    def get_player(self, user_id):
        conn = self.connect()

        row = conn.execute(
            "SELECT * FROM players WHERE user_id=?",
            (user_id,)
        ).fetchone()

        conn.close()

        return row

    def create_group(self, chat_id):
        with self.lock:
            conn = self.connect()

            conn.execute("""
                INSERT INTO groups(chat_id)
                VALUES (?)
                ON CONFLICT(chat_id)
                DO NOTHING
            """, (chat_id,))

            conn.commit()
            conn.close()

    def get_group(self, chat_id):
        conn = self.connect()

        row = conn.execute(
            "SELECT * FROM groups WHERE chat_id=?",
            (chat_id,)
        ).fetchone()

        conn.close()

        return row

    def join_group(self, chat_id, user_id):
        with self.lock:
            conn = self.connect()

            conn.execute("""
                INSERT OR IGNORE INTO memberships(
                    chat_id,
                    user_id
                )
                VALUES (?, ?)
            """, (
                chat_id,
                user_id
            ))

            conn.commit()
            conn.close()

    def is_member(self, chat_id, user_id):
        conn = self.connect()

        row = conn.execute("""
            SELECT 1
            FROM memberships
            WHERE chat_id=? AND user_id=?
        """, (
            chat_id,
            user_id
        )).fetchone()

        conn.close()

        return row is not None

    def update_player(
        self,
        user_id,
        energy_delta=0,
        fragments_delta=0,
        score_delta=0,
        action_delta=0
    ):
        with self.lock:
            conn = self.connect()

            conn.execute("""
                UPDATE players
                SET
                    energy = MAX(
                        0,
                        energy + ?
                    ),
                    fragments = MAX(
                        0,
                        fragments + ?
                    ),
                    score = MAX(
                        0,
                        score + ?
                    ),
                    actions = actions + ?
                WHERE user_id=?
            """, (
                energy_delta,
                fragments_delta,
                score_delta,
                action_delta,
                user_id
            ))

            conn.commit()
            conn.close()

    def update_group(
        self,
        chat_id,
        round_delta=0,
        world_energy_delta=0,
        chaos_delta=0,
        event=None,
        round_started=None,
        round_ends=None
    ):
        with self.lock:
            conn = self.connect()

            group = conn.execute(
                "SELECT * FROM groups WHERE chat_id=?",
                (chat_id,)
            ).fetchone()

            if not group:
                conn.close()
                return

            new_round = group["round"] + round_delta

            new_world_energy = max(
                0,
                min(
                    100,
                    group["world_energy"]
                    + world_energy_delta
                )
            )

            new_chaos = max(
                0,
                min(
                    100,
                    group["chaos"]
                    + chaos_delta
                )
            )

            conn.execute("""
                UPDATE groups
                SET
                    round=?,
                    world_energy=?,
                    chaos=?,
                    event=COALESCE(?, event),
                    round_started=COALESCE(
                        ?,
                        round_started
                    ),
                    round_ends=COALESCE(
                        ?,
                        round_ends
                    )
                WHERE chat_id=?
            """, (
                new_round,
                new_world_energy,
                new_chaos,
                event,
                round_started,
                round_ends,
                chat_id
            ))

            conn.commit()
            conn.close()

    def action_exists(
        self,
        chat_id,
        round_number,
        user_id
    ):
        conn = self.connect()

        row = conn.execute("""
            SELECT 1
            FROM round_actions
            WHERE chat_id=?
              AND round=?
              AND user_id=?
        """, (
            chat_id,
            round_number,
            user_id
        )).fetchone()

        conn.close()

        return row is not None

    def save_action(
        self,
        chat_id,
        round_number,
        user_id,
        action
    ):
        with self.lock:
            conn = self.connect()

            conn.execute("""
                INSERT OR IGNORE INTO round_actions(
                    chat_id,
                    round,
                    user_id,
                    action
                )
                VALUES (?, ?, ?, ?)
            """, (
                chat_id,
                round_number,
                user_id,
                action
            ))

            conn.commit()
            conn.close()

    def action_count(
        self,
        chat_id,
        round_number
    ):
        conn = self.connect()

        row = conn.execute("""
            SELECT COUNT(*) AS total
            FROM round_actions
            WHERE chat_id=? AND round=?
        """, (
            chat_id,
            round_number
        )).fetchone()

        conn.close()

        return row["total"]

    def ranking(self, chat_id, limit=10):
        conn = self.connect()

        rows = conn.execute("""
            SELECT p.*
            FROM players p
            JOIN memberships m
              ON p.user_id=m.user_id
            WHERE m.chat_id=?
            ORDER BY p.score DESC
            LIMIT ?
        """, (
            chat_id,
            limit
        )).fetchall()

        conn.close()

        return rows
