import streamlit as st

import config_store
import jira_client
import llm_client

EXAMPLES = ("create test cases for SAM1-1", "create test cases for SAM1-2")

st.set_page_config(
    page_title="Local Testcase Generator", page_icon="🧪", layout="wide"
)


def render_sidebar(settings, configured):
    with st.sidebar:
        st.subheader("Status")
        if configured:
            st.success("Ready")
        else:
            st.warning("Jira credentials are not set")
            st.page_link("pages/settings.py", label="Open Settings")
        provider = settings["provider"]
        model = (
            settings["ollama_model"] if provider == "Ollama" else settings["groq_model"]
        )
        st.caption(f"Provider: {provider} · {model}")
        st.caption(f"Ollama: {settings['ollama_url']}")
        st.caption(f"Jira: {settings['jira_url'] or 'not set'}")
        st.caption(f"Groq fallback: {'key set' if settings['groq_api_key'] else 'no key'}")


def render_history():
    history = st.session_state.history
    last_index = len(history) - 1
    for index, message in enumerate(history):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("meta"):
                st.caption(message["meta"])
            if (
                message["role"] == "assistant"
                and message.get("key")
                and index == last_index
            ):
                st.download_button(
                    "Download test cases (.md)",
                    message["content"],
                    file_name=f"{message['key']}_testcases.md",
                    mime="text/markdown",
                    key=f"download_{index}",
                )


def run_pipeline(text, template_name, settings):
    key = jira_client.parse_issue_key(text)
    if not key:
        raise ValueError(
            "No Jira issue key found in that message. Try: create test cases for SAM1-1"
        )
    issue = jira_client.fetch_issue(key, settings)
    if not issue["description"] and not issue["acceptance_criteria"]:
        raise ValueError(
            f"{issue['key']} has no description or acceptance criteria on Jira, "
            "so there is nothing to generate test cases from. Add requirements to "
            "the ticket first."
        )
    template = llm_client.load_template(template_name)
    prompt = llm_client.build_prompt(issue, template)
    return issue, llm_client.generate(prompt, settings)


def main():
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("draft", [])
    if st.session_state.pop("settings_saved", False):
        st.success("Settings saved.")

    settings = config_store.load_settings()
    configured = config_store.is_configured(settings)
    render_sidebar(settings, configured)

    st.title("Local Testcase Generator")
    st.caption(
        "Ask for test cases using a Jira issue key. Ollama runs locally; Groq is the fallback."
    )

    templates = llm_client.list_templates()
    render_history()

    if not configured:
        st.info(
            "Add your Jira URL, email, and API token on the Settings screen to get started."
        )
        st.page_link("pages/settings.py", label="Open Settings")

    if not templates:
        st.error(f"No templates found in {llm_client.template_dir()}.")
        return

    for column, example in zip(st.columns(len(EXAMPLES)), EXAMPLES):
        if column.button(example, disabled=not configured):
            st.session_state.draft = example
            st.rerun()

    with st.form("chat_form", clear_on_submit=True):
        text = st.text_input(
            "Ask for test cases",
            value=st.session_state.draft,
            placeholder="create test cases for QA-102",
            disabled=not configured,
        )
        template_name = st.selectbox("Template", templates)
        submitted = st.form_submit_button(
            "Send", type="primary", disabled=not configured
        )

    if not submitted:
        return

    st.session_state.draft = ""
    message = (text or "").strip()
    if not message:
        return

    st.session_state.history.append({"role": "user", "content": message})

    with st.spinner("Fetching the ticket and generating test cases..."):
        try:
            issue, result = run_pipeline(message, template_name, settings)
        except (ValueError, jira_client.JiraError, llm_client.LLMUnavailable) as exc:
            st.session_state.history.append(
                {
                    "role": "assistant",
                    "content": f"**Could not generate test cases.**\n\n{exc}",
                }
            )
        except Exception as exc:
            st.session_state.history.append(
                {
                    "role": "assistant",
                    "content": f"**Unexpected error.**\n\n`{type(exc).__name__}: {exc}`",
                }
            )
        else:
            meta = f"{result['provider']} · {result['model']} · {issue['key']}"
            if result["fallback_reason"]:
                meta += f" · fell back from Ollama: {result['fallback_reason']}"
            st.session_state.history.append(
                {
                    "role": "assistant",
                    "content": result["text"],
                    "meta": meta,
                    "key": issue["key"],
                }
            )

    st.rerun()


main()
