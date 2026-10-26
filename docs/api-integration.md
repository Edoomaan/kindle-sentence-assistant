# API configuration

Implementation and provider research: 2026-10-23. Device status consolidated: 2026-10-25.

## Providers and credentials

| Provider ID | Chat endpoint | Authentication | Private key file |
| --- | --- | --- | --- |
| `evren` | `https://evren-llmapi.ssyz.org.tr/v1/chat/completions` | `X-API-Key` | `evren-header` |
| `openai` | `https://api.openai.com/v1/chat/completions` | `Authorization: Bearer` | `openai-header` |
| `deepseek` | `https://api.deepseek.com/chat/completions` | `Authorization: Bearer` | `deepseek-header` |

All files live under `/var/local/sentence-assistant`, owned by `framework` with directory mode `700` and file mode `600`. The normal setup path uses an offline computer form and a temporary USB transfer file. An optional developer CLI uses a hidden prompt and SSH stdin. Key replacement stages a file with the correct ownership and permissions before renaming it. A failed write leaves the prior key in place. Symlink destinations are rejected. Keys are plaintext, not encrypted against root access.

The endpoint and credential path are fixed for each provider. Unknown providers and invalid model IDs fail rather than falling back to another provider. There is no automatic cross-provider fallback. TLS verification remains enabled and redirects are not followed.

## USB setup (no SSH)

Open the packaged `setup.html` on your computer with its adjacent `setup.js`. Choose a provider, a Chat Completions model ID available to your account, and a key. Review and edit the prefilled explanation instruction (up to 2000 UTF-16 code units). The form makes no network requests and does not use browser storage.

Download `setup.properties`, copy it into `/mnt/us/extensions/sentence-assistant-installer`, safely eject file transfer, then select **Import settings from USB** in KUAL. The key is plaintext in this temporary file: keep it out of Git, cloud-shared folders and `documents`. Import copies it to a private staging directory, removes the Kindle USB copy, validates it, and publishes the selected provider's header and settings with private permissions. On validation failure, existing settings are retained and the transfer file must be recreated. Power loss before cleanup can leave a transfer copy; inspect and remove it manually if import was interrupted. Deletion is not secure erasure on flash storage.

Delete the computer's downloaded copy after import. Leave the key field empty to reuse that provider's saved key. There is no cross-provider key reuse. The exporter/importer escape properties syntax and reject unknown providers, invalid models, header line breaks, extra fields and oversized input; the transfer file is never executed as shell code.

**Test API (uses provider quota)** sends a synthetic sentence over Kindle Wi-Fi and reports success/failure through **Show installer status**. It uses the same request implementation as Explain and does not display or log credentials, selected book text or response reasoning. Check the actual Explain card after installing the new plugin; a bundled-payload API test alone cannot establish that the reader loaded it.

The preferences are the entire system message, with no hidden prefix or English-only rule. The default appears only in the editable `setup.html` textarea. Users can request another response language or translation. Blank or missing instructions are rejected rather than replaced with a compiled default. Settings are reloaded for the next request; an in-flight request keeps its original configuration.

After upgrading an older plugin, import a complete instruction from the new form. Existing short style-only preferences no longer receive additional explanation rules. Leave the key blank to reuse the selected provider's saved key. The fully editable instruction revision is host-tested; device validation remains pending.


## Optional developer SSH commands


The commands below run on the computer, not in a Kindle shell. Set `--host` before the subcommand if the USB SSH address differs from `192.168.15.244`.

```bash
python3 tools/setup-api.py key --provider evren
python3 tools/setup-api.py key --provider openai
python3 tools/setup-api.py key --provider deepseek
```

Each command asks for that provider's key privately. To rotate a key without affecting other providers:

```bash
python3 tools/setup-api.py key --provider openai --replace
```

Test a provider independently of the active card configuration:

```bash
python3 tools/setup-api.py test --provider evren --model qwen3.8-flash-next
python3 tools/setup-api.py test --provider deepseek --model deepseek-flash
python3 tools/setup-api.py test --provider openai --model YOUR_CHAT_MODEL
```

Replace `YOUR_CHAT_MODEL` with an available Chat Completions model in your OpenAI account. A synthetic English sentence is sent by the Kindle. The script prints timing and the final explanation, not the key or reasoning content. Tests may incur provider charges; no free tier is assumed.

After testing, choose the active provider/model:

```bash
python3 tools/setup-api.py use --provider evren --model qwen3.8-flash-next
```

This writes a key-free `api.properties` file (CLI selection reads its default instruction from the local setup.html form):

```properties
provider=evren
model=qwen3.8-flash-next
instruction=Explain the selected text in Turkish.
```

The new plugin reads it when starting a request, so no framework restart is needed for subsequent provider changes. In-flight requests keep their original configuration. Setting a provider requires its own saved key. A test does not change this file.

Existing installations with only `evren-header` must import settings including an instruction. The old Evren-only plugin must be upgraded before `use` affects the card. `setup-api.py` replaces the old `setup-evren.py` commands.

## Request behavior

Every request sends exactly two messages: the saved instruction in the system message, and the selected passage in the user message. No surrounding paragraphs, book identity or history are added. The UI displays only `choices[0].message.content` from completed responses. Refusals, malformed responses, token-limited responses and transport errors produce a short error state.

Provider-specific settings:

- Evren: `max_tokens=1024`, `reasoning_effort=low` (tested with Qwen).
- OpenAI: `max_completion_tokens=1024`, `store=false`; no reasoning setting is forced on arbitrary models.
- DeepSeek: `max_tokens=1024`, `thinking.type=disabled`.

Limits: 8000 UTF-16 code units of selected text, 64 KiB response body, 10-second connection timeout and 45-second total curl timeout. Streaming and automatic retries are disabled. Each new request has its own curl process. Closing or changing the selection cancels it; generation IDs prevent stale results from replacing a newer selection. Cancellation cannot guarantee that server-side processing or charges stop.

## Validation status

The preceding Evren-only revision was tested end to end on the target Kindle, including USB-disconnected Wi-Fi use. Single-sentence observations were GLM 5.3: 15.83 s, DeepSeek through Evren: 7.13 s, Qwen through Evren: 2.82 s. These are individual observations, not latency guarantees or direct-provider benchmarks.

The USB import and configurable-preferences revision passes host tests. The user confirmed successful device import after the staging-ownership fix; a separate API-test confirmation remains pending. The preceding multi-provider revision was compiled against the Kindle runtime and deployed through KUAL; the user confirmed Evren explanations work. Direct OpenAI/DeepSeek credentials, model access and Kindle TLS compatibility have not been tested. Their pricing and retention policies are separate from Evren's. Evren's previously observed zero pricing is not a guarantee of future free service.

## Sources

Checked 2026-10-23:

- [OpenAI authentication](https://developers.openai.com/api/reference/overview): Bearer authentication.
- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create): endpoint, messages, `max_completion_tokens` and `store`.
- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/): endpoint and request schema.
- [DeepSeek thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/): explicit non-thinking mode.
- Evren's key page, model metadata and successful synthetic responses were supplied or verified during device testing. Historical scope and limitations are summarized in [technical findings](feasibility.md).


A `.env` file is not used by the Kindle runtime. Its filename would not encrypt the key or restrict access. The app uses provider-specific header files in the private directory instead; `.env`, `setup.properties` and header files are excluded from Git. Do not add real keys to an example configuration.
