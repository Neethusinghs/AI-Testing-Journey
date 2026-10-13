import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
CONFIG_PATH = BASE_DIR / "config.json"

PROVIDERS = ("Ollama", "Groq")

DEFAULTS = {
    "jira_url": "",
    "jira_email": "",
    "jira_token": "",
    "provider": "Ollama",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "gemma3:1b",
    "groq_api_key": "",
    "groq_model": "openai/gpt-oss-120b",
}

ENV_ALIASES = {
    "jira_url": ("JIRA_URL", "JIRA_BASE_URL"),
    "jira_email": ("JIRA_EMAIL", "JIRA_USER", "JIRA_USERNAME"),
    "jira_token": ("JIRA_API_TOKEN", "JIRA_API_KEY", "JIRA_TOKEN"),
    "provider": ("LLM_PROVIDER", "PROVIDER"),
    "ollama_url": ("OLLAMA_URL",),
    "ollama_model": ("OLLAMA_MODEL", "OLLAMA_TAG"),
    "groq_api_key": ("GROQ_API_KEY", "GROQ_API_TOKEN", "GROQ_TOKEN", "GROQ_KEY"),
    "groq_model": ("GROQ_MODEL",),
}


def config_path():
    return str(CONFIG_PATH)


def _read_config():
    if not CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _normalise_provider(value):
    provider = (value or "").strip().capitalize()
    return provider if provider in PROVIDERS else DEFAULTS["provider"]


def env_keys_present():
    load_dotenv(ENV_PATH, override=False)
    return [
        name
        for names in ENV_ALIASES.values()
        for name in names
        if (os.getenv(name) or "").strip()
    ]


def load_settings():
    settings = dict(DEFAULTS)
    load_dotenv(ENV_PATH, override=False)
    for setting_key, env_names in ENV_ALIASES.items():
        for env_name in env_names:
            value = (os.getenv(env_name) or "").strip()
            if value:
                settings[setting_key] = value
                break
    for setting_key, value in _read_config().items():
        if setting_key in DEFAULTS and isinstance(value, str) and value.strip():
            settings[setting_key] = value.strip()
    settings["provider"] = _normalise_provider(settings["provider"])
    return settings


def save_settings(values):
    merged = load_settings()
    for setting_key in DEFAULTS:
        candidate = values.get(setting_key)
        if isinstance(candidate, str):
            merged[setting_key] = candidate.strip()
    merged["provider"] = _normalise_provider(merged["provider"])
    temp_path = CONFIG_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    os.replace(temp_path, CONFIG_PATH)
    return merged


def is_configured(settings):
    return all(
        (settings.get(key) or "").strip()
        for key in ("jira_url", "jira_email", "jira_token")
    )
