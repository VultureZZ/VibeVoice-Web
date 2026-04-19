"""
Operator-facing HTML for production QA audition and admin dashboard.
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["production-ui"])


def _audition_html(task_id: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Audition {task_id}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; display: flex; height: 100vh; }}
main {{ flex: 1; padding: 1rem; overflow: auto; }}
aside {{ width: 320px; border-left: 1px solid #ccc; padding: 1rem; background: #f8f8f8; overflow: auto; }}
.timeline {{ position: relative; height: 120px; background: #222; border-radius: 6px; margin: 1rem 0; }}
.ev {{ position: absolute; top: 4px; height: 24px; border-radius: 3px; cursor: pointer; font-size: 10px; color: #fff; padding: 2px 4px; overflow: hidden; }}
.ev.muted {{ opacity: 0.35; }}
.ev.solo {{ outline: 2px solid #fc0; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
.pass {{ background: #cfc; }}
.fail {{ background: #fcc; }}
.meta {{ font-size: 12px; color: #444; margin-top: 0.5rem; }}
button {{ margin-top: 0.5rem; }}
</style></head><body>
<main>
  <h1>Audition</h1>
  <p id="status"></p>
  <audio id="player" controls style="width:100%"></audio>
  <div id="timeline" class="timeline"></div>
  <pre id="evdetail" class="meta"></pre>
</main>
<aside>
  <h2>QA</h2>
  <div id="qa"></div>
  <h3>Regenerate event</h3>
  <p class="meta">Select an event on the timeline, then:</p>
  <button type="button" id="regen">Regenerate this event</button>
  <p id="regenmsg" class="meta"></p>
</aside>
<script>
const TASK = """ + json.dumps(task_id) + """;
let data = null;
let selected = null;

async function load() {{
  const r = await fetch('/api/v1/podcast/production/' + encodeURIComponent(TASK) + '/audition');
  if (!r.ok) {{ document.getElementById('status').textContent = 'Load failed'; return; }}
  data = await r.json();
  document.getElementById('status').textContent = data.status || '';
  if (data.audio_url) {{
    document.getElementById('player').src = data.audio_url;
  }}
  renderQA(data.qa_results);
  renderTimeline(data.production_plan);
}}

function renderQA(qa) {{
  const el = document.getElementById('qa');
  el.innerHTML = '';
  if (!qa || !qa.checks) {{ el.textContent = 'No QA data'; return; }}
  for (const c of qa.checks) {{
    const d = document.createElement('div');
    d.style.marginBottom = '8px';
    const b = document.createElement('span');
    b.className = 'badge ' + (c.passed ? 'pass' : 'fail');
    b.textContent = (c.passed ? 'PASS' : 'FAIL') + ' ' + c.name;
    d.appendChild(b);
    d.appendChild(document.createTextNode(' ' + JSON.stringify(c.value) + ' (' + c.threshold + ')'));
    el.appendChild(d);
  }}
}}

function msTotal(plan) {{
  let m = 0;
  for (const t of (plan && plan.tracks) || []) {{
    for (const e of t.events || []) {{
      m = Math.max(m, (e.start_ms|0) + (e.duration_ms|0));
    }}
  }}
  return Math.max(m, 60000);
}}

function roleColor(role) {{
  if (role.indexOf('voice') >= 0) return '#4a90d9';
  if (role.indexOf('music') >= 0) return '#7b68ee';
  return '#e67e22';
}}

function renderTimeline(plan) {{
  const tl = document.getElementById('timeline');
  tl.innerHTML = '';
  if (!plan || !plan.tracks) return;
  const total = msTotal(plan);
  const scale = (tl.clientWidth || 600) / total;
  let row = 0;
  const rowHeight = 28;
  for (const tr of plan.tracks) {{
    for (const ev of tr.events || []) {{
      const div = document.createElement('div');
      div.className = 'ev';
      div.style.left = ((ev.start_ms|0) * scale) + 'px';
      div.style.width = Math.max(2, (ev.duration_ms|0) * scale) + 'px';
      div.style.top = (4 + row * rowHeight) + 'px';
      div.style.background = roleColor(tr.track_role || '');
      div.textContent = (ev.event_id || '').slice(0, 12);
      div.dataset.trackId = tr.track_id;
      div.dataset.eventId = ev.event_id;
      div.onclick = () => selectEvent(tr, ev, div);
      tl.appendChild(div);
    }}
    row++;
  }}
  tl.style.height = Math.max(120, 8 + row * rowHeight) + 'px';
}}

function selectEvent(tr, ev, el) {{
  document.querySelectorAll('.ev').forEach(e => e.classList.remove('solo'));
  el.classList.add('solo');
  selected = {{ track_id: tr.track_id, event_id: ev.event_id, tr, ev }};
  const ar = ev.asset_ref || {{}};
  document.getElementById('evdetail').textContent = JSON.stringify({{
    track_role: tr.track_role,
    event_id: ev.event_id,
    asset_id: ar.asset_id,
    generation_prompt: ar.generation_prompt,
    volume_db: ev.volume_db,
    pan: ev.pan,
    automation: ev.automation
  }}, null, 2);
}}

document.getElementById('regen').onclick = async () => {{
  const msg = document.getElementById('regenmsg');
  msg.textContent = '';
  if (!selected) {{ msg.textContent = 'Select an event first'; return; }}
  msg.textContent = 'Regenerating…';
  const r = await fetch('/api/v1/podcast/production/' + encodeURIComponent(TASK) + '/regenerate-event', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ track_id: selected.track_id, event_id: selected.event_id }})
  }});
  const j = await r.json().catch(() => ({{}}));
  if (!r.ok) {{ msg.textContent = j.detail || r.statusText; return; }}
  msg.textContent = 'Done. Reloading…';
  if (j.audio_url) document.getElementById('player').src = j.audio_url;
  await load();
}};

load();
</script>
</body></html>"""


@router.get("/audition/{task_id}", response_class=HTMLResponse)
async def audition_page(task_id: str) -> HTMLResponse:
    return HTMLResponse(_audition_html(task_id))


def _admin_html() -> str:
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Production renders</title>
<style>
body { font-family: system-ui, sans-serif; margin: 1rem; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; font-size: 14px; }
.pass { color: green; } .fail { color: #c00; } .unk { color: #666; }
a { color: #06c; }
</style></head><body>
<h1>Production renders (last 50)</h1>
<table id="t"><thead><tr>
<th>Task</th><th>Time</th><th>QA</th><th>Drift (s)</th><th>Audition</th>
</tr></thead><tbody></tbody></table>
<script>
async function load() {
  const r = await fetch('/api/v1/podcast/admin/production-renders');
  const j = await r.json();
  const tb = document.querySelector('#t tbody');
  tb.innerHTML = '';
  for (const row of j.renders || []) {
    const tr = document.createElement('tr');
    const qa = row.qa_all_passed;
    const qaCell = qa === true ? '<span class="pass">pass</span>' : qa === false ? '<span class="fail">fail</span>' : '<span class="unk">—</span>';
    tr.innerHTML = '<td>' + (row.task_id || '') + '</td>' +
      '<td>' + (row.created_at || '') + '</td>' +
      '<td>' + qaCell + '</td>' +
      '<td>' + (row.duration_drift_sec != null ? row.duration_drift_sec : '—') + '</td>' +
      '<td><a href="/audition/' + encodeURIComponent(row.task_id) + '">Open</a></td>';
    tb.appendChild(tr);
  }
}
load();
</script>
</body></html>"""


@router.get("/admin/production", response_class=HTMLResponse)
async def admin_production_page() -> HTMLResponse:
    return HTMLResponse(_admin_html())
