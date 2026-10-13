# Plan — Local Testcase Generator (Chapter 3)

## Goal
Build the 2-screen Streamlit app specified in `src/prompt.md`: a chat screen that turns a Jira issue key into a test-case draft, and a settings screen that persists Jira + LLM credentials locally. Default LLM is local Ollama (`gemma3:1b`), with Groq as fallback / explicit option.

## Confirmed decisions
| Decision | Choice |
|---|---|
| Credentials | `.env` seeds `config.json` on first run; Settings screen reads/writes `config.json`; `config.json` wins over `.env` |
| Layout | Streamlit **multipage**: `app.py` = Chat, `pages/settings.py` = Settings, sidebar navigation |
| Groq model | `llama-3.3-70b-versatile` default, editable in Settings |
| Scope | Exactly the 6 mandated deliverables + "Test Ollama" / "Test Groq" buttons |
| HTTP | Plain `requests` (no `ollama`/`groq` SDKs) — uniform fallback handling, minimal deps |

Credentials come from the `.env` file supplied separately. Nothing is hardcoded, nothing credential-bearing is committed.

## Target file structure
```
Chapter_3_Local_Testcase_Generator/
├── app.py                                  # Screen 1 — Chat            (new)
├── pages/
│   └── settings.py                         # Screen 2 — Settings        (new)
├── config_store.py                         # persisted settings layer   (new)
├── jira_client.py                          # Jira REST access           (new)
├── llm_client.py                           # Ollama + Groq + fallback   (new)
├── templates/
│   ├── 01_Testcase_Generator_Template.md   # exists (RTCFR)
│   └── 04_Negative_Testcases_Template.md   # new 2nd template for picker
├── requirements.txt                        # new
├── .gitignore                              # new
├── .env.example                            # new — key names only, no values
├── .env                                    # provided separately, gitignored
├── config.json                             # runtime-generated, gitignored
└── plan.md                                 # this plan (committed)
```

## Module contracts

### `config_store.py`
Single source of truth for persisted settings.

- `DEFAULTS` — `{jira_url: "", jira_email: "", jira_token: "", provider: "Ollama", ollama_url: "http://localhost:11434", ollama_model: "gemma3:1b", groq_api_key: "", groq_model: "llama-3.3-70b-versatile"}`
- `ENV_MAP` — maps env var → setting key: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `LLM_PROVIDER`, `OLLAMA_URL`, `OLLAMA_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`
- `load_settings() -> dict` — merge order `DEFAULTS` → `.env` (via `dotenv.load_dotenv()`) → `config.json`
- `save_settings(values: dict) -> None` — atomic write of `config.json` (write temp + `os.replace`)
- `env_keys_present() -> list[str]` — names of `.env` keys detected (never values), for display on Settings
- `config_path() -> str` — absolute path of `config.json`, for display on Settings
- `is_configured(settings) -> bool` — Jira URL + email + token all non-empty

`config.json` sits next to the app source, resolved from `Path(__file__).parent` so CWD does not matter.

### `jira_client.py`
- `class JiraError(Exception)` — carried into `st.error` with a human message.
- `parse_issue_key(text) -> str | None` — regex `\b[A-Z][A-Z0-9]{1,9}-\d+\b`, first match, uppercased. Returns `None` when the chat message has no key.
- `fetch_issue(key, settings) -> dict` — `GET {jira_url}/rest/api/2/issue/{key}` with `fields=summary,description,issuetype,priority,status,labels` and `auth=HTTPBasicAuth(email, token)`, `timeout=15`. API **v2** is used deliberately: Cloud and Server both serve it and it returns `description` as plain text. If `description` arrives as a dict (ADF), `_adf_to_text()` walks `content`/`text` nodes to flatten it.
- Returns `{key, summary, description, acceptance_criteria, issue_type, priority, status, labels, url}` where `url = f"{jira_url}/browse/{key}"`.
- `_extract_acceptance_criteria(description) -> str` — regex slice from an `Acceptance Criteria` / `AC:` heading to end of description; returns `""` when absent so the template's `"Not specified"` constraint governs.
- Error mapping: 401/403 → "Jira rejected the credentials", 404 → "Issue KEY not found", `ConnectionError`/`Timeout` → "Cannot reach Jira at URL".

### `llm_client.py`
Template loading, prompt assembly, both providers, fallback.

