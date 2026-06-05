from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OPTIONS_PATH = Path("/data/options.json")
MANAGED_TARGETS_PATH = Path("/data/managed_targets.json")


@dataclass(slots=True)
class AdvertisedTarget:
    name: str
    ma_player_id: str
    enabled: bool = True


@dataclass(slots=True)
class AppConfig:
    music_assistant_url: str
    music_assistant_token: str | None
    advertised_targets: list[AdvertisedTarget]
    log_level: str
    mdns_interface: str | None
    airplay_backend: str
    sync_interval_seconds: int = 300


def _require_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Option '{key}' must be a non-empty string")
    return value.strip()


def load_config(path: Path = OPTIONS_PATH) -> AppConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))

    targets = load_managed_targets()
    if not targets:
        targets = load_legacy_option_targets(raw)

    url = _require_string(raw, "music_assistant_url").rstrip("/")
    token = raw.get("music_assistant_token") or None
    if token is not None and not isinstance(token, str):
        raise ValueError("Option 'music_assistant_token' must be a string")

    mdns_interface = raw.get("mdns_interface") or None
    if mdns_interface is not None and not isinstance(mdns_interface, str):
        raise ValueError("Option 'mdns_interface' must be a string")

    airplay_backend = _require_string(raw, "airplay_backend")
    if airplay_backend != "shairport-sync":
        raise ValueError("Only 'shairport-sync' is supported in v1")

    log_level = _require_string(raw, "log_level").lower()

    return AppConfig(
        music_assistant_url=url,
        music_assistant_token=token,
        advertised_targets=targets,
        log_level=log_level,
        mdns_interface=mdns_interface,
        airplay_backend=airplay_backend,
    )


def load_legacy_option_targets(raw: dict[str, Any]) -> list[AdvertisedTarget]:
    targets: list[AdvertisedTarget] = []
    for index, item in enumerate(raw.get("advertised_targets", [])):
        if not isinstance(item, dict):
            raise ValueError(f"advertised_targets[{index}] must be an object")
        name = _require_string(item, "name")
        ma_player_id = _require_string(item, "ma_player_id")
        enabled = bool(item.get("enabled", True))
        targets.append(
            AdvertisedTarget(name=name, ma_player_id=ma_player_id, enabled=enabled)
        )
    return targets


def load_managed_targets(path: Path = MANAGED_TARGETS_PATH) -> list[AdvertisedTarget]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("managed_targets.json must contain a list")
    targets: list[AdvertisedTarget] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"managed_targets[{index}] must be an object")
        name = _require_string(item, "name")
        ma_player_id = _require_string(item, "ma_player_id")
        enabled = bool(item.get("enabled", True))
        targets.append(
            AdvertisedTarget(name=name, ma_player_id=ma_player_id, enabled=enabled)
        )
    return targets


def save_managed_targets(
    targets: list[AdvertisedTarget],
    path: Path = MANAGED_TARGETS_PATH,
) -> None:
    payload = [
        {
            "name": item.name,
            "ma_player_id": item.ma_player_id,
            "enabled": item.enabled,
        }
        for item in targets
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
