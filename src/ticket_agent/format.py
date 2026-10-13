from datetime import datetime


def _duration(seconds: int | None) -> str:
    if seconds is None:
        return "?"
    hours, rem = divmod(int(seconds), 3600)
    return f"{hours}h {rem // 60:02d}m"


def _time(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%a %d %b %H:%M")


def _leg(label: str, leg: dict) -> str:
    arrival = datetime.fromisoformat(leg["arrivalTime"]).strftime("%H:%M")
    stops = "direct" if not leg.get("stops") else f"{leg['stops']} stop(s)"
    airlines = ", ".join(
        dict.fromkeys(s.get("carrierName") or s.get("carrier", "?") for s in leg.get("segments", []))
    )
    return (
        f"     {label:<3} {_time(leg['departureTime'])} → {arrival}  "
        f"{' → '.join(leg['route'])}  {_duration(leg.get('durationSeconds'))}  {stops}  ({airlines})"
    )


def format_itineraries(itineraries: list[dict], limit: int = 5) -> str:
    lines = []
    for i, it in enumerate(sorted(itineraries, key=lambda x: x["price"])[:limit], 1):
        lines.append(
            f"  {i}. {it['priceFormatted']}  total {_duration(it.get('totalDurationSeconds'))}  {it.get('bookingUrl', '')}"
        )
        lines.append(_leg("out", it["outbound"]))
        if it.get("inbound"):
            lines.append(_leg("in", it["inbound"]))
    return "\n".join(lines)