- Constants: `OLLAMA_DEFAULT_URL`, `OLLAMA_DEFAULT_MODEL = "gemma3:1b"`, `GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"`, `GROQ_DEFAULT_MODEL`, `class LLMUnavailable(Exception)`.
- `list_templates() -> list[str]` / `load_template(name) -> str` — reads `templates/*.md`. No `templates/` writes; no model pulling.
- `build_prompt(issue, template_text) -> str`
  - Replace placeholders in place: `[PASTE REQUIREMENTS HERE]`, `[PASTE PRD HERE]`, `[PASTE REQUIREMENTS]` → fenced Jira block; `[FEATURE]` → `issue["summary"]`; `[NUMBER]` → "an appropriate number of".
  - If no placeholder matched, append the Jira block under a `REQUIREMENTS:` heading.
  - Jira block format:
    ```
    === JIRA ISSUE <KEY> ===
    Summary: ...
    Type / Priority / Status: ...
    Description:
    ...
    Acceptance Criteria:
    ...
    === END JIRA ISSUE ===
    ```
    followed by one line: use ONLY the content between the markers; where information is missing, write "Not specified".
- `_call_ollama(prompt, settings) -> str` — `POST {ollama_url}/api/chat` body `{"model": ollama_model, "messages": [{"role": "user", "content": prompt}], "stream": false}`, read `["message"]["content"]`, `timeout=(5, 180)`.
- `_call_groq(prompt, settings) -> str` — `POST GROQ_ENDPOINT` with `Authorization: Bearer <groq_api_key>`, body `{"model": groq_model, "messages": [...], "temperature": 0.2}`, read `["choices"][0]["message"]["content"]`.
- `_ollama_reachable(settings) -> tuple[bool, str]` — `GET {ollama_url}/api/tags` (timeout 5) and confirm `ollama_model` is in the returned model names. This is the fast pre-flight that keeps fallback snappy on a cold/missing Ollama instead of waiting on a generation timeout.
- `generate(prompt, settings) -> dict` returning `{text, provider, model, fallback_reason}`
  - `provider == "Groq"` → Groq only. Ollama is never called (satisfies `[Don't]`).
  - `provider == "Ollama"` (default) → pre-flight `_ollama_reachable`; if not reachable, or `_call_ollama` raises/times out, fall back to Groq when `groq_api_key` is set, setting `fallback_reason`. If no Groq key, raise `LLMUnavailable` with "Ollama is unavailable at <url> — start it, or add a Groq API key in Settings".
- `check_ollama(settings) -> tuple[bool, str]` / `check_groq(settings) -> tuple[bool, str]` — back the Settings test buttons; return a status string naming the model.

