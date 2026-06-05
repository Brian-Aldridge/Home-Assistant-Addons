from __future__ import annotations

import asyncio
import logging

from aiohttp import web

from .bridge import SendSpinAirPlayBridge
from .config import load_config
from .logging_setup import configure_logging
from .web import create_app


LOGGER = logging.getLogger(__name__)


async def run_forever() -> None:
    config = load_config()
    configure_logging(config.log_level)

    LOGGER.info("Music Assistant URL: %s", config.music_assistant_url)
    LOGGER.info("Configured AirPlay backend: %s", config.airplay_backend)
    if config.mdns_interface:
        LOGGER.info(
            "Configured mDNS interface hint: %s (handled by Music Assistant if supported)",
            config.mdns_interface,
        )
    LOGGER.info("Configured advertised targets: %s", len(config.advertised_targets))

    bridge = SendSpinAirPlayBridge(config)
    retry_delay = 5

    async def sync_loop() -> None:
        nonlocal retry_delay
        while True:
            try:
                latest = load_config()
                config.music_assistant_url = latest.music_assistant_url
                config.music_assistant_token = latest.music_assistant_token
                config.advertised_targets = latest.advertised_targets
                config.log_level = latest.log_level
                config.mdns_interface = latest.mdns_interface
                config.airplay_backend = latest.airplay_backend

                summary = await bridge.run_sync()
                LOGGER.info(
                    "Sync complete: configured=%s enabled=%s updated=%s sendspin_candidates=%s groups=%s",
                    summary.configured_targets,
                    summary.enabled_targets,
                    summary.created_or_updated,
                    summary.sendspin_candidates,
                    summary.groups_seen,
                )
                retry_delay = 5
                await asyncio.sleep(config.sync_interval_seconds)
            except Exception as err:
                LOGGER.exception("Bridge sync failed: %s", err)
                LOGGER.info("Retrying in %s seconds", retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 300)

    app = create_app(config, bridge)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()
    LOGGER.info("Management UI listening on port 8099")

    await sync_loop()


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
