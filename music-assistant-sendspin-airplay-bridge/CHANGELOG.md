# Changelog

## 0.3.14

- Added per-instance cleanup logging so failed AirPlay receiver removals include the exact provider instance ID.
- Bulk cleanup now continues past broken entries instead of aborting on the first `500` response from Music Assistant.

## 0.3.13

- Fixed AirPlay receiver inventory to fetch actual configured provider values instead of config-entry definitions.
- Fixed receiver rows to show real AirPlay names and Music Assistant player IDs.
- Updated cleanup matching to use hydrated provider values from Music Assistant's config value API.

## 0.3.12

- Fixed Music Assistant provider inventory fetching to request provider config values.
- Fixed AirPlay receiver detection to match Music Assistant provider configs using both `domain` and `provider_domain`.
- This allows stale and broken AirPlay Receiver entries to appear in the receiver inventory and cleanup flow.

## 0.3.11

- Disabling a target now removes its managed AirPlay receiver instead of leaving a stale receiver behind.
- Wired disabled-target cleanup into the save flow with status feedback in the UI.

## 0.3.10

- Fixed same-name speaker handling so distinct speakers are no longer collapsed just because they share a display name.
- Added disambiguated target labels and default AirPlay names when multiple distinct players share the same name.
- Kept wrapper deduplication only for the specific universal-player-to-real-target case.

## 0.3.9

- Clarified in repository and add-on documentation that this project intentionally supports AirPlay receiver management only.
- Added explicit explanation for why Chromecast / Google Cast receiver support is out of scope.

## 0.3.8

- Added detailed sync diagnostics around AirPlay receiver provider creation and post-save lookup.
- Improved logging to distinguish provider-save success from receiver lookup/matching failures.

## 0.3.7

- Added safe cleanup actions for AirPlay receiver instances classified as cleanup candidates.
- Verified and used Music Assistant's `config/providers/remove` API for receiver removal.
- Added per-row and bulk cleanup actions in the receiver inventory UI.

## 0.3.6

- Added selected target health status to the add-on UI.
- Added AirPlay receiver inventory with managed/unmanaged and cleanup-candidate visibility.
- Added client-side search, filtering, and advanced duplicate inspection controls.
- Added dashboard counts for visible targets, selected targets, receivers, and cleanup candidates.

## 0.3.5

- Deduplicated duplicate-looking Music Assistant players in the add-on UI using logical speaker/group targets.
- Persisted target selections by logical key so mappings survive wrapper player ID changes after reconnects.
- Preferred stable group and native targets over wrapper players when duplicate display names exist.

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
