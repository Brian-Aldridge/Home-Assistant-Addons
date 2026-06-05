# Music Assistant SendSpin AirPlay Bridge

This Home Assistant add-on manages Music Assistant AirPlay Receiver targets for selected Music Assistant players or groups, with a focus on SendSpin-backed targets.

The runtime design is deliberate: current Music Assistant already includes an official `airplay_receiver` plugin backed by `shairport-sync`, and that plugin can expose any MA player, including groups, as an AirPlay target. This add-on uses the Music Assistant API to inspect players, validate configured targets, and create or update the corresponding AirPlay Receiver provider instances.

## What It Does

- Connects to a Music Assistant server.
- Reads available Music Assistant players and groups.
- Logs the discovered player inventory for diagnostics.
- Validates configured target mappings.
- Creates or updates one Music Assistant AirPlay Receiver instance per configured target.
- Preserves sync by targeting a Music Assistant group as a single MA player/group id.
- Retries with backoff when Music Assistant is unavailable.

## Why This Approach

The cleanest current integration point is Music Assistant's official AirPlay Receiver plugin, not a parallel custom receiver stack. Music Assistant's documentation states that:

- the AirPlay Receiver plugin "allows any MA player to appear as an AirPlay device";
- "Any MA player can be exposed including groups";
- the plugin is configured per target player.

That makes a controller add-on more defensible than reimplementing RAOP routing beside MA.

## Current Limitations

- This add-on does not implement its own AirPlay receiver pipeline.
- AirPlay advertisement and audio ingestion are performed by Music Assistant's official AirPlay Receiver plugin.
- Automatic SendSpin detection is heuristic. The add-on logs likely SendSpin targets, but final validation is still based on your configured MA player ids.
- Unmanaged pre-existing `airplay_receiver` instances are left in place.
- The add-on expects a reachable Music Assistant API at the configured URL.

## Why Chromecast Is Out Of Scope

Google Cast receiver emulation is legally and technically different from AirPlay. Receiver behavior is not fully open in the same way, and there is no equivalent clean, redistributable, open-source path comparable to `shairport-sync` plus Music Assistant's existing AirPlay Receiver provider. This v1 stays on the open path.

## Configuration

The add-on options now only handle connection settings. Speaker and group selection is managed from the add-on UI after startup.

Example:

```yaml
music_assistant_url: "http://homeassistant.local:8095"
music_assistant_token: ""
log_level: "info"
mdns_interface: ""
airplay_backend: "shairport-sync"
```

## Music Assistant URL

Set `music_assistant_url` to the base HTTP URL of your Music Assistant server, for example:

- `http://homeassistant.local:8095`
- `http://192.168.1.50:8095`
- `https://music.example.internal`

If your Music Assistant server requires authentication for API access, set `music_assistant_token`.

## Managing Speakers And Groups

After the add-on starts, open its built-in UI from Home Assistant. The page queries Music Assistant and shows:

- all discovered players and groups;
- whether each target looks like SendSpin;
- a checkbox to enable it;
- an editable AirPlay target name field.

That avoids manual `player_id` entry. For grouped playback, select the Music Assistant group row directly so playback stays grouped at the MA layer.

## Installation

1. Put this add-on folder inside a Home Assistant add-on repository.
2. Ensure the Music Assistant server is already running and reachable.
3. In Music Assistant, install or enable the official AirPlay Receiver plugin.
4. Add this repository to Home Assistant add-ons if needed.
5. Install the add-on.
6. Configure `music_assistant_url` and optional `music_assistant_token`.
7. Start the add-on.
8. Open the add-on UI.
9. Select speakers/groups from the list, set names, and save.
10. Run sync and inspect logs if needed.

## Troubleshooting

### mDNS / AirPlay target not visible

- Confirm the Music Assistant server host can advertise mDNS on the target LAN.
- Confirm the official Music Assistant AirPlay Receiver plugin is installed.
- Confirm the target provider instances were created successfully in Music Assistant.
- Verify client devices and the Music Assistant host are on the same broadcast domain or that mDNS reflection is configured.

### Firewall / networking

- Ensure the add-on can reach the configured Music Assistant URL.
- Ensure the Music Assistant host is permitted to advertise and receive AirPlay traffic on the LAN.
- If you use reverse proxies or TLS termination, verify both `/api` and `/ws` access paths.

### Music Assistant connection failures

- Check the add-on logs for retry messages and HTTP/websocket errors.
- Verify the API token if one is required.
- Confirm the Music Assistant server version is current enough to expose the `airplay_receiver` provider.

### Configured target fails validation

- Verify the `ma_player_id` exists in Music Assistant.
- Review the startup logs; the add-on logs all discovered players and groups.
- For grouped playback, use the MA group id rather than a member speaker id.

## Development Notes

- The add-on uses Music Assistant's websocket endpoint for connection validation and the JSON API for provider reconciliation.
- A future revision could add a richer UI or surface provider-instance cleanup.
- A future Android-audio or Chromecast-like bridge would need a separate legal and technical design track.
