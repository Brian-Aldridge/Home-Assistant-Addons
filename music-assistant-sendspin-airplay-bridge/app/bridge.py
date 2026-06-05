from __future__ import annotations

import logging
import re
import socket
from dataclasses import dataclass

from .airplay import AIRPLAY_PROVIDER_DOMAIN, match_existing_provider, normalize_player
from .config import AppConfig, AdvertisedTarget, save_managed_targets
from .ma_client import MusicAssistantClient


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncSummary:
    configured_targets: int
    enabled_targets: int
    sendspin_candidates: int
    groups_seen: int
    created_or_updated: int


@dataclass(slots=True)
class PlayerChoice:
    logical_key: str
    player_id: str
    display_name: str
    provider: str
    is_group: bool
    is_sendspin_candidate: bool
    duplicate_count: int
    alternate_player_ids: list[str]
    alternate_providers: list[str]


class SendSpinAirPlayBridge:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._last_summary: SyncSummary | None = None

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
            choices = self._build_player_choices(players)

            player_index = {player.player_id: player for player in players}
            choice_index = {choice.logical_key: choice for choice in choices}
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
            persisted_targets: list[AdvertisedTarget] = []
            for target in self.config.advertised_targets:
                if target.enabled:
                    enabled_targets += 1
                resolved_target = self._resolve_target(target, choices, player_index, choice_index)
                player = player_index.get(resolved_target.ma_player_id)
                if player is None:
                    LOGGER.error(
                        "Configured target '%s' references missing player/group id '%s'",
                        resolved_target.name,
                        resolved_target.ma_player_id,
                    )
                    continue
                persisted_targets.append(resolved_target)

                if not player.is_sendspin_candidate:
                    LOGGER.warning(
                        "Target '%s' points at player '%s', but it is not clearly identifiable "
                        "as SendSpin from the Music Assistant player metadata",
                        resolved_target.name,
                        player.display_name,
                    )

                if player.is_group:
                    LOGGER.info(
                        "Target '%s' maps to MA group '%s'; sync will be preserved by MA",
                        resolved_target.name,
                        player.display_name,
                    )

                match = match_existing_provider(resolved_target, provider_configs)
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
                    resolved_target.name,
                    resolved_target.ma_player_id,
                )

            if persisted_targets and persisted_targets != self.config.advertised_targets:
                self.config.advertised_targets = persisted_targets
                save_managed_targets(persisted_targets)

            summary = SyncSummary(
                configured_targets=len(self.config.advertised_targets),
                enabled_targets=enabled_targets,
                sendspin_candidates=sendspin_candidates,
                groups_seen=groups_seen,
                created_or_updated=updated,
            )
            self._last_summary = summary
            return summary

    async def fetch_players(self) -> list[dict[str, object]]:
        async with MusicAssistantClient(
            self.config.music_assistant_url,
            self.config.music_assistant_token,
        ) as client:
            await client.probe_websocket()
            players = [normalize_player(item) for item in await client.get_players()]
            choices = self._build_player_choices(players)
            return [
                {
                    "logical_key": choice.logical_key,
                    "player_id": choice.player_id,
                    "display_name": choice.display_name,
                    "provider": choice.provider,
                    "is_group": choice.is_group,
                    "is_sendspin_candidate": choice.is_sendspin_candidate,
                    "duplicate_count": choice.duplicate_count,
                    "alternate_player_ids": choice.alternate_player_ids,
                    "alternate_providers": choice.alternate_providers,
                }
                for choice in choices
            ]

    async def fetch_mdns_interfaces(self) -> list[dict[str, str]]:
        interfaces: list[dict[str, str]] = [{"name": "Automatic", "value": ""}]
        seen: set[str] = set()
        for _, name in socket.if_nameindex():
            if name in seen:
                continue
            seen.add(name)
            interfaces.append({"name": name, "value": name})
        return interfaces

    @property
    def last_summary(self) -> SyncSummary | None:
        return self._last_summary

    def _build_player_choices(self, players: list) -> list[PlayerChoice]:
        clusters: dict[str, list] = {}
        for player in players:
            cluster_key = self._cluster_key(player.display_name)
            clusters.setdefault(cluster_key, []).append(player)

        choices: list[PlayerChoice] = []
        for cluster_players in clusters.values():
            sorted_players = sorted(cluster_players, key=self._player_priority_key)
            primary = sorted_players[0]
            logical_key = self._logical_key_for_choice(primary, cluster_players)
            alternates = [item.player_id for item in sorted_players[1:]]
            alternate_providers = [item.provider or "unknown" for item in sorted_players[1:]]
            choices.append(
                PlayerChoice(
                    logical_key=logical_key,
                    player_id=primary.player_id,
                    display_name=primary.display_name,
                    provider=primary.provider or "unknown",
                    is_group=primary.is_group,
                    is_sendspin_candidate=any(
                        item.is_sendspin_candidate for item in cluster_players
                    ),
                    duplicate_count=len(cluster_players),
                    alternate_player_ids=alternates,
                    alternate_providers=alternate_providers,
                )
            )
        choices.sort(key=lambda item: item.display_name.lower())
        return choices

    def _resolve_target(
        self,
        target: AdvertisedTarget,
        choices: list[PlayerChoice],
        player_index: dict[str, object],
        choice_index: dict[str, PlayerChoice],
    ) -> AdvertisedTarget:
        if target.logical_key:
            choice = choice_index.get(target.logical_key)
            if choice:
                if choice.player_id != target.ma_player_id:
                    LOGGER.info(
                        "Resolved target '%s' from stale player id '%s' to '%s' using logical key '%s'",
                        target.name,
                        target.ma_player_id,
                        choice.player_id,
                        target.logical_key,
                    )
                return AdvertisedTarget(
                    name=target.name,
                    ma_player_id=choice.player_id,
                    enabled=target.enabled,
                    logical_key=target.logical_key,
                )

        if target.ma_player_id in player_index:
            match = next(
                (
                    choice
                    for choice in choices
                    if choice.player_id == target.ma_player_id
                    or target.ma_player_id in choice.alternate_player_ids
                ),
                None,
            )
            return AdvertisedTarget(
                name=target.name,
                ma_player_id=target.ma_player_id,
                enabled=target.enabled,
                logical_key=match.logical_key if match else target.logical_key,
            )

        fallback_choice = next(
            (
                choice
                for choice in choices
                if self._normalize_name(choice.display_name)
                == self._normalize_name(target.name)
            ),
            None,
        )
        if fallback_choice:
            LOGGER.warning(
                "Recovered target '%s' by display-name fallback; binding to player id '%s'",
                target.name,
                fallback_choice.player_id,
            )
            return AdvertisedTarget(
                name=target.name,
                ma_player_id=fallback_choice.player_id,
                enabled=target.enabled,
                logical_key=fallback_choice.logical_key,
            )

        return target

    def _cluster_key(self, display_name: str) -> str:
        return f"name:{self._normalize_name(display_name)}"

    def _logical_key_for_choice(self, primary, cluster_players: list) -> str:
        normalized_name = self._normalize_name(primary.display_name)
        if any(player.is_group for player in cluster_players):
            return f"group:{normalized_name}"
        return f"speaker:{normalized_name}"

    def _player_priority_key(self, player) -> tuple[int, int, int, str]:
        provider = (player.provider or "").lower()
        if player.is_group or provider == "sync_group":
            rank = 0
        elif provider == "hass_players":
            rank = 1
        elif provider == "universal_player":
            rank = 3
        else:
            rank = 2
        entity_like = 0 if "." in player.player_id else 1
        sendspin_bonus = 0 if player.is_sendspin_candidate else 1
        return (rank, entity_like, sendspin_bonus, player.player_id.lower())

    def _normalize_name(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "unnamed"
