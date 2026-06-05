# Changelog

## 0.3.4

- Replaced the placeholder repository branding with cropped project logo assets.
- Updated `icon.png` to a square symbol-only version for better add-on store presentation.
- Updated `logo.png` to a tightly cropped full lockup version.

## 0.3.3

- Added Home Assistant add-on store documentation in `DOCS.md`.
- Added English configuration translations for better field labels and descriptions.
- Normalized repository metadata to match standard Home Assistant add-on repository conventions.
- Removed placeholder example URLs from repository and add-on metadata.

## 0.3.2

- Restyled the ingress UI to follow Home Assistant theme colors and card patterns.
- Improved responsive behavior for the target table on narrower viewports.

## 0.3.1

- Fixed the ingress management UI form actions so save/sync work behind Home Assistant ingress.
- Added an mDNS interface selector to the add-on UI.
- Persisted the selected mDNS interface into the add-on runtime options.

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
