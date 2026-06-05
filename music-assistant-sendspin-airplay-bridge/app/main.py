from __future__ import annotations

import asyncio
import logging

from .bridge import SendSpinAirPlayBridge
from .config import load_config
from .logging_setup import configure_logging


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

    while True:
        try:
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


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
