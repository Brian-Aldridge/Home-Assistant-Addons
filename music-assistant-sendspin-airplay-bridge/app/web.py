from __future__ import annotations

import html
import logging

from aiohttp import web

from .bridge import SendSpinAirPlayBridge
from .config import AdvertisedTarget, AppConfig, load_managed_targets, save_managed_targets


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
    except Exception as err:
        LOGGER.exception("Failed to load players for UI: %s", err)
        players = []
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
            f"<td><input type='checkbox' name='enabled::{html.escape(player_id)}' {checked}></td>"
            f"<td>{html.escape(display_name)}<div class='meta'>{html.escape(player_id)}</div></td>"
            f"<td>{html.escape(str(player['provider']))}</td>"
            f"<td>{badge_text}</td>"
            f"<td><input type='text' name='name::{html.escape(player_id)}' value='{html.escape(suggested_name)}'></td>"
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

    body = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SendSpin AirPlay Bridge</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
    input[type=text] {{ width: 100%; box-sizing: border-box; padding: 6px; }}
    .toolbar {{ display: flex; gap: 12px; margin: 16px 0; }}
    button {{ padding: 10px 14px; }}
    .meta {{ color: #666; font-size: 12px; margin-top: 4px; }}
    .badge {{ display: inline-block; padding: 2px 6px; border: 1px solid #999; border-radius: 6px; margin-right: 6px; font-size: 12px; }}
    .status {{ margin-bottom: 16px; padding: 10px; background: #f4f4f4; }}
    .error {{ background: #fdecec; color: #8a1f1f; }}
  </style>
</head>
<body>
  <h1>SendSpin AirPlay Bridge</h1>
  <p>Music Assistant server: {html.escape(config.music_assistant_url)}</p>
  {status_html}
  <form method="post" action="/save">
    <div class="toolbar">
      <button type="submit">Save target selection</button>
    </div>
    <table>
      <thead>
        <tr>
          <th>Enable</th>
          <th>Music Assistant player or group</th>
          <th>Provider</th>
          <th>Tags</th>
          <th>AirPlay target name</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </form>
  <form method="post" action="/sync">
    <div class="toolbar">
      <button type="submit">Run sync now</button>
    </div>
  </form>
</body>
</html>"""
    return web.Response(text=body, content_type="text/html")


async def handle_save(request: web.Request) -> web.Response:
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
    return web.HTTPFound("/")


async def handle_sync(request: web.Request) -> web.Response:
    config: AppConfig = request.app["config"]
    bridge: SendSpinAirPlayBridge = request.app["bridge"]
    config.advertised_targets = load_managed_targets()
    try:
        await bridge.run_sync()
    except Exception as err:
        LOGGER.exception("Manual sync failed: %s", err)
    return web.HTTPFound("/")
