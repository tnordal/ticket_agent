import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_name TEXT NOT NULL,
    searched_at TEXT NOT NULL,
    results_count INTEGER NOT NULL,
    cheapest_price REAL,
    currency TEXT,
    booking_url TEXT,
    outbound_departure TEXT,
    inbound_departure TEXT,
    airlines TEXT,
    top_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_route ON runs (route_name, searched_at);
"""

TOP_N = 5


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _airlines(itinerary: dict) -> str:
    names: list[str] = []
    for leg in ("outbound", "inbound"):
        for seg in (itinerary.get(leg) or {}).get("segments", []):
            name = seg.get("carrierName") or seg.get("carrier")
            if name and name not in names:
                names.append(name)
    return ", ".join(names)


def save_run(conn: sqlite3.Connection, route_name: str, data: dict) -> sqlite3.Row | None:
    itineraries = sorted(data.get("itineraries") or [], key=lambda i: i["price"])
    best = itineraries[0] if itineraries else None
    conn.execute(
        "INSERT INTO runs (route_name, searched_at, results_count, cheapest_price, currency,"
        " booking_url, outbound_departure, inbound_departure, airlines, top_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            route_name,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            len(itineraries),
            best["price"] if best else None,
            data.get("currency"),
            best.get("bookingUrl") if best else None,
            (best.get("outbound") or {}).get("departureTime") if best else None,
            (best.get("inbound") or {}).get("departureTime") if best else None,
            _airlines(best) if best else None,
            json.dumps(itineraries[:TOP_N]),
        ),
    )
    conn.commit()
    return conn.execute("SELECT * FROM runs WHERE id = last_insert_rowid()").fetchone()


def history(conn: sqlite3.Connection, route_name: str, limit: int) -> list[sqlite3.Row]:
    rows = conn.execute(
        "SELECT * FROM runs WHERE route_name = ? ORDER BY searched_at DESC, id DESC LIMIT ?",
        (route_name, limit),
    ).fetchall()
    return list(reversed(rows))


def route_names(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT route_name FROM runs ORDER BY route_name")]


def lowest_ever(conn: sqlite3.Connection, route_name: str) -> float | None:
    row = conn.execute(
        "SELECT MIN(cheapest_price) FROM runs WHERE route_name = ?", (route_name,)
    ).fetchone()
    return row[0]
