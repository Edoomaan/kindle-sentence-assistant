# Technical findings and validation

Research performed 2026-10-21–23; consolidated 2026-10-25. This summary replaces the chronological development logs. Device observations apply only to Kindle Basic 11th generation (2024), firmware `5.17.1.0.4`, build `4351960007`.

## Native integration

Private device JAR copies were checked with SHA-256 and ZIP integrity tests, then inspected with `javap`. The stock reader exposes selection text through:

```text
ReaderSDK.mH() → BookNavigator
BookNavigator.azE().mt(), BookNavigator.azF().mq() → selection bounds
ReaderSDK.mJ() → Book
Book.q(start, end) → selected text
```

Translator/Wikipedia integrations register selection-card providers through `ReaderSDK.Jc().a(provider)` and remove them with `b(provider)`. The project uses a separate `SelectionDialogCard` and provider; it does not replace Wikipedia or modify annotation actions. Close uses the reader's dialog API through `ReaderSDK.Jd().Hz().Vo()`.

`ReaderSDK-impl.jar` loads `reader_plugins.xml` through its classloader. Entries can name a separate JAR, loaded through `URLClassLoader`, and implement `ReaderPlugin`. Our registration points to `/mnt/us/extensions/sentence-assistant/explain-preview.jar`. Initial registration changes only the XML entry's uncompressed contents; archive compression/metadata can differ. Updates replace only our plugin when registration already matches. KUAL hosts the installer menu; copying a plugin JAR into `extensions` alone does not register it with the reader.

The first API build failed on Kindle because `java.awt.event.HierarchyEvent` is absent, despite successful desktop Java 8 compilation. Native builds therefore require the device's `rt.jar` and `agui.jar`. Supported lifecycle callbacks replaced that dependency. HTTP requests use a background curl process, avoiding dependence on the old JVM's TLS support; TLS verification stays enabled.

Direct dragging can invoke the reader's QUICK_HIGHLIGHT mode and save an annotation. The user verified that holding one word, lifting the finger, and extending selection handles avoids this behavior. The plugin does not delete annotations automatically.

## Validation and recovery evidence

| Check | Evidence and limits |
| --- | --- |
| Selection and explanation | User confirmed working cards and Evren/Qwen responses, including Wi-Fi with USB disconnected. |
| Multiple providers | New plugin deployed; Evren works. Direct OpenAI/DeepSeek access remains untested. |
| KUAL update | Compatibility check and Install/Update succeeded; detached worker survived framework shutdown and the user confirmed Explain still worked. |
| Clean first installation | User confirmed Explain was absent after removal. KUAL installation then succeeded; SSH verified running reader, correct permissions, read-only root, and exactly one new XML registration. Detailed post-install card testing was not separately recorded. |
| Manual recovery | Fresh root SSH succeeded with framework stopped. Original system JAR restoration was verified. A prior blank screen persisted until explicit Library activation; the user then confirmed normal reading. The blank-screen root cause was not established. |
| User regression report (2026-10-25) | User reported the proposed offline/error, cancellation, new-selection, special-text and KUAL Restore tests passed. These were not independently instrumented. |
| USB settings import | Host-tested; user confirmed import after the staging-ownership fix. Does not require SSH. |
| Automatic rollback | Mocked command-failure tests pass on the computer. Deliberate failure recovery has not been exercised on Kindle. |
| Reboot recovery | Not tested; no bootloop recovery guarantee. |

System JAR metadata remained `0:0:644`; root returned to `ro`. These hashes identify the tested artifacts, not universal firmware compatibility:

| Artifact | SHA-256 |
| --- | --- |
| Original ReaderSDK-impl.jar | `a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce` |
| Original Reader-plugin.jar | `7045e658c189b525a9dbeac624587e594bc2f2cfe7c449153fbce1355381b9be` |
| Earlier XML registration | `5787dad5a8d18b6ddfd71fb5ec2bddb29c6c411cbb6a7bf88a7db71b6d5459ea` |
| KUAL-generated first-install system JAR | `6e2603b10df8b14fd3c99ce4d0d2559a1e4375aec6d9acc74e399ae3f09f0a20` |
| Working Evren-only plugin | `73928fe8fa1f21a777af5653316c1c7047af90aa9faf492ebe79be371598d272` |
| Deployed multi-provider plugin | `1c97890c8566b94597d30b6773647e990af397599a81fa1a30d9b3a098385440` |

