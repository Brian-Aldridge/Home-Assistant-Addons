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

    provider_text = f"{provider} {player_id} {display_name}".lower()
    is_sendspin_candidate = "sendspin" in provider_text or player_id.startswith("spb_")

    return PlayerRecord(
        player_id=player_id,
        display_name=display_name,
        provider=str(provider) if provider else None,
        is_group=is_group,
        is_sendspin_candidate=is_sendspin_candidate,
        raw=player,
    )


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
