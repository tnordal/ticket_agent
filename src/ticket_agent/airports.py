import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_NINJAS_URL = "https://api.api-ninjas.com/v1/airports"
DEFAULT_LIMIT = 10


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def search_airports(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    load_dotenv()
    api_key = os.environ.get("API_NINJAS_API_KEY")
    if not api_key:
        raise RuntimeError("API_NINJAS_API_KEY is not set")
    params = urlencode({"q": query, "limit": max(1, min(limit, 100)), "has_iata": "true"})
    req = Request(f"{API_NINJAS_URL}?{params}", headers={"X-Api-Key": api_key})
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"airport search failed: {exc}") from exc


def format_airports(rows: list[dict]) -> str:
    if not rows:
        return "No airports found."
    code_w = max(len("IATA"), *(len((r.get("iata") or "-")) for r in rows))
    city_w = max(len("City"), *(len(r.get("city") or "-") for r in rows))
    country_w = max(len("Country"), *(len(r.get("country") or "-") for r in rows))
    size_w = max(len("Size"), *(len(r.get("size") or "-") for r in rows))
    lines = [
        f"{'IATA':<{code_w}}  {'City':<{city_w}}  {'Country':<{country_w}}  {'Size':<{size_w}}  Name",
        f"{'-' * code_w}  {'-' * city_w}  {'-' * country_w}  {'-' * size_w}  {'-' * 30}",
    ]
    for r in rows:
        lines.append(
            f"{(r.get('iata') or '-'): <{code_w}}  {(r.get('city') or '-'): <{city_w}}  "
            f"{(r.get('country') or '-'): <{country_w}}  {(r.get('size') or '-'): <{size_w}}  {r.get('name') or '-'}"
        )
    return "\n".join(lines)
