# Local Testcase Generator (Project 2)

A two-screen **Streamlit** app that turns a Jira issue key into a test-case draft. It runs a **local LLM (Ollama)** by default and falls back to **Groq** when Ollama is unavailable or explicitly selected.

![Local Testcase Generator](Local%20Testcase%20generator%20app%20screenshot.jpg)

## What it does

- **Screen 1 — Chat**: type a request like `create test cases for SAM1-1`, pick a template, and press **Send**. The app parses the Jira key, fetches the ticket, merges its content into the template, and renders a markdown test-case table back in the chat with a **Download (.md)** button.
- **Screen 2 — Settings**: persists Jira URL / email / API token, the provider (`Ollama` or `Groq`), the Ollama URL + model, and the Groq API key + model — saved locally to `config.json`.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3 |
| UI | Streamlit (multipage: `app.py` + `pages/`) |
| HTTP | `requests` (no provider SDKs) |
| Config layer | `python-dotenv` + local `config.json` |
| Default LLM | Ollama `gemma3:1b` at `http://localhost:11434` |
| Fallback LLM | Groq `openai/gpt-oss-120b` |

## Layout

```
project_2 Local testcase generator/
├── README.md
├── Local Testcase generator app screenshot.jpg
├── templates/
│   ├── 01_Testcase_Generator_Template.md   # RTCFR test-case generator template
│   └── 04_Negative_Testcases_Template.md   # negative-only template
└── src/
    ├── app.py                              # Screen 1 — Chat
    ├── pages/
    │   └── settings.py                     # Screen 2 — Settings
    ├── config_store.py                     # load/save persisted settings
    ├── jira_client.py                      # Jira REST access
    ├── llm_client.py                       # Ollama + Groq + fallback
    ├── requirements.txt
    ├── run.cmd                             # Windows launcher
    ├── .gitignore
    ├── plan.md                             # build plan
    └── prompt.md                           # original requirements
```

> `llm_client.py` resolves templates from `src/templates/` first, then from the sibling `templates/` folder one level up — which is why `templates/` sits next to `src/` here.

## Setup

```powershell
cd src
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ollama must already be running locally with `gemma3:1b` pulled:

```powershell
ollama serve        # if not already running
ollama pull gemma3:1b
```

## Run

```powershell
python -m streamlit run app.py
```

Or double-click `src\run.cmd` (starts on `http://localhost:8501`).

Then open **Settings** and enter your Jira URL, email, and API token. Optionally add a Groq API key to enable the fallback.

## Configuration and secrets

Values resolve in this order: **`config.json` → `.env` → built-in defaults**.

| Setting | Env var(s) | Default |
|---|---|---|
| Jira URL | `JIRA_URL`, `JIRA_BASE_URL` | *(empty)* |
| Jira email | `JIRA_EMAIL`, `JIRA_USER` | *(empty)* |
| Jira API token | `JIRA_API_TOKEN`, `JIRA_API_KEY` | *(empty)* |
| Provider | `LLM_PROVIDER` | `Ollama` |
| Ollama URL | `OLLAMA_URL` | `http://localhost:11434` |
| Ollama model | `OLLAMA_MODEL` | `gemma3:1b` |
| Groq API key | `GROQ_API_KEY` | *(empty)* |
| Groq model | `GROQ_MODEL` | `openai/gpt-oss-120b` |

**No credentials are committed.** `.env` and `config.json` live in `src/` and are gitignored. Enter your own values via the Settings screen (or a local `.env`); nothing is hardcoded in source.

## Generation flow

```
[Chat] "create test cases for SAM1-1" + template + Send
      │
      ▼
jira_client.parse_issue_key ──► no key? → inline error, stop
      │  "SAM1-1"
      ▼
jira_client.fetch_issue ──► {summary, description, acceptance_criteria, ...}
      │
      ▼
llm_client.load_template(templates/<picked>.md)
      │
      ▼
llm_client.build_prompt(issue, template)
      │
      ▼
llm_client.generate(prompt, settings)
      ├── provider == Groq   → Groq only (Ollama never called)
      └── provider == Ollama → pre-flight GET /api/tags
                               ├── ok   → POST /api/chat
                               └── down → Groq, fallback_reason recorded
      │  {text, provider, model, fallback_reason}
      ▼
[Chat] assistant message + "provider · model · KEY" caption + Download button
```

Every failure (missing key, bad token, unreachable Jira, unavailable Ollama with no Groq key) surfaces as a specific message in the chat instead of a crash.

## Notes

- Groq is only called when Ollama is unreachable or the provider is explicitly set to `Groq`.
- The app never re-pulls `gemma3:1b`; it only reads `/api/tags` and calls `/api/chat`.
- Jira REST **v2** is used so both Cloud and Server return `description` as readable text (ADF is flattened when present).