Private backups, including the before-clean-install archive, remain outside Git. See [installation and recovery](installation.md) for current procedures and [API configuration](api-integration.md) for transport limits and provider evidence.

## Reference research

The [Oasis project at commit dc6a0f0](https://github.com/Lemelson/kindle-oasis-native-reader-ai/tree/dc6a0f0a61cb29f15660a591ffc7b96d305a5253) was inspected on 2026-10-21. Its [controller](https://github.com/Lemelson/kindle-oasis-native-reader-ai/blob/dc6a0f0a61cb29f15660a591ffc7b96d305a5253/patch-work/src/com/amazon/ebook/booklet/reader/plugin/notesandmarks/AiAssistantController.java) and [architecture](https://github.com/Lemelson/kindle-oasis-native-reader-ai/blob/dc6a0f0a61cb29f15660a591ffc7b96d305a5253/docs/NATIVE_READER_AI_ARCHITECTURE.md) informed the investigation. Its obfuscated methods differ: `mM/mO`, `aAK/aAL`, `Book.r` and `Jl` correspond to different names on our firmware. Its patch was not assumed compatible or applied.

[KUAL's launcher source](https://github.com/coplate/KUAL_Booklet/blob/master/src/com/mobileread/ixtab/kindlelauncher/KualBooklet.java) and the [USBNetLite extension](https://github.com/notmarek/kindle-usbnetlite/tree/master/extension/extensions/usbnetlite) informed menu and recovery research. These were inspected during 2026-10-21–23; unpinned upstream links can change.

Historical USBNetLite audit (2026-10-23): the [1.0.M release](https://github.com/notmarek/kindle-usbnetlite/releases/tag/1.0.M) contained `Update_usbnetlite_1.0.P_install_khf_11thgenplus.bin`, 242527 bytes, SHA-256 `233f976018c6fbdd4094f43097b1ce013b5d1343c9b3bba858b9da62d8ff52c6`. Its internal label was `1.0.M-r5b188ff`; filenames alone did not identify contents reliably. It was unpacked with [KindleTool](https://github.com/NiLuJe/KindleTool/tree/95291295e039a1a3bc0bc9d6040b07f640dae74a). Static ARM hard-float/loader checks were only preliminary evidence; later actual SSH tests established access on this device. The package modifies system paths and Upstart jobs, so it is not bundled or installed by this project. The checksum identifies the inspected artifact, not an independent publisher signature.

Historical provider exploration: unauthenticated OpenCode free-model inference returned HTTP 403 on Kindle, despite the then-current [API documentation](https://opencode.ai/v2/docs/console/api/inference/). Authenticated access was not tested. Evren was selected after successful authenticated device requests; no client restrictions were bypassed. This is a dated observation, not a claim about current free-tier availability.


## USB settings validation (2026-10-25)

The revised settings flow passes 17 Python tests (including Java registration/import and Node form serialization), core UI/lifecycle checks, and native card/provider checks compiled against verified device runtime/SDK copies. A real headless Chromium test with a dummy key verified offline file download, Unicode escaping and clearing the password field. Credentials were not used in these tests. The final ZIP was checked against its hash manifest and source files and contains project classes only. The 43 Git-visible source/document files were scanned for credential artifacts and high-confidence secret/device-ID patterns; no matches were found. This is not a proof that every possible secret format can be detected.

Device library copies now reside in a permanent private computer directory outside the repository. Temporary library exports and the developer-only KUAL export menu were removed from Kindle after hash/CRC verification. USB settings import, the new KUAL API test action and explanation preferences still require device validation; host success is not reported as a device test.


The earlier two-press installer coupled export and installation. As of 2026-10-26, Install / Update performs installation in one invocation, with a verified on-device transaction backup. A separate Export backup (optional, recommended) action creates a computer-copy export without restarting the reader. Host tests cover installation without an export, stale-export independence, repeated export preservation and rollback. This revised flow has not yet been device-tested. Automatic compatibility checks remain; firmware support is unchanged.


For an independent README onboarding test on 2026-10-25, the user removed both extension directories but Explain remained in the running reader. SSH verified the installed system registration still existed. After saving verified original/current system JARs and metadata on the computer and checking a fresh SSH connection with framework stopped, the original JAR was restored (`a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce`, `0:0:644`). Existing API settings were moved to a root-private inactive backup without reading or printing credentials. Removing extension directories alone is not a complete native-plugin uninstall.
