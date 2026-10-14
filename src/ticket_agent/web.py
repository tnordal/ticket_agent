import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

COLUMNS = (
    "id, route_name, searched_at, results_count, cheapest_price, currency,"
    " booking_url, outbound_departure, inbound_departure, airlines"
)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ticket Agent – Runs</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px system-ui, sans-serif; height: 100vh; display: flex; flex-direction: column; color: #222; }
  header { padding: 12px 16px; background: #f3f4f6; border-bottom: 1px solid #d1d5db; display: flex; flex-wrap: wrap; gap: 12px; align-items: end; }
  header h1 { font-size: 16px; margin: 0 16px 0 0; align-self: center; }
  label { display: flex; flex-direction: column; font-size: 12px; color: #555; gap: 2px; }
  input, select, button { font: inherit; padding: 4px 6px; }
  #count { margin-left: auto; align-self: center; color: #555; }
  main { flex: 1; overflow: auto; }
  table { border-collapse: collapse; width: 100%; }
  th, td { padding: 6px 10px; text-align: left; white-space: nowrap; border-bottom: 1px solid #eee; }
  th { position: sticky; top: 0; background: #fff; cursor: pointer; user-select: none; border-bottom: 2px solid #d1d5db; }
  th.sorted::after { content: " \\25B2"; font-size: 10px; }
  th.sorted.desc::after { content: " \\25BC"; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  tbody tr:hover { background: #f9fafb; }
  .muted { color: #999; }
</style>
</head>
<body>
<header>
  <h1>Ticket Agent runs</h1>
  <label>Route <select id="route"><option value="">All</option></select></label>
  <label>Search <input id="q" type="search" placeholder="airline, route, ..."></label>
  <label>From <input id="from" type="date"></label>
  <label>To <input id="to" type="date"></label>
  <label>Min price <input id="min" type="number" min="0" style="width:90px"></label>
  <label>Max price <input id="max" type="number" min="0" style="width:90px"></label>
  <button id="reset">Reset</button>
  <span id="count"></span>
</header>
<main>
<table>
  <thead><tr id="head"></tr></thead>
  <tbody id="body"></tbody>
</table>
</main>
<script>
const COLS = [
  ["id", "ID", true], ["route_name", "Route"], ["searched_at", "Searched at (UTC)"],
  ["cheapest_price", "Cheapest", true], ["currency", "Cur"], ["results_count", "Results", true],
  ["airlines", "Airlines"], ["outbound_departure", "Outbound"], ["inbound_departure", "Inbound"],
  ["booking_url", "Booking"],
];
const $ = id => document.getElementById(id);
let rows = [], sortKey = "searched_at", sortDesc = true;

function esc(s) { return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

function cell(r, [key, , num]) {
  const v = r[key];
  if (v === null || v === undefined || v === "") return '<td class="muted">–</td>';
  if (key === "booking_url") {
    const links = String(v).split("|").map(s => s.trim()).filter(s => /^https?:\\/\\//i.test(s));
    return "<td>" + links.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">${links.length > 1 ? "link " + (i + 1) : "open"}</a>`).join(" ") + "</td>";
  }
  if (key === "searched_at") return `<td>${esc(v.replace("T", " ").replace("+00:00", ""))}</td>`;
  if (key === "cheapest_price") return `<td class="num">${Number(v).toFixed(0)}</td>`;
  return `<td${num ? ' class="num"' : ""}>${esc(v)}</td>`;
}

function filtered() {
  const route = $("route").value, q = $("q").value.trim().toLowerCase();
  const from = $("from").value, to = $("to").value;
  const min = $("min").value, max = $("max").value;
  return rows.filter(r => {
    if (route && r.route_name !== route) return false;
    const day = r.searched_at.slice(0, 10);
    if (from && day < from) return false;
    if (to && day > to) return false;
    if (min !== "" && (r.cheapest_price === null || r.cheapest_price < +min)) return false;
    if (max !== "" && (r.cheapest_price === null || r.cheapest_price > +max)) return false;
    if (q && !Object.values(r).some(v => v !== null && String(v).toLowerCase().includes(q))) return false;
    return true;
  });
}

function render() {
  const out = filtered().sort((a, b) => {
    const x = a[sortKey], y = b[sortKey];
    if (x === y) return 0;
    if (x === null) return 1;
    if (y === null) return -1;
    return (x < y ? -1 : 1) * (sortDesc ? -1 : 1);
  });
  $("body").innerHTML = out.map(r => "<tr>" + COLS.map(c => cell(r, c)).join("") + "</tr>").join("");
  $("count").textContent = `${out.length} of ${rows.length} records`;
  document.querySelectorAll("th").forEach(th => {
    th.classList.toggle("sorted", th.dataset.key === sortKey);
    th.classList.toggle("desc", sortDesc);
  });
}

$("head").innerHTML = COLS.map(([k, label]) => `<th data-key="${k}">${label}</th>`).join("");
$("head").addEventListener("click", e => {
  const key = e.target.dataset.key;
  if (!key) return;
  sortDesc = key === sortKey ? !sortDesc : false;
  sortKey = key;
  render();
});
["route", "q", "from", "to", "min", "max"].forEach(id => $(id).addEventListener("input", render));
$("reset").addEventListener("click", () => {
  ["route", "q", "from", "to", "min", "max"].forEach(id => $(id).value = "");
  render();
});

fetch("/api/runs").then(r => r.json()).then(data => {
  rows = data;
  [...new Set(rows.map(r => r.route_name))].sort().forEach(n => {
    $("route").insertAdjacentHTML("beforeend", `<option>${esc(n)}</option>`);
  });
  render();
});
</script>
</body>
</html>
"""


def make_handler(db_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/":
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            elif path == "/api/runs":
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                conn.row_factory = sqlite3.Row
                try:
                    rows = [dict(r) for r in conn.execute(f"SELECT {COLUMNS} FROM runs ORDER BY searched_at DESC, id DESC")]
                finally:
                    conn.close()
                self._send(200, json.dumps(rows).encode(), "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def log_message(self, format: str, *args) -> None:
            pass

    return Handler


def serve(db_path: Path, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    print(f"Serving {db_path} at http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
