# Changelog

## 0.3.0

- Bumped the add-on version so Home Assistant can install the new release.
- Added clearer repository and add-on documentation.
- Documented the ingress-based speaker management flow and update process.

## 0.2.0

- Added an add-on management UI for selecting Music Assistant players and groups.
- Removed manual `advertised_targets` editing from the add-on options form.
- Added managed target persistence in `/data/managed_targets.json`.
- Added manual sync action from the add-on UI.

## 0.1.0

- Initial Home Assistant add-on scaffold.
- Added Music Assistant websocket/API client.
- Added target reconciliation for Music Assistant AirPlay Receiver instances.
- Added startup logging, retry/backoff behavior, and README documentation.
