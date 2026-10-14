# ticket-agent

Personal flight price tracker. Queries the free public [Kiwi.com MCP server](https://www.kiwi.com/en/pages/mcp/)
(`https://mcp.kiwi.com`) and stores the cheapest price per route in SQLite.

## Usage

```sh
uv sync
uv run ticket-agent run          # search all routes in routes.json, store results
uv run ticket-agent report -n 30 # price history with change vs previous run
uv run ticket-agent airports oslo
```

## Airport code helper

Search airport codes from the CLI:

```sh
export API_NINJAS_API_KEY=...
uv run ticket-agent airports oslo
uv run ticket-agent airports bangkok -n 20
```

This uses the free-text Airports API from API Ninjas and returns IATA-coded airports.

`routes.json` entries use the Kiwi `search-flight` tool arguments directly (dates are `dd/mm/yyyy`),
plus a `name`. Any extra tool argument works, e.g. `max_sector_stopovers`, `select_airlines`,
`price_to`, `adults_hold_bags`, `nights_in_dst_from`/`nights_in_dst_to`.

`TOP_N` is also supported per route and controls how many itineraries are printed for that route.
If omitted, the default from `src/ticket_agent/__init__.py` is used.

### Max stops

`"maxStops": 1` limits every leg (each direction) to at most that many stops; `0` means direct only.
It is an alias for Kiwi's `max_sector_stopovers` and also applies to both searches in mixed-class routes.

### Cabin class

- `"cabinClass": "economy"` or `"business"` (also `premium_economy`, `first`, or Kiwi codes `M/W/C/F`) applies both ways.
- `"cabinClassOutbound"` / `"cabinClassInbound"` set the class per direction, e.g. business out, economy back.
  An omitted direction defaults to economy.

Kiwi takes one cabin class per search, so when the two directions differ the agent runs two one-way
searches and pairs the cheapest ones (return must depart after arrival; `nights_in_dst_*` is honored).
The booking URL is then two links joined by ` | `. `ret_*` filters apply to the inbound search.

## Schedule (4x per day)

`crontab -e`:

```
0 7,12,17,22 * * * cd /home/tn/projects/ticket_agent && /home/tn/.local/bin/uv run ticket-agent run >> run.log 2>&1
```

Adjust the `uv` path with `which uv`. Data is stored in `prices.db` (git-ignored).
Expired date ranges will return no results, so update `routes.json` as dates pass.
