# Music Assistant SendSpin AirPlay Bridge

Manage Music Assistant AirPlay Receiver targets for selected Music Assistant players and groups from a Home Assistant add-on.

## What this add-on does

- Connects to your Music Assistant server.
- Discovers available Music Assistant players and groups.
- Lets you select targets from the add-on UI instead of typing player IDs by hand.
- Creates or updates Music Assistant `airplay_receiver` provider instances for those selected targets.
- Preserves grouped playback by targeting Music Assistant sync groups directly.

## Before you start

1. Music Assistant must already be installed and reachable.
2. The Music Assistant server should have the official AirPlay Receiver plugin available.
3. If your Music Assistant API requires authentication, create a long-lived token in Music Assistant and enter it in this add-on.

## Configuration

Add-on options:

- `music_assistant_url`: Base URL of your Music Assistant server, for example `http://homeassistant.local:8095`
- `music_assistant_token`: Optional long-lived Music Assistant token
- `log_level`: Logging verbosity
- `mdns_interface`: Optional network interface override
- `airplay_backend`: Current backend selection, `shairport-sync`

## Selecting speakers and groups

After starting the add-on:

1. Open the add-on UI.
2. Choose the `mDNS interface` if you need to pin traffic to a specific interface.
3. Enable the players or groups you want to expose.
4. Adjust the AirPlay target names if needed.
5. Save the target selection.
6. Run sync now or wait for the next scheduled reconciliation.

## Notes

- This add-on does not implement a separate AirPlay stack; it manages Music Assistant's own AirPlay Receiver provider instances.
- If Music Assistant shows players as `universal_player`, they can still be selected.
- For grouped playback, select the Music Assistant group entry instead of the individual child speakers.

## Troubleshooting

### Save or sync returns an error

- Update to the latest version of this add-on.
- Check the add-on logs.
- Confirm the Music Assistant server URL and token are correct.

### AirPlay target does not appear

- Verify Music Assistant can advertise AirPlay receivers on your LAN.
- Check the chosen `mdns_interface`.
- Confirm the AirPlay Receiver plugin is available in Music Assistant.

### Music Assistant authentication fails

- Create a long-lived token in Music Assistant under `Settings -> Profile`.
- Paste that token into `music_assistant_token`.

## Source and repo

This add-on lives in a custom Home Assistant add-on repository. The repository root contains `repository.yaml`, and this add-on is stored in the `music-assistant-sendspin-airplay-bridge` folder.
