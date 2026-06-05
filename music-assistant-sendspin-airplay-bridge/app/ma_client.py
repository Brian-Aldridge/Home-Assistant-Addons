from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import aiohttp


LOGGER = logging.getLogger(__name__)


class MusicAssistantClient:
    def __init__(self, base_url: str, token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "MusicAssistantClient":
        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def probe_websocket(self) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("Client session is not initialized")

        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        if not ws_url.endswith("/ws"):
            ws_url = f"{ws_url}/ws"

        async with self._session.ws_connect(ws_url, heartbeat=55, max_msg_size=0) as ws:
            server_info = await ws.receive_json()
            if self.token:
                await ws.send_json(
                    {
                        "message_id": str(uuid.uuid4()),
                        "command": "auth",
                        "args": {"token": self.token, "device_name": "ha-sendspin-bridge"},
                    }
                )
                auth_reply = await ws.receive_json()
                if auth_reply.get("success") is False:
                    raise RuntimeError(
                        auth_reply.get("error") or "Music Assistant websocket auth failed"
                    )
            return server_info

    async def command(self, command: str, args: dict[str, Any] | None = None) -> Any:
        if self._session is None:
            raise RuntimeError("Client session is not initialized")

        payload = {
            "message_id": str(uuid.uuid4()),
            "command": command,
            "args": args or {},
        }
        async with self._session.post(
            f"{self.base_url}/api",
            headers=self.headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            data = await response.json()
            if isinstance(data, dict):
                if data.get("success") is False:
                    raise RuntimeError(
                        data.get("error") or f"Music Assistant command failed: {command}"
                    )
                return data.get("result", data)
            return data

    async def get_players(self) -> list[dict[str, Any]]:
        result = await self.command("players/all")
        if not isinstance(result, list):
            raise RuntimeError("Unexpected players/all response")
        return result

    async def get_provider_configs(self) -> list[dict[str, Any]]:
        for command in ("config/providers", "providers"):
            try:
                result = await self.command(command)
            except Exception as err:
                LOGGER.debug("Provider query %s failed: %s", command, err)
                continue
            if isinstance(result, list):
                return result
        raise RuntimeError("Unable to read provider configuration list from Music Assistant")

    async def save_provider_config(
        self,
        provider_domain: str,
        values: dict[str, Any],
        instance_id: str | None = None,
    ) -> Any:
        args: dict[str, Any] = {
            "provider_domain": provider_domain,
            "values": values,
        }
        if instance_id:
            args["instance_id"] = instance_id
        return await self.command("config/providers/save", args)

    async def remove_provider_config(self, instance_id: str) -> Any:
        return await self.command("config/providers/remove", {"instance_id": instance_id})

    async def get_provider_manifests(self) -> list[dict[str, Any]]:
        for command in ("providers/manifests", "config/providers/manifests"):
            try:
                result = await self.command(command)
            except Exception as err:
                LOGGER.debug("Provider manifest query %s failed: %s", command, err)
                continue
            if isinstance(result, list):
                return result
        return []

    async def ping(self) -> None:
        await self.command("info")

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
