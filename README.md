# ticket-agent

Personal flight price tracker. Queries the free public [Kiwi.com MCP server](https://www.kiwi.com/en/pages/mcp/)
(`https://mcp.kiwi.com`) and stores the cheapest price per route in SQLite.

## Usage

```sh
uv sync
uv run ticket-agent run          # search all routes in routes.json, store results
uv run ticket-agent report -n 30 # price history with change vs previous run
```

`routes.json` entries use the Kiwi `search-flight` tool arguments directly (dates are `dd/mm/yyyy`),
plus a `name`. Any extra tool argument works, e.g. `max_sector_stopovers`, `select_airlines`,
`price_to`, `adults_hold_bags`, `nights_in_dst_from`/`nights_in_dst_to`.

## Schedule (4x per day)

`crontab -e`:

```
0 7,12,17,22 * * * cd /home/tn/projects/ticket_agent && /home/tn/.local/bin/uv run ticket-agent run >> run.log 2>&1
```

Adjust the `uv` path with `which uv`. Data is stored in `prices.db` (git-ignored).
Expired date ranges will return no results, so update `routes.json` as dates pass.