### `app.py` — Screen 1, Chat
- `st.set_page_config(page_title="Local Testcase Generator", page_icon="🧪", layout="wide")`, then `st.title("Local Testcase Generator")`.
- `st.session_state.history: list[dict]` of `{role, content, meta}`; initialised once on first run.
- Sidebar status block: active provider + model, Jira URL, Ollama URL, and either a green "Ready" or an amber "Not configured" with `st.page_link("pages/settings.py", label="Open Settings →")`.
- Unconfigured guard: warning banner + link, input disabled.
- Input row, per `[Mandatory]` "a text input box and a Send button":
  ```python
  with st.form("chat_form", clear_on_submit=True):
      text = st.text_input("Ask for test cases", placeholder="create test cases for QA-102")
      template_name = st.selectbox("Template", list_templates())
      submitted = st.form_submit_button("Send")
  ```
  A form keeps Enter-to-send and a real Send button in one control. Example-prompt buttons above the form (the wireframe's `Create tc for ...` row) write a canned string into `st.session_state.draft` and rerun.
- On submit (only path that triggers work, so Streamlit reruns never re-generate): append the user message, then
  `parse_issue_key` → `fetch_issue` → `load_template` → `build_prompt` → `generate` → append assistant message and `st.rerun()`.
- History renders as `st.chat_message("user"|"assistant")` + `st.markdown(content)`; assistant messages get a `st.caption` with `provider · model` and why the fallback fired. Every failed step is caught and rendered via `st.error` with the message appended to history so the conversation stays a truthful transcript.
- `st.spinner("Fetching ticket and generating test cases…")` around the pipeline.
- `st.download_button` under the newest assistant message to save the generated suite as `.md`.

### `pages/settings.py` — Screen 2, Settings
- `st.set_page_config(page_title="Settings", page_icon="⚙️")`, heading, prefill every field from `load_settings()`.
- `st.form("settings_form")` fields: Jira URL, Jira Email, Jira API Token (`type="password"`), Ollama URL, Ollama model, Provider radio (`Ollama` first/default, `Groq`), Groq API Key (`type="password"`), Groq model.
- `st.form_submit_button("Save Settings")` → `save_settings({...})` → `st.success("Saved to <config_path>")` → `st.rerun()`. Token fields are prefilled so an untouched Save preserves them; caption states "leave as-is to keep the stored token".
- Below the form, a divider and two independent plain buttons (`Test Ollama`, `Test Groq`) calling `check_ollama` / `check_groq`, showing `st.success`/`st.error` with the returned detail. Kept out of the save form so testing never overwrites settings.
- Storage note panel: `config.json` path, whether `.env` values were picked up (key names only, never values), and a reminder that both files are gitignored.

### `templates/`
`01_Testcase_Generator_Template.md` stays as-is (RTCFR, `[PASTE REQUIREMENTS HERE]`). Add `04_Negative_Testcases_Template.md` (negative-only, `| Test ID | Invalid Scenario | Input | Expected Error |`) adapted from `Chapter_2_Prompt_Engineering/Testcase Templates/04_Negative_Test_Cases_Only_Template.md` so the template picker is meaningful.

### Support files
- `requirements.txt` — `streamlit>=1.40`, `requests>=2.31`, `python-dotenv>=1.0`.
- `.gitignore` — `.env`, `config.json`, `.streamlit/secrets.toml`, `.venv/`, `__pycache__/`, `*.pyc`.
- `.env.example` — the eight key names with empty values and a one-line comment each.

## Data flow
```
[Screen 1 chat] text_input + Send
      │  message text
      ▼
jira_client.parse_issue_key ──► no key? → inline error, stop
      │  "QA-102"
      ▼
config_store.load_settings ──► jira_url + email + token
      │
      ▼
jira_client.fetch_issue ──► {summary, description, acceptance_criteria, ...}
      │
      ▼
llm_client.load_template(templates/<picked>.md)
      │
      ▼
llm_client.build_prompt(issue, template) ──► single merged prompt
      │
      ▼
llm_client.generate(prompt, settings)
      ├── provider == Groq  → Groq only
      └── provider == Ollama → preflight /api/tags
                               ├── ok      → Ollama /api/chat
                               └── down    → Groq, fallback_reason recorded
      │  {text, provider, model, fallback_reason}
      ▼
[Screen 1 chat] assistant message + provider caption + download button

[Screen 2 settings] save ──► config.json ──► read by every load_settings() call above
[.env] ──(first run seed, config.json absent)──► load_settings()
```

## Build order (one module at a time, per prompt.md)
1. **Scaffold** — `.gitignore`, `requirements.txt`, `.env.example`, second template; `pip install -r requirements.txt`.
2. **`config_store.py`** — verify merge order with a throwaway script in the scratchpad: no `config.json` → `.env` values visible; after a `save_settings`, `config.json` wins.
3. **`jira_client.py`** — run a scratchpad script against the real credentials from `.env` for the target ticket key; print summary, description length, and extracted acceptance criteria.
4. **`llm_client.py`** — confirm `_ollama_reachable` against the live server and `generate()` on a canned prompt; then point `ollama_url` at a dead port to prove the Groq fallback fires and records `fallback_reason`.
5. **`pages/settings.py`** — save/load round-trip in the browser, and both test buttons.
6. **`app.py`** — full end-to-end in the browser.
7. **Review** — stop for sign-off before any further polish.

## Verification
Run from `Chapter_3_Local_Testcase_Generator/`:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py
```
- **Chat happy path** — Send `create test cases for <key>` → markdown table matching the chosen template's format, caption showing `Ollama · gemma3:1b`.
- **Real-target check** — assert the table's content actually reflects the fetched ticket (summary/AC appear as requirements), not a generic guess; and that no `[PASTE ...]` placeholder survived into the rendered output.
- **Fallback** — stop Ollama (`Stop-Process -Name ollama`), resend → response arrives from Groq with `fallback_reason` in the caption.
- **No unintended Groq call** — provider `Ollama` with Ollama running keeps the caption Ollama-only; provider `Groq` produces no `/api/chat` hit in the Ollama server log.
- **Not-configured state** — temporarily rename `config.json`, confirm the `[Don't]` holds: the app warns and asks for Settings instead of hitting Groq. Restore.
- **Settings persistence** — change Jira URL, Save, restart Streamlit, confirm the value survives; confirm `config.json` and `.env` are untracked by `git status`.
- **Bad input** — a message with no key, a nonexistent key, and a deliberately wrong token each produce a specific `st.error`, and the app never crashes.

## Constraints honoured
- No credentials in source; all of them live in `.env` / `config.json`, both gitignored.
- Groq is only called when Ollama is unreachable or the provider is explicitly `Groq`.
- Nothing re-pulls or re-downloads `gemma3:1b`; the app only reads `/api/tags` and calls `/api/chat`.
- Python code is comment-free with no docstring prose — documentation lives in this plan, per project taste.
- Six mandated deliverables, three dependencies, no extra abstraction layer.

# https://neethusingh.atlassian.net/browse/SAM1-1  -> testcase generated for this