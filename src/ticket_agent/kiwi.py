from contextlib import asynccontextmanager
from datetime import datetime

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

KIWI_MCP_URL = "https://mcp.kiwi.com"

CABIN_CODES = {
    "economy": "M",
    "premium_economy": "W",
    "business": "C",
    "first": "F",
}
CABIN_KEYS = ("cabinClass", "cabinClassOutbound", "cabinClassInbound")
PAIR_POOL = 30


@asynccontextmanager
async def kiwi_session():
    async with streamable_http_client(KIWI_MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def cabin_code(value: str | None) -> str | None:
    if value is None:
        return None
    code = CABIN_CODES.get(str(value).strip().lower().replace(" ", "_").replace("-", "_"), value)
    if code not in CABIN_CODES.values():
        raise ValueError(f"unknown cabin class {value!r} (use {', '.join(CABIN_CODES)})")
    return code


async def _call(session: ClientSession, params: dict) -> dict:
    result = await session.call_tool("search-flight", params)
    data = result.structured_content
    if result.is_error or not data:
        text = " ".join(getattr(c, "text", "") for c in result.content)
        raise RuntimeError(f"Kiwi search failed: {text[:300]}")
    if data.get("error"):
        raise RuntimeError(f"Kiwi search error: {data['error']}")
    return data


def _one_way_params(params: dict, outbound: bool) -> dict:
    base = {k: v for k, v in params.items() if k not in CABIN_KEYS}
    for key in ("returnDate", "returnDateTo", "returnDateFlexDays", "nights_in_dst_from", "nights_in_dst_to"):
        base.pop(key, None)
    if outbound:
        for key in ("ret_dtime_from", "ret_dtime_to", "ret_atime_from", "ret_atime_to", "ret_fly_days"):
            base.pop(key, None)
        return base
    inbound = {k: v for k, v in base.items() if not k.startswith("ret_") and k not in (
        "dtime_from", "dtime_to", "atime_from", "atime_to", "fly_days", "departureDate",
        "departureDateTo", "departureDateFlexDays")}
    inbound["flyFrom"], inbound["flyTo"] = params["flyTo"], params["flyFrom"]
    inbound["departureDate"] = params["returnDate"]
    for src, dst in (
        ("returnDateTo", "departureDateTo"),
        ("returnDateFlexDays", "departureDateFlexDays"),
        ("ret_dtime_from", "dtime_from"),
        ("ret_dtime_to", "dtime_to"),
        ("ret_atime_from", "atime_from"),
        ("ret_atime_to", "atime_to"),
        ("ret_fly_days", "fly_days"),
    ):
        if src in params:
            inbound[dst] = params[src]
    return inbound


def _combine(out: dict, back: dict, params: dict) -> dict | None:
    o, i = out["outbound"], back["outbound"]
    dep_out = datetime.fromisoformat(o["departureTime"])
    dep_in = datetime.fromisoformat(i["departureTime"])
    if dep_in <= datetime.fromisoformat(o["arrivalTime"]):
        return None
    nights = (dep_in.date() - dep_out.date()).days
    lo, hi = params.get("nights_in_dst_from"), params.get("nights_in_dst_to")
    if (lo is not None and nights < lo) or (hi is not None and nights > hi):
        return None
    price = out["price"] + back["price"]
    return {
        "price": price,
        "priceFormatted": f"{price:.0f} {params.get('currency', '')}".strip(),
        "totalDurationSeconds": (o.get("durationSeconds") or 0) + (i.get("durationSeconds") or 0),
        "bookingUrl": " | ".join(u for u in (out.get("bookingUrl"), back.get("bookingUrl")) if u),
        "outbound": o,
        "inbound": i,
    }


async def _search_mixed(session: ClientSession, params: dict, out_cabin: str, in_cabin: str) -> dict:
    if "returnDate" not in params:
        raise ValueError("cabinClassInbound needs a returnDate")
    out_data = await _call(session, {**_one_way_params(params, True), "cabinClass": out_cabin})
    in_data = await _call(session, {**_one_way_params(params, False), "cabinClass": in_cabin})
    outs = sorted(out_data.get("itineraries") or [], key=lambda x: x["price"])[:PAIR_POOL]
    backs = sorted(in_data.get("itineraries") or [], key=lambda x: x["price"])[:PAIR_POOL]
    combined = [c for o in outs for b in backs if (c := _combine(o, b, params))]
    return {"currency": out_data.get("currency") or in_data.get("currency"), "itineraries": combined}


async def search_flights(session: ClientSession, params: dict) -> dict:
    params = dict(params)
    if "maxStops" in params:
        params.setdefault("max_sector_stopovers", params.pop("maxStops"))
        params.pop("maxStops", None)
    default = cabin_code(params.get("cabinClass"))
    out_cabin = cabin_code(params.get("cabinClassOutbound")) or default
    in_cabin = cabin_code(params.get("cabinClassInbound")) or default
    if "returnDate" not in params:
        in_cabin = out_cabin
    if out_cabin or in_cabin:
        out_cabin, in_cabin = out_cabin or "M", in_cabin or "M"
    if out_cabin != in_cabin:
        return await _search_mixed(session, params, out_cabin, in_cabin)
    plain = {k: v for k, v in params.items() if k not in CABIN_KEYS}
    if out_cabin:
        plain["cabinClass"] = out_cabin
    return await _call(session, plain)
