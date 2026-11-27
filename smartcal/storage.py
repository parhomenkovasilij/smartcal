"""Локальне збереження даних у SQLite (SCF_07)."""
import sqlite3
from datetime import datetime

from .models import Block, FixedEvent, Settings, Task

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, title TEXT, start TEXT, end TEXT);
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, deadline TEXT,
                                  duration_h REAL, priority INTEGER);
CREATE TABLE IF NOT EXISTS blocks (id INTEGER PRIMARY KEY, task_id INTEGER, start TEXT,
                                   end TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL);
"""


class Storage:
    def __init__(self, path: str = "smartcal.db"):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    # --- події ---
    def events(self) -> list[FixedEvent]:
        rows = self.conn.execute("SELECT id, title, start, end FROM events ORDER BY start")
        return [FixedEvent(t, datetime.fromisoformat(s), datetime.fromisoformat(e), i)
                for i, t, s, e in rows]

    def save_event(self, ev: FixedEvent) -> None:
        if ev.id is None:
            cur = self.conn.execute("INSERT INTO events (title, start, end) VALUES (?, ?, ?)",
                                    (ev.title, ev.start.isoformat(), ev.end.isoformat()))
            ev.id = cur.lastrowid
        else:
            self.conn.execute("UPDATE events SET title=?, start=?, end=? WHERE id=?",
                              (ev.title, ev.start.isoformat(), ev.end.isoformat(), ev.id))
        self.conn.commit()

    def delete_event(self, event_id: int) -> None:
        self.conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.conn.commit()

    # --- завдання ---
    def tasks(self) -> list[Task]:
        rows = self.conn.execute("SELECT id, title, deadline, duration_h, priority FROM tasks")
        return [Task(t, datetime.fromisoformat(d), h, p, i) for i, t, d, h, p in rows]

    def save_task(self, task: Task) -> None:
        cur = self.conn.execute(
            "INSERT INTO tasks (title, deadline, duration_h, priority) VALUES (?, ?, ?, ?)",
            (task.title, task.deadline.isoformat(), task.duration_h, task.priority))
        task.id = cur.lastrowid
        self.conn.commit()

    def delete_task(self, task_id: int) -> None:
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.execute("DELETE FROM blocks WHERE task_id=?", (task_id,))
        self.conn.commit()

    # --- блоки ---
    def blocks(self) -> list[Block]:
        rows = self.conn.execute("SELECT id, task_id, start, end, status FROM blocks ORDER BY start")
        return [Block(t, datetime.fromisoformat(s), datetime.fromisoformat(e), st, i)
                for i, t, s, e, st in rows]

    def replace_planned_blocks(self, blocks: list[Block]) -> None:
        """Видаляє всі незавершені блоки й записує новий план (історія done/skipped лишається)."""
        self.conn.execute("DELETE FROM blocks WHERE status='planned'")
        for b in blocks:
            cur = self.conn.execute(
                "INSERT INTO blocks (task_id, start, end, status) VALUES (?, ?, ?, ?)",
                (b.task_id, b.start.isoformat(), b.end.isoformat(), b.status))
            b.id = cur.lastrowid
        self.conn.commit()

    def set_block_status(self, block_id: int, status: str) -> None:
        self.conn.execute("UPDATE blocks SET status=? WHERE id=?", (status, block_id))
        self.conn.commit()

    # --- налаштування ---
    def settings(self) -> Settings:
        s = Settings()
        for key, value in self.conn.execute("SELECT key, value FROM settings"):
            if hasattr(s, key):
                setattr(s, key, type(getattr(s, key))(value))
        return s

    def save_settings(self, s: Settings) -> None:
        for key, value in vars(s).items():
            self.conn.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, value))
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
