from __future__ import annotations

import logging
from dataclasses import dataclass

from .airplay import AIRPLAY_PROVIDER_DOMAIN, match_existing_provider, normalize_player
from .config import AppConfig
from .ma_client import MusicAssistantClient


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncSummary:
    configured_targets: int
    enabled_targets: int
    sendspin_candidates: int
    groups_seen: int
    created_or_updated: int


class SendSpinAirPlayBridge:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def run_sync(self) -> SyncSummary:
        async with MusicAssistantClient(
            self.config.music_assistant_url,
            self.config.music_assistant_token,
        ) as client:
            server_info = await client.probe_websocket()
            LOGGER.info(
                "Connected to Music Assistant server_id=%s version=%s",
                server_info.get("server_id", "unknown"),
                server_info.get("server_version", "unknown"),
            )

            manifests = await client.get_provider_manifests()
            manifest_domains = {
                str(item.get("domain") or item.get("provider_domain") or "")
                for item in manifests
            }
            if manifests and AIRPLAY_PROVIDER_DOMAIN not in manifest_domains:
                raise RuntimeError(
                    "Music Assistant does not report the airplay_receiver provider. "
                    "Install or enable the official AirPlay Receiver plugin first."
                )

            players = [normalize_player(item) for item in await client.get_players()]
            provider_configs = await client.get_provider_configs()

            player_index = {player.player_id: player for player in players}
            groups_seen = sum(1 for player in players if player.is_group)
            sendspin_candidates = sum(
                1 for player in players if player.is_sendspin_candidate
            )

            LOGGER.info(
                "Discovered %s players, %s groups, %s SendSpin candidates",
                len(players),
                groups_seen,
                sendspin_candidates,
            )
            for player in players:
                marker = []
                if player.is_group:
                    marker.append("group")
                if player.is_sendspin_candidate:
                    marker.append("sendspin-candidate")
                suffix = f" ({', '.join(marker)})" if marker else ""
                LOGGER.info(
                    "Player: id=%s name=%s provider=%s%s",
                    player.player_id,
                    player.display_name,
                    player.provider or "unknown",
                    suffix,
                )

            updated = 0
            enabled_targets = 0
            for target in self.config.advertised_targets:
                if target.enabled:
                    enabled_targets += 1
                player = player_index.get(target.ma_player_id)
                if player is None:
                    LOGGER.error(
                        "Configured target '%s' references missing player/group id '%s'",
                        target.name,
                        target.ma_player_id,
                    )
                    continue

                if not player.is_sendspin_candidate:
                    LOGGER.warning(
                        "Target '%s' points at player '%s', but it is not clearly identifiable "
                        "as SendSpin from the Music Assistant player metadata",
                        target.name,
                        player.display_name,
                    )

                if player.is_group:
                    LOGGER.info(
                        "Target '%s' maps to MA group '%s'; sync will be preserved by MA",
                        target.name,
                        player.display_name,
                    )

                match = match_existing_provider(target, provider_configs)
                await client.save_provider_config(
                    match.provider_domain,
                    match.values,
                    match.instance_id,
                )
                updated += 1

                action = "updated" if match.instance_id else "created"
                LOGGER.info(
                    "AirPlay target %s: name=%s ma_player_id=%s",
                    action,
                    target.name,
                    target.ma_player_id,
                )

            return SyncSummary(
                configured_targets=len(self.config.advertised_targets),
                enabled_targets=enabled_targets,
                sendspin_candidates=sendspin_candidates,
                groups_seen=groups_seen,
                created_or_updated=updated,
            )
