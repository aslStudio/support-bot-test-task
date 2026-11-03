"""Local demonstration data. This database contains no real customer records."""

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_policy() -> dict:
    return json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS demo_orders (
            id TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            status TEXT NOT NULL,
            delivery_note TEXT
        )"""
    )
    orders = json.loads((ROOT / "seed_orders.json").read_text(encoding="utf-8"))
    connection.executemany(
        "INSERT OR IGNORE INTO demo_orders (id, product, status, delivery_note) VALUES (:id, :product, :status, :delivery_note)",
        orders,
    )
    connection.commit()
    return connection


def get_order(connection: sqlite3.Connection, order_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, product, status, delivery_note FROM demo_orders WHERE id = ?",
        (order_id,),
    ).fetchone()


def list_orders(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id, product, status, delivery_note FROM demo_orders ORDER BY id"
    ).fetchall()
