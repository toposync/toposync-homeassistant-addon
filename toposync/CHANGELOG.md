# Changelog

## 0.11.0 - 2026-10-24

- Install toposync-streaming 0.11.0 with passive pipeline inspection, visual sensors, automatic activity history and image sequence playback.
- Include updated camera tracking, streaming fallback and privacy controls.
- Align the application and both add-ons at 0.11.0. Back up application data before upgrading; separately installed processing servers must be updated separately.

## 0.10.1 - 2026-10-18

- Correct the Toposync brand spelling in the store, sidebar, documentation and translations.
- Keep the installed application pinned to `toposync-streaming==0.10.0`; this patch only updates add-on metadata and documentation.

## 0.10.0 - 2026-10-17

- Rename the store and sidebar entry to Toposync Full Application to distinguish it from Toposync Remote Instance.
- Add English and Brazilian Portuguese network descriptions and installation guidance.
- Install `toposync-streaming==0.10.0`, including authenticated remote ingress support and HLS preference for remote connections. Existing full add-on authentication remains unchanged.

## 0.9.0 - 2026-10-16

- Install `toposync-streaming==0.9.0`, keeping the add-on and application versions aligned.
- Include the new PTZ Attention extension in the application bundle.
- Include panoramic region filters, geographic maps, Vision improvements, and updated pipeline and notification interfaces.
- Physical PTZ attention requires explicit configuration and qualification; updating the add-on does not authorize camera movement.
- Back up the data directory before upgrading. Previous attention profiles require explicit review before migration to panoramic profiles.
- Pipeline graphs require schema version 2; export and migrate version 1 graphs before upgrading.
