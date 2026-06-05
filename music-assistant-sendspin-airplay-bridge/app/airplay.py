from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import AdvertisedTarget


AIRPLAY_PROVIDER_DOMAIN = "airplay_receiver"


@dataclass(slots=True)
class PlayerRecord:
    player_id: str
    display_name: str
    provider: str | None
    is_group: bool
    is_sendspin_candidate: bool
    raw: dict[str, Any]


@dataclass(slots=True)
class ProviderMatch:
    instance_id: str | None
    provider_domain: str
    values: dict[str, Any]
    target: AdvertisedTarget


def normalize_player(player: dict[str, Any]) -> PlayerRecord:
    provider = (
        player.get("provider")
        or player.get("provider_domain")
        or player.get("provider_instance")
        or ""
    )
    player_id = str(player.get("player_id") or "")
    display_name = str(player.get("display_name") or player_id)
    group_childs = player.get("group_childs") or player.get("group_members") or []
    is_group = bool(player.get("group_player") or group_childs)
    provider_name = str(provider).lower() if provider else ""
    raw_text = _flatten_text(player)
    provider_text = f"{provider_name} {player_id} {display_name} {raw_text}".lower()
    endpoint_text = f"{player_id} {display_name}".lower()
    is_sendspin_candidate = _is_sendspin_candidate(
        provider_name=provider_name,
        player_id=player_id,
        display_name=display_name,
        is_group=is_group,
        provider_text=provider_text,
        endpoint_text=endpoint_text,
    )

    return PlayerRecord(
        player_id=player_id,
        display_name=display_name,
        provider=str(provider) if provider else None,
        is_group=is_group,
        is_sendspin_candidate=is_sendspin_candidate,
        raw=player,
    )


def _is_sendspin_candidate(
    *,
    provider_name: str,
    player_id: str,
    display_name: str,
    is_group: bool,
    provider_text: str,
    endpoint_text: str,
) -> bool:
    if is_group or provider_name == "sync_group":
        return True

    if player_id.startswith("spb_"):
        return True

    if provider_name in {"hass_players", "universal_player"}:
        if _looks_like_video_endpoint(endpoint_text):
            return False
        return _looks_like_audio_endpoint(endpoint_text)

    if provider_name == "sendspin":
        if _looks_like_browser_endpoint(provider_text):
            return False
        return True

    if "sendspin" in provider_text:
        return not _looks_like_browser_endpoint(provider_text)

    return False


def _looks_like_audio_endpoint(endpoint_text: str) -> bool:
    tokens = {
        "speaker",
        "speakers",
        "assistant",
        "soundbar",
        "audio",
        "receiver",
        "amp",
        "music",
        "group",
        "synced",
    }
    return any(token in endpoint_text for token in tokens)


def _looks_like_video_endpoint(endpoint_text: str) -> bool:
    tokens = {
        " tv",
        "_tv",
        "television",
        "display",
        "projector",
        "roku",
        "webos",
        "ultra",
    }
    candidate_text = f" {endpoint_text}"
    return any(token in candidate_text for token in tokens)


def _looks_like_browser_endpoint(provider_text: str) -> bool:
    tokens = {
        "pwa",
        "browser",
        "edge",
        "chrome",
        "firefox",
        "safari",
        "webkit",
        "tab",
        "window",
    }
    return any(token in provider_text for token in tokens)


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return ""


def build_provider_values(target: AdvertisedTarget) -> dict[str, Any]:
    return {
        "name": target.name,
        "enabled": target.enabled,
        "mass_player_id": target.ma_player_id,
        "airplay_name": target.name,
    }


def match_existing_provider(
    target: AdvertisedTarget,
    provider_configs: list[dict[str, Any]],
) -> ProviderMatch:
    for provider in provider_configs:
        provider_domain = str(
            provider.get("provider_domain") or provider.get("domain") or ""
        )
        if provider_domain != AIRPLAY_PROVIDER_DOMAIN:
            continue
        values = provider.get("values") or {}
        if values.get("mass_player_id") == target.ma_player_id:
            return ProviderMatch(
                instance_id=str(provider.get("instance_id") or ""),
                provider_domain=AIRPLAY_PROVIDER_DOMAIN,
                values=build_provider_values(target),
                target=target,
            )
        if values.get("airplay_name") == target.name or provider.get("name") == target.name:
            return ProviderMatch(
                instance_id=str(provider.get("instance_id") or ""),
                provider_domain=AIRPLAY_PROVIDER_DOMAIN,
                values=build_provider_values(target),
                target=target,
            )

    return ProviderMatch(
        instance_id=None,
        provider_domain=AIRPLAY_PROVIDER_DOMAIN,
        values=build_provider_values(target),
        target=target,
    )
