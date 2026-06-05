# Music Assistant SendSpin AirPlay Bridge Repository

This repository is a custom Home Assistant add-on repository containing one add-on:

- `music-assistant-sendspin-airplay-bridge`

The add-on manages Music Assistant AirPlay Receiver targets for selected SendSpin players and SendSpin-backed groups.

It is intentionally an AirPlay-focused repository. It does not provide Chromecast / Google Cast receiver emulation.

## Repository Structure

- `repository.yaml`: repository metadata for Home Assistant.
- `README.md`: repo-level install and update notes.
- `music-assistant-sendspin-airplay-bridge/`: the actual add-on.

## What This Repository Is

This is:

- a Home Assistant add-on repository.

This is not:

- a HACS repository;
- a Home Assistant integration;
- a Codex plugin.

## Installation

1. In Home Assistant, open `Settings -> Add-ons -> Add-on Store`.
2. Open the overflow menu and choose `Repositories`.
3. Add the URL of this repository.
4. Refresh the add-on store if needed.
5. Open `Music Assistant SendSpin AirPlay Bridge`.
6. Install the add-on.
7. Set `music_assistant_url` and, if your MA server requires auth, `music_assistant_token`.
8. Start the add-on.
9. Open the add-on UI and select the speakers/groups you want exposed.

## Updating

Home Assistant add-ons update by version number, not by file timestamp.

That means every release must increase:

- `music-assistant-sendspin-airplay-bridge/config.yaml -> version`

Example:

- installed: `0.2.0`
- new release: `0.3.0`

If Home Assistant shows an available update but the installed and latest versions are identical, it will not let you install anything. In that case:

1. confirm the add-on `version` actually increased;
2. refresh the custom repository;
3. if Home Assistant still shows stale metadata, remove and re-add the repository.

## Documentation

The add-on-specific documentation lives in:

- `music-assistant-sendspin-airplay-bridge/README.md`
