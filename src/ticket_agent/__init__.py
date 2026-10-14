import argparse
import asyncio
import json
import sys
from pathlib import Path

from ticket_agent import db
from ticket_agent.airports import format_airports, search_airports
from ticket_agent.format import format_itineraries
from ticket_agent.kiwi import kiwi_session, search_flights

ROOT = Path.cwd()
DEFAULT_ROUTES = ROOT / "routes.json"
DEFAULT_DB = ROOT / "prices.db"
TOP_N = 10


def load_routes(path: Path) -> list[dict]:
    routes = json.loads(path.read_text())
    for route in routes:
        for key in ("name", "flyFrom", "flyTo", "departureDate"):
            if key not in route:
                raise SystemExit(f"{path}: route {route.get('name', route)} is missing '{key}'")
    return routes


async def run_searches(routes: list[dict], conn) -> int:
    failures = 0
    async with kiwi_session() as session:
        for route in routes:
            name = route["name"]
            params = {k: v for k, v in route.items() if k != "name"}
            try:
                data = await search_flights(session, params)
            except Exception as exc:
                failures += 1
                print(f"[{name}] FAILED: {exc}", file=sys.stderr)
                continue
            row = db.save_run(conn, name, data)
            if row["cheapest_price"] is None:
                print(f"[{name}] no results")
                continue
            prev = db.history(conn, name, 2)
            change = ""
            if len(prev) == 2 and prev[0]["cheapest_price"] is not None:
                delta = row["cheapest_price"] - prev[0]["cheapest_price"]
                change = f" ({delta:+.0f} vs last run)"
            print(f"[{name}] cheapest {row['cheapest_price']:.0f} {row['currency']}{change}")
            print(format_itineraries(data["itineraries"], TOP_N))
    return failures


def print_report(conn, limit: int) -> None:
    names = db.route_names(conn)
    if not names:
        print("No data yet. Run: uv run ticket-agent run")
        return
    for name in names:
        rows = db.history(conn, name, limit)
        low = db.lowest_ever(conn, name)
        print(f"\n== {name} (lowest ever: {low:.0f}) ==" if low is not None else f"\n== {name} ==")
        prev = None
        for r in rows:
            price = r["cheapest_price"]
            if price is None:
                print(f"{r['searched_at']}  no results")
                continue
            delta = f"{price - prev:+.0f}" if prev is not None else "  -"
            print(f"{r['searched_at']}  {price:7.0f} {r['currency']}  {delta:>5}  {r['airlines']}")
            prev = price


def main() -> None:
    parser = argparse.ArgumentParser(prog="ticket-agent", description="Track flight prices via Kiwi MCP")
    parser.add_argument("--routes", type=Path, default=DEFAULT_ROUTES)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="search all routes and store the cheapest price")
    report = sub.add_parser("report", help="show price history")
    report.add_argument("-n", "--limit", type=int, default=20)
    airports = sub.add_parser("airports", help="search airport codes by text")
    airports.add_argument("query", help="airport/city/code text")
    airports.add_argument("-n", "--limit", type=int, default=10)
    args = parser.parse_args()

    conn = db.connect(args.db)
    if args.command == "run":
        failures = asyncio.run(run_searches(load_routes(args.routes), conn))
        raise SystemExit(1 if failures else 0)
    if args.command == "airports":
        print(format_airports(search_airports(args.query, args.limit)))
        return
    print_report(conn, args.limit)
