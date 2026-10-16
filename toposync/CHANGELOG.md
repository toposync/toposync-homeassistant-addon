# Changelog

## 0.9.0 - 2026-10-16

- Install `toposync-streaming==0.9.0`, keeping the add-on and application versions aligned.
- Include the new PTZ Attention extension in the application bundle.
- Include panoramic region filters, geographic maps, Vision improvements, and updated pipeline and notification interfaces.
- Physical PTZ attention requires explicit configuration and qualification; updating the add-on does not authorize camera movement.
- Back up the data directory before upgrading. Previous attention profiles require explicit review before migration to panoramic profiles.
- Pipeline graphs require schema version 2; export and migrate version 1 graphs before upgrading.
