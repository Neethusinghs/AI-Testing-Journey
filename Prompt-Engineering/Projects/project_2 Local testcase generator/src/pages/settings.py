import streamlit as st

import config_store
import llm_client

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

settings = config_store.load_settings()

st.title("Settings")
st.caption("Saved locally to config.json. Values in .env are used until you save here.")

with st.form("settings_form"):
    st.subheader("Jira")
    jira_url = st.text_input(
        "Jira URL",
        value=settings["jira_url"],
        placeholder="https://your-domain.atlassian.net",
    )
    jira_email = st.text_input("Jira email ID", value=settings["jira_email"])
    jira_token = st.text_input(
        "Jira API token", value=settings["jira_token"], type="password"
    )
    st.caption("Leave the token field untouched to keep the stored value.")

    st.subheader("LLM provider")
    provider = st.radio(
        "Provider",
        config_store.PROVIDERS,
        index=config_store.PROVIDERS.index(settings["provider"]),
        horizontal=True,
    )
    st.caption(
        "Ollama is the default. Groq is called only when Ollama is unavailable or you select it here."
    )

    st.subheader("Ollama")
    ollama_url = st.text_input("Ollama URL", value=settings["ollama_url"])
    ollama_model = st.text_input("Ollama model", value=settings["ollama_model"])

    st.subheader("Groq")
    groq_api_key = st.text_input(
        "Groq API key", value=settings["groq_api_key"], type="password"
    )
    groq_model = st.text_input("Groq model", value=settings["groq_model"])

    saved = st.form_submit_button("Save Settings", type="primary")

if saved:
    config_store.save_settings(
        {
            "jira_url": jira_url,
            "jira_email": jira_email,
            "jira_token": jira_token,
            "provider": provider,
            "ollama_url": ollama_url,
            "ollama_model": ollama_model,
            "groq_api_key": groq_api_key,
            "groq_model": groq_model,
        }
    )
    st.session_state["settings_saved"] = True
    st.rerun()

st.divider()
st.subheader("Connection tests")
st.caption("These use the saved settings, not unsaved edits in the form above.")

left, right = st.columns(2)

if left.button("Test Ollama"):
    ollama_ok, ollama_detail = llm_client.check_ollama(config_store.load_settings())
    if ollama_ok:
        st.success(ollama_detail)
    else:
        st.error(ollama_detail)

if right.button("Test Groq"):
    groq_ok, groq_detail = llm_client.check_groq(config_store.load_settings())
    if groq_ok:
        st.success(groq_detail)
    else:
        st.error(groq_detail)

st.divider()
st.subheader("Storage")
st.caption(f"config.json: {config_store.config_path()}")
env_keys = config_store.env_keys_present()
st.caption("Read from .env: " + (", ".join(env_keys) if env_keys else "nothing"))
st.caption(".env and config.json are gitignored and must not be committed.")
