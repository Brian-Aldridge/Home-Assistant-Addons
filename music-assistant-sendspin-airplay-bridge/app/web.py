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
    return app


async def handle_index(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    current_targets = {item.ma_player_id: item for item in load_managed_targets()}
    error_text = ""
    try:
        players = await bridge.fetch_players()
        interfaces = await bridge.fetch_mdns_interfaces()
    except Exception as err:
        LOGGER.exception("Failed to load players for UI: %s", err)
        players = []
        interfaces = [{"name": "Automatic", "value": ""}]
        error_text = html.escape(str(err))

    summary = bridge.last_summary
    rows: list[str] = []
    for player in sorted(players, key=lambda item: str(item["display_name"]).lower()):
        player_id = str(player["player_id"])
        display_name = str(player["display_name"])
        existing = current_targets.get(player_id)
        checked = "checked" if existing and existing.enabled else ""
        suggested_name = existing.name if existing else display_name
        badges: list[str] = []
        if player["is_group"]:
            badges.append("group")
        if player["is_sendspin_candidate"]:
            badges.append("sendspin")
        badge_text = " ".join(
            f"<span class='badge'>{html.escape(tag)}</span>" for tag in badges
        )
        rows.append(
            "<tr>"
            f"<td data-label='Enable'><input type='checkbox' name='enabled::{html.escape(player_id)}' {checked}></td>"
            f"<td data-label='Music Assistant player or group' class='player-col'>{html.escape(display_name)}<div class='meta'>{html.escape(player_id)}</div></td>"
            f"<td data-label='Provider'>{html.escape(str(player['provider']))}</td>"
            f"<td data-label='Tags'>{badge_text}</td>"
            f"<td data-label='AirPlay target name'><input type='text' name='name::{html.escape(player_id)}' value='{html.escape(suggested_name)}'></td>"
            "</tr>"
        )

    status_html = ""
    if summary:
        status_html = (
            f"<div class='status'>Last sync: configured {summary.configured_targets}, "
            f"enabled {summary.enabled_targets}, updated {summary.created_or_updated}.</div>"
        )
    elif error_text:
        status_html = f"<div class='status error'>Player list failed: {error_text}</div>"

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
    .player-col {{
      font-weight: 600;
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
    input[type=checkbox] {{
      width: 18px;
      height: 18px;
      accent-color: var(--accent-color);
      margin-top: 4px;
    }}
    @media (max-width: 900px) {{
      body {{ padding: 16px; }}
      h1 {{ font-size: 1.7rem; }}
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
  <div class="shell">
    <h1>SendSpin AirPlay Bridge</h1>
    <p>Music Assistant server: {html.escape(config.music_assistant_url)}</p>
    {status_html}
    <form method="post" action="save" class="panel">
      <div class="settings">
        <div class="field">
          <label for="mdns_interface">mDNS interface</label>
          <select id="mdns_interface" name="mdns_interface">
            {''.join(interface_options)}
          </select>
          <div class="meta">Use Automatic unless you need to pin multicast traffic to a specific interface.</div>
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
    <form method="post" action="sync" class="toolbar">
      <button type="submit" class="secondary">Run sync now</button>
    </div>
  </div>
</body>
</html>"""
    return web.Response(text=body, content_type="text/html")


async def handle_save(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    try:
        players = await bridge.fetch_players()
    except Exception as err:
        LOGGER.exception("Unable to save targets because players could not be loaded: %s", err)
        return web.HTTPFound("/")

    player_ids = {str(item["player_id"]) for item in players}
    data = await request.post()
    targets: list[AdvertisedTarget] = []
    for player_id in sorted(player_ids):
        enabled = data.get(f"enabled::{player_id}") == "on"
        if not enabled:
            continue
        name = str(data.get(f"name::{player_id}", "")).strip()
        if not name:
            name = next(
                str(item["display_name"])
                for item in players
                if str(item["player_id"]) == player_id
            )
        targets.append(
            AdvertisedTarget(name=name, ma_player_id=player_id, enabled=True)
        )

    save_managed_targets(targets)
    config.mdns_interface = str(data.get("mdns_interface", "")).strip() or None
    save_runtime_overrides(config)
    return web.HTTPFound("./")


async def handle_sync(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    config.advertised_targets = load_managed_targets()
    try:
        await bridge.run_sync()
    except Exception as err:
        LOGGER.exception("Manual sync failed: %s", err)
    return web.HTTPFound("./")
