# Native reader plugin

See the root [README](../README.md) for usage, build commands and validation status, [API configuration](../docs/api-integration.md) for provider setup, and [installation](../docs/installation.md) for recovery requirements.

The native entry point is `org.kindlesentence.nativeui.ExplainPlugin`. The registered device path remains `/mnt/us/extensions/sentence-assistant/explain-preview.jar` to preserve existing installations.

The build requires the tested device's SDK and Java runtime copies. Host tests exercise rendering and request lifecycle behavior; they cannot establish touch interaction, E Ink refresh or native loader compatibility by themselves.

Previous experimental artifacts and obsolete fixed-hash installers are not part of the source tree. Historical findings, including the unsupported `HierarchyEvent` failure, are summarized in [technical findings](../docs/feasibility.md).
