# Changelog

## [0.1.2-beta] — 2026-06-02

### Added
- Resource table below each per-proxy chart showing name, state (color-coded badge), and creator for every monitored resource
- Clickable deep links from resource names and chart legends directly to the Databricks workspace UI (clusters, pipelines, warehouses, apps)
- Animated pulse marker on the latest data point in every chart
- Interactive chart legend: hovering a legend item highlights the corresponding line and dims the rest
- `service_id` and `creator` fields added to the TruProxy schema; graceful fallback for older binary builds that don't emit them yet
- Loading spinner shown while fetching cost data

### Changed
- App pink color palette replaced with a higher-contrast set (dark rose, bright pink, orange, purple, indigo, teal)
- Chart legends hidden when clickable link-legends are rendered (avoids duplication)
- Stale resource metadata is pruned when entries leave the rolling history window

### Fixed
- NaN values in chart data filled to zero to prevent rendering gaps

## [0.1.1-beta] — 2026-06-02

### Added
- Databricks Apps monitoring — new Apps page with cost tracking and pink color theme
- `apps` API scope added to PAT configuration (required for `/api/2.0/apps` access)

### Changed
- Settings page now shows interactive API scope selector (pill buttons) instead of a static permission list
- PAT scopes are persisted in session state and passed to TruProxy on save
- Updated streamlit to 1.40

## [0.1.0-beta] — 2026-05-29

### Initial beta release
- Real-time cost monitoring for clusters, pipelines, and SQL warehouses
- 5-second refresh interval with 10-minute rolling history
- PAT token configuration via Settings page
- TRUPROXY_REGION and TRUPROXY_TIER configurable via app.yaml environment variables
