from __future__ import annotations

import html
import logging

from aiohttp import web

from .bridge import SendSpinAirPlayBridge
from .config import (
    AdvertisedTarget,
    AppConfig,
    load_managed_targets,
    save_managed_targets,
    save_runtime_overrides,
)


LOGGER = logging.getLogger(__name__)


def create_app(config: AppConfig, bridge: SendSpinAirPlayBridge) -> web.Application:
    app = web.Application()
    app["config"] = config
    app["bridge"] = bridge
    app.router.add_get("/", handle_index)
    app.router.add_post("/save", handle_save)
    app.router.add_post("/sync", handle_sync)
    app.router.add_post("/cleanup", handle_cleanup)
    return app


async def handle_index(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    current_targets = load_managed_targets()
    targets_by_player_id = {item.ma_player_id: item for item in current_targets}
    targets_by_logical_key = {
        item.logical_key: item for item in current_targets if item.logical_key
    }
    error_text = ""
    action_status = html.escape(request.query.get("status", ""))
    try:
        dashboard = await bridge.fetch_dashboard_state(current_targets)
        players = list(dashboard["players"])
        target_rows = list(dashboard["targets"])
        receiver_rows = list(dashboard["receivers"])
        interfaces = await bridge.fetch_mdns_interfaces()
    except Exception as err:
        LOGGER.exception("Failed to load players for UI: %s", err)
        players = []
        target_rows = []
        receiver_rows = []
        interfaces = [{"name": "Automatic", "value": ""}]
        error_text = html.escape(str(err))

    summary = bridge.last_summary
    rows: list[str] = []
    for player in sorted(players, key=lambda item: str(item["effective_name"]).lower()):
        logical_key = str(player["logical_key"])
        player_id = str(player["player_id"])
        display_name = str(player["display_name"])
        effective_name = str(player.get("effective_name") or display_name)
        existing = targets_by_logical_key.get(logical_key) or targets_by_player_id.get(player_id)
        checked = "checked" if existing and existing.enabled else ""
        suggested_name = existing.name if existing else effective_name
        badges: list[str] = []
        if player["is_group"]:
            badges.append("group")
        if player["is_sendspin_candidate"]:
            badges.append("sendspin")
        if int(player["duplicate_count"]) > 1:
            badges.append(f"deduped {int(player['duplicate_count'])}x")
        badge_text = " ".join(
            f"<span class='badge'>{html.escape(tag)}</span>" for tag in badges
        )
        duplicate_note = ""
        alternate_providers = ", ".join(str(item) for item in player["alternate_providers"])
        if int(player["duplicate_count"]) > 1:
            duplicate_note = (
                f"<div class='meta'>Using preferred Music Assistant target. Hidden duplicates: "
                f"{html.escape(alternate_providers or 'same provider')}.</div>"
                f"<div class='meta advanced-only'>Preferred reason: {html.escape(str(player['preferred_reason']))}. "
                f"Alternate IDs: {html.escape(', '.join(str(v) for v in player['alternate_player_ids']) or 'none')}.</div>"
            )
        rows.append(
            "<tr class='player-row'"
            f" data-name='{html.escape((display_name + ' ' + effective_name).lower())}'"
            f" data-provider='{html.escape(str(player['provider']).lower())}'"
            f" data-selected='{'true' if existing and existing.enabled else 'false'}'"
            f" data-group='{'true' if player['is_group'] else 'false'}'"
            f" data-duplicate='{'true' if int(player['duplicate_count']) > 1 else 'false'}'"
            ">"
            f"<td data-label='Enable'><input type='checkbox' name='enabled::{html.escape(logical_key)}' {checked}></td>"
            f"<td data-label='Music Assistant player or group' class='player-col'>{html.escape(effective_name)}<div class='meta'>{html.escape(player_id)}</div>{duplicate_note}</td>"
            f"<td data-label='Provider'>{html.escape(str(player['provider']))}</td>"
            f"<td data-label='Tags'>{badge_text}</td>"
            f"<td data-label='AirPlay target name'><input type='text' name='name::{html.escape(logical_key)}' value='{html.escape(suggested_name)}'></td>"
            "</tr>"
        )

    target_summary_rows: list[str] = []
    for row in target_rows:
        status = str(row["status"])
        status_label = {
            "ready": "ready",
            "receiver_missing": "receiver missing",
            "player_missing": "player missing",
        }.get(status, status)
        status_badge = f"<span class='badge status-{html.escape(status)}'>{html.escape(status_label)}</span>"
        target_summary_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['name']))}</td>"
            f"<td>{status_badge}</td>"
            f"<td>{html.escape(str(row['resolved_display_name']))}</td>"
            f"<td><code>{html.escape(str(row['resolved_player_id']))}</code></td>"
            f"<td><code>{html.escape(str(row['receiver_instance_id']) or '-')}</code></td>"
            "</tr>"
        )

    receiver_inventory_rows: list[str] = []
    cleanup_count = 0
    for row in receiver_rows:
        if bool(row["cleanup_candidate"]):
            cleanup_count += 1
        flags = " ".join(
            f"<span class='badge'>{html.escape(str(flag))}</span>"
            for flag in row["status_flags"]
        )
        receiver_inventory_rows.append(
            "<tr class='receiver-row'"
            f" data-managed='{'true' if row['managed'] else 'false'}'"
            f" data-cleanup='{'true' if row['cleanup_candidate'] else 'false'}'"
            ">"
            f"<td>{html.escape(str(row['airplay_name']))}</td>"
            f"<td>{flags}</td>"
            f"<td>{html.escape(str(row['resolved_display_name']))}</td>"
            f"<td><code>{html.escape(str(row['mass_player_id']) or '-')}</code></td>"
            f"<td><code>{html.escape(str(row['instance_id']))}</code></td>"
            "<td>"
            + (
                f"<form method='post' action='cleanup' class='inline-form'>"
                f"<input type='hidden' name='instance_id' value='{html.escape(str(row['instance_id']))}'>"
                "<button type='submit' class='danger'>Remove</button>"
                "</form>"
                if bool(row["cleanup_candidate"]) and str(row["instance_id"])
                else "<span class='meta'>kept</span>"
            )
            + "</td>"
            "</tr>"
        )

    status_html = ""
    if summary:
        status_html = (
            f"<div class='status'>Last sync: configured {summary.configured_targets}, "
            f"enabled {summary.enabled_targets}, updated {summary.created_or_updated}. "
            f"Cleanup candidates: {cleanup_count}.</div>"
        )
    if error_text:
        status_html += f"<div class='status error'>Player list failed: {error_text}</div>"
    if action_status:
        status_html += f"<div class='status'>{action_status}</div>"

    selected_interface = config.mdns_interface or ""
    interface_options = []
    for interface in interfaces:
        value = str(interface["value"])
        selected = " selected" if value == selected_interface else ""
        label = html.escape(str(interface["name"]))
        interface_options.append(
            f"<option value='{html.escape(value)}'{selected}>{label}</option>"
        )

    body = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SendSpin AirPlay Bridge</title>
  <style>
    :root {{
      color-scheme: light dark;
      --page-bg: var(--primary-background-color, #111111);
      --card-bg: var(--card-background-color, #1c1c1c);
      --text-color: var(--primary-text-color, #f5f5f5);
      --secondary-text: var(--secondary-text-color, #b0b0b0);
      --border-color: var(--divider-color, rgba(255,255,255,0.12));
      --accent-color: var(--primary-color, #03a9f4);
      --accent-contrast: var(--text-primary-color, #ffffff);
      --muted-bg: var(--secondary-background-color, rgba(127,127,127,0.12));
      --success-bg: color-mix(in srgb, var(--accent-color) 10%, transparent);
      --error-bg: rgba(244, 67, 54, 0.12);
      --error-text: var(--error-color, #f44336);
      --input-bg: var(--ha-card-background, var(--card-bg));
      --shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--page-bg);
      color: var(--text-color);
      font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif);
      font-size: 14px;
      line-height: 1.5;
    }}
    .shell {{
      max-width: 1400px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 2.1rem;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: var(--secondary-text);
    }}
    .panel {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      box-shadow: var(--shadow);
      padding: 20px;
      margin-top: 20px;
    }}
    .panel-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .panel-header h2 {{
      margin: 0;
      font-size: 1.1rem;
    }}
    .status {{
      margin-top: 16px;
      padding: 12px 14px;
      background: var(--muted-bg);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      color: var(--text-color);
    }}
    .error {{
      background: var(--error-bg);
      color: var(--error-text);
    }}
    .settings {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 20px;
    }}
    .filters {{
      display: grid;
      grid-template-columns: minmax(220px, 1.6fr) repeat(3, minmax(160px, 1fr));
      gap: 12px;
      margin: 16px 0 20px;
    }}
    .field label {{
      display: block;
      margin-bottom: 6px;
      color: var(--secondary-text);
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    input[type=text], select {{
      width: 100%;
      min-height: 40px;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border-color);
      background: var(--input-bg);
      color: var(--text-color);
      outline: none;
    }}
    input[type=text]:focus, select:focus {{
      border-color: var(--accent-color);
      box-shadow: 0 0 0 1px var(--accent-color);
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      color: var(--secondary-text);
    }}
    .toolbar {{
      display: flex;
      gap: 12px;
      margin: 16px 0 0;
      flex-wrap: wrap;
    }}
    button {{
      min-height: 40px;
      padding: 0 16px;
      border: 0;
      border-radius: 10px;
      background: var(--accent-color);
      color: var(--accent-contrast);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }}
    button.secondary {{
      background: transparent;
      color: var(--text-color);
      border: 1px solid var(--border-color);
    }}
    button.danger {{
      background: rgba(244, 67, 54, 0.16);
      color: #ff8f8f;
      border: 1px solid rgba(244, 67, 54, 0.35);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    thead th {{
      color: var(--secondary-text);
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 0 8px 12px;
      text-align: left;
    }}
    th, td {{
      border-bottom: 1px solid var(--border-color);
      padding: 12px 8px;
      text-align: left;
      vertical-align: top;
    }}
    tbody tr:hover {{
      background: color-mix(in srgb, var(--accent-color) 4%, transparent);
    }}
    .meta {{
      color: var(--secondary-text);
      font-size: 12px;
      margin-top: 4px;
      overflow-wrap: anywhere;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 8px;
      border: 1px solid var(--border-color);
      border-radius: 999px;
      margin-right: 6px;
      margin-bottom: 6px;
      font-size: 12px;
      color: var(--secondary-text);
      background: var(--muted-bg);
    }}
    .status-ready {{
      color: #7bd88f;
      border-color: rgba(123,216,143,0.35);
    }}
    .status-receiver_missing, .status-player_missing {{
      color: #ffb86c;
      border-color: rgba(255,184,108,0.35);
    }}
    .player-col {{
      font-weight: 600;
    }}
    .advanced-only {{
      display: none;
    }}
    .show-advanced .advanced-only {{
      display: block;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 20px;
    }}
    .metric {{
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px;
      background: var(--muted-bg);
    }}
    .metric-label {{
      color: var(--secondary-text);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .metric-value {{
      margin-top: 6px;
      font-size: 20px;
      font-weight: 700;
    }}
    .checkbox-cell {{
      width: 88px;
    }}
    .provider-col {{
      width: 18%;
    }}
    .tags-col {{
      width: 14%;
    }}
    .name-col {{
      width: 28%;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    .inline-form {{
      display: inline;
    }}
    .section-stack {{
      display: grid;
      gap: 20px;
      margin-top: 20px;
    }}
    input[type=checkbox] {{
      width: 18px;
      height: 18px;
      accent-color: var(--accent-color);
      margin-top: 4px;
    }}
    @media (max-width: 900px) {{
      body {{ padding: 16px; }}
      h1 {{ font-size: 1.7rem; }}
      .filters {{ grid-template-columns: 1fr; }}
      table, thead, tbody, th, td, tr {{ display: block; }}
      thead {{ display: none; }}
      tbody tr {{
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
      }}
      tbody td {{
        border: 0;
        padding: 8px 0;
      }}
      tbody td::before {{
        content: attr(data-label);
        display: block;
        color: var(--secondary-text);
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 6px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell" id="app-shell">
    <h1>SendSpin AirPlay Bridge</h1>
    <p>Music Assistant server: {html.escape(config.music_assistant_url)}</p>
    {status_html}
    <div class="metrics">
      <div class="metric"><div class="metric-label">Visible targets</div><div class="metric-value">{len(players)}</div></div>
      <div class="metric"><div class="metric-label">Selected targets</div><div class="metric-value">{len(target_rows)}</div></div>
      <div class="metric"><div class="metric-label">AirPlay receivers</div><div class="metric-value">{len(receiver_rows)}</div></div>
      <div class="metric"><div class="metric-label">Cleanup candidates</div><div class="metric-value">{cleanup_count}</div></div>
    </div>
    <form method="post" action="save" class="panel">
      <div class="panel-header">
        <div>
          <h2>Available targets</h2>
          <div class="meta">Search, filter, and select one stable target per logical speaker or group.</div>
        </div>
      </div>
      <div class="settings">
        <div class="field">
          <label for="mdns_interface">mDNS interface</label>
          <select id="mdns_interface" name="mdns_interface">
            {''.join(interface_options)}
          </select>
          <div class="meta">Use Automatic unless you need to pin multicast traffic to a specific interface.</div>
        </div>
      </div>
      <div class="filters">
        <div class="field">
          <label for="search">Search targets</label>
          <input type="text" id="search" placeholder="Filter by name or provider">
        </div>
        <div class="field">
          <label for="filter-type">Type</label>
          <select id="filter-type">
            <option value="all">All targets</option>
            <option value="selected">Selected only</option>
            <option value="groups">Groups only</option>
            <option value="duplicates">Deduped only</option>
          </select>
        </div>
        <div class="field">
          <label for="show-advanced">Advanced</label>
          <select id="show-advanced">
            <option value="off">Hide details</option>
            <option value="on">Show details</option>
          </select>
        </div>
        <div class="field">
          <label for="receiver-filter">Receiver inventory</label>
          <select id="receiver-filter">
            <option value="all">All receivers</option>
            <option value="cleanup">Cleanup candidates</option>
            <option value="managed">Managed only</option>
          </select>
        </div>
      </div>
      <div class="toolbar">
        <button type="submit">Save target selection</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="checkbox-cell">Enable</th>
              <th>Music Assistant player or group</th>
              <th class="provider-col">Provider</th>
              <th class="tags-col">Tags</th>
              <th class="name-col">AirPlay target name</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
    </form>
    <div class="section-stack">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Selected target health</h2>
            <div class="meta">Current mapping and receiver state for the targets this add-on manages.</div>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>AirPlay target</th>
                <th>Status</th>
                <th>Resolved MA target</th>
                <th>Player ID</th>
                <th>Receiver instance</th>
              </tr>
            </thead>
            <tbody>
              {''.join(target_summary_rows) or "<tr><td colspan='5'>No targets selected yet.</td></tr>"}
            </tbody>
          </table>
        </div>
      </section>
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>AirPlay receiver inventory</h2>
            <div class="meta">Managed and unmanaged Music Assistant AirPlay Receiver instances. Cleanup candidates are highlighted so you can remove them in Music Assistant if needed.</div>
          </div>
          <form method="post" action="cleanup" class="inline-form">
            <input type="hidden" name="cleanup_mode" value="all_candidates">
            <button type="submit" class="danger">Remove cleanup candidates</button>
          </form>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>AirPlay name</th>
                <th>Status</th>
                <th>Resolved player</th>
                <th>MA player ID</th>
                <th>Instance ID</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="receiver-table">
              {''.join(receiver_inventory_rows) or "<tr><td colspan='6'>No AirPlay receiver instances found.</td></tr>"}
            </tbody>
          </table>
        </div>
      </section>
    </div>
    <form method="post" action="sync" class="toolbar">
      <button type="submit" class="secondary">Run sync now</button>
    </form>
  </div>
  <script>
    const shell = document.getElementById('app-shell');
    const searchInput = document.getElementById('search');
    const filterType = document.getElementById('filter-type');
    const advancedToggle = document.getElementById('show-advanced');
    const receiverFilter = document.getElementById('receiver-filter');

    function applyPlayerFilters() {{
      const query = (searchInput.value || '').trim().toLowerCase();
      const type = filterType.value;
      const showAdvanced = advancedToggle.value === 'on';
      shell.classList.toggle('show-advanced', showAdvanced);

      document.querySelectorAll('.player-row').forEach((row) => {{
        const haystack = `${{row.dataset.name}} ${{row.dataset.provider}}`;
        const matchesQuery = !query || haystack.includes(query);
        const matchesType =
          type === 'all' ||
          (type === 'selected' && row.dataset.selected === 'true') ||
          (type === 'groups' && row.dataset.group === 'true') ||
          (type === 'duplicates' && row.dataset.duplicate === 'true');
        row.style.display = matchesQuery && matchesType ? '' : 'none';
      }});
    }}

    function applyReceiverFilters() {{
      const filter = receiverFilter.value;
      document.querySelectorAll('.receiver-row').forEach((row) => {{
        const visible =
          filter === 'all' ||
          (filter === 'cleanup' && row.dataset.cleanup === 'true') ||
          (filter === 'managed' && row.dataset.managed === 'true');
        row.style.display = visible ? '' : 'none';
      }});
    }}

    searchInput.addEventListener('input', applyPlayerFilters);
    filterType.addEventListener('change', applyPlayerFilters);
    advancedToggle.addEventListener('change', applyPlayerFilters);
    receiverFilter.addEventListener('change', applyReceiverFilters);
    applyPlayerFilters();
    applyReceiverFilters();
  </script>
</body>
</html>"""
    return web.Response(text=body, content_type="text/html")


async def handle_save(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    previous_targets = load_managed_targets()
    try:
        players = await bridge.fetch_players()
    except Exception as err:
        LOGGER.exception("Unable to save targets because players could not be loaded: %s", err)
        return web.HTTPFound("./")

    players_by_key = {str(item["logical_key"]): item for item in players}
    data = await request.post()
    targets: list[AdvertisedTarget] = []
    for logical_key in sorted(players_by_key):
        enabled = data.get(f"enabled::{logical_key}") == "on"
        if not enabled:
            continue
        player = players_by_key[logical_key]
        player_id = str(player["player_id"])
        name = str(data.get(f"name::{logical_key}", "")).strip()
        if not name:
            name = str(player["display_name"])
        targets.append(
            AdvertisedTarget(
                name=name,
                ma_player_id=player_id,
                enabled=True,
                logical_key=logical_key,
            )
        )

    save_managed_targets(targets)
    config.mdns_interface = str(data.get("mdns_interface", "")).strip() or None
    save_runtime_overrides(config)
    status_parts = ["Target selection saved"]
    try:
        cleanup_result = await bridge.remove_disabled_targets(previous_targets, targets)
        if cleanup_result["removed"]:
            status_parts.append(
                f"removed {len(cleanup_result['removed'])} disabled receiver(s)"
            )
        if cleanup_result["skipped"]:
            status_parts.append(
                f"skipped {len(cleanup_result['skipped'])} target(s) with no receiver to remove"
            )
    except Exception as err:
        LOGGER.exception("Failed removing disabled targets: %s", err)
        status_parts.append(f"cleanup failed: {err}")

    from urllib.parse import quote
    return web.HTTPFound(f"./?status={quote('; '.join(status_parts))}")


async def handle_sync(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    config.advertised_targets = load_managed_targets()
    try:
        await bridge.run_sync()
    except Exception as err:
        LOGGER.exception("Manual sync failed: %s", err)
    return web.HTTPFound("./")


async def handle_cleanup(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    config.advertised_targets = load_managed_targets()
    data = await request.post()
    cleanup_mode = str(data.get("cleanup_mode", "")).strip()
    instance_id = str(data.get("instance_id", "")).strip()
    try:
        result = await bridge.cleanup_receivers(
            config.advertised_targets,
            instance_ids=[instance_id] if instance_id else [],
            remove_all_candidates=(cleanup_mode == "all_candidates"),
        )
        message = f"Cleanup removed {len(result['removed'])} receiver(s)"
        if result["skipped"]:
            message += f"; skipped {len(result['skipped'])}"
    except Exception as err:
        LOGGER.exception("Cleanup failed: %s", err)
        message = f"Cleanup failed: {err}"
    from urllib.parse import quote
    return web.HTTPFound(f"./?status={quote(message)}")
