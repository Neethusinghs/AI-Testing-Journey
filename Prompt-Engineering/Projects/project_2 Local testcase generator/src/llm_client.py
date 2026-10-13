import re
from pathlib import Path

import requests

OLLAMA_DEFAULT_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "gemma3:1b"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_ENDPOINT = "https://api.groq.com/openai/v1/models"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"

FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*[ \t]*\n(.*)\n```$", re.DOTALL)

TEMPLATE_DIRS = (
    Path(__file__).resolve().parent / "templates",
    Path(__file__).resolve().parent.parent / "templates",
)

REQUIREMENT_PLACEHOLDERS = (
    "[PASTE REQUIREMENTS HERE]",
    "[PASTE REQUIREMENTS]",
    "[PASTE PRD HERE]",
)

STRICTNESS = (
    'Use ONLY the JIRA issue content provided. Where information is missing, write "Not specified" '
    "instead of inventing it. Return the result as a single markdown table with no extra commentary."
)


class LLMUnavailable(Exception):
    pass


def template_dir():
    for candidate in TEMPLATE_DIRS:
        if candidate.is_dir() and any(candidate.glob("*.md")):
            return candidate
    return TEMPLATE_DIRS[0]


def list_templates():
    return sorted(path.name for path in template_dir().glob("*.md"))


def load_template(name):
    path = template_dir() / Path(str(name)).name
    if not path.is_file():
        raise LLMUnavailable(f"Template '{name}' was not found in {template_dir()}.")
    return path.read_text(encoding="utf-8")


def _issue_block(issue):
    lines = [
        f"=== JIRA ISSUE {issue['key']} ===",
        f"Summary: {issue.get('summary') or 'Not specified'}",
        (
            "Type / Priority / Status: "
            f"{issue.get('issue_type') or 'Not specified'} / "
            f"{issue.get('priority') or 'Not specified'} / "
            f"{issue.get('status') or 'Not specified'}"
        ),
        "Description:",
        issue.get("description") or "Not specified",
    ]
    if issue.get("acceptance_criteria"):
        lines += ["", "Acceptance Criteria:", issue["acceptance_criteria"]]
    if issue.get("labels"):
        lines += ["", "Labels: " + ", ".join(issue["labels"])]
    lines.append(f"=== END JIRA ISSUE {issue['key']} ===")
    return "\n".join(lines)


def build_prompt(issue, template_text):
    block = _issue_block(issue)
    prompt = template_text
    replaced = False

    for placeholder in REQUIREMENT_PLACEHOLDERS:
        if placeholder in prompt:
            prompt = prompt.replace(placeholder, block)
            replaced = True

    if "[FEATURE]" in prompt:
        prompt = prompt.replace("[FEATURE]", issue.get("summary") or issue["key"])
        replaced = True

    if "[NUMBER]" in prompt:
        prompt = prompt.replace("[NUMBER]", "an appropriate number of")
        replaced = True

    if not replaced:
        prompt = f"{prompt.rstrip()}\n\nREQUIREMENTS:\n{block}"

    return f"{prompt.rstrip()}\n\n{STRICTNESS}\n"


def _ollama_url(settings):
    return (settings.get("ollama_url") or OLLAMA_DEFAULT_URL).strip().rstrip("/")


def _ollama_model(settings):
    return (settings.get("ollama_model") or OLLAMA_DEFAULT_MODEL).strip()


def _groq_model(settings):
    return (settings.get("groq_model") or GROQ_DEFAULT_MODEL).strip()


def _ollama_reachable(settings):
    url = _ollama_url(settings)
    model = _ollama_model(settings)
    try:
        response = requests.get(f"{url}/api/tags", timeout=5)
    except requests.exceptions.RequestException:
        return False, f"Ollama is not reachable at {url}."
    if response.status_code >= 400:
        return False, f"Ollama at {url} returned HTTP {response.status_code}."
    try:
        names = {
            item.get("name", "")
            for item in (response.json().get("models") or [])
            if isinstance(item, dict)
        }
    except ValueError:
        return False, f"Ollama at {url} returned an unreadable response."
    wanted = model if ":" in model else f"{model}:latest"
    if wanted not in names:
        return False, f"Ollama is running but model '{model}' is not present."
    return True, "ok"


def _unwrap_fence(text):
    stripped = text.strip()
    match = FENCE_RE.match(stripped)
    if match and "```" not in match.group(1):
        return match.group(1).strip()
    return stripped


def _call_ollama(prompt, settings):
    url = _ollama_url(settings)
    model = _ollama_model(settings)
    try:
        response = requests.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=(5, 180),
        )
    except requests.exceptions.RequestException as exc:
        raise LLMUnavailable(f"Ollama request to {url} failed: {exc}")

    if response.status_code == 404:
        raise LLMUnavailable(f"Ollama has no model named '{model}'.")
    if response.status_code >= 400:
        raise LLMUnavailable(f"Ollama returned HTTP {response.status_code}.")

    try:
        content = ((response.json().get("message") or {}).get("content") or "").strip()
    except ValueError:
        raise LLMUnavailable("Ollama returned an unreadable response.")
    if not content:
        raise LLMUnavailable("Ollama returned an empty response.")
    return _unwrap_fence(content)


def list_groq_models(settings):
    api_key = (settings.get("groq_api_key") or "").strip()
    if not api_key:
        return []
    try:
        response = requests.get(
            GROQ_MODELS_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
    except requests.exceptions.RequestException:
        return []
    if response.status_code >= 400:
        return []
    try:
        return sorted(
            item["id"]
            for item in (response.json().get("data") or [])
            if isinstance(item, dict) and item.get("id")
        )
    except (ValueError, TypeError):
        return []


def _call_groq(prompt, settings):
    api_key = (settings.get("groq_api_key") or "").strip()
    if not api_key:
        raise LLMUnavailable("No Groq API key is set. Add one on the Settings screen.")

    model = _groq_model(settings)
    try:
        response = requests.post(
            GROQ_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=(5, 180),
        )
    except requests.exceptions.RequestException as exc:
        raise LLMUnavailable(f"Groq request failed: {exc}")

    if response.status_code in (401, 403):
        raise LLMUnavailable("Groq rejected the API key.")
    if response.status_code == 404:
        available = list_groq_models(settings)
        hint = f" Available on this key: {', '.join(available)}." if available else ""
        raise LLMUnavailable(
            f"Groq does not have '{model}' available for this account.{hint}"
        )
    if response.status_code == 429:
        raise LLMUnavailable("Groq rate limit reached. Try again shortly.")
    if response.status_code >= 400:
        raise LLMUnavailable(f"Groq returned HTTP {response.status_code}.")

    try:
        choices = response.json().get("choices") or []
        content = (
            ((choices[0].get("message") or {}).get("content") or "").strip()
            if choices
            else ""
        )
    except ValueError:
        raise LLMUnavailable("Groq returned an unreadable response.")
    if not content:
        raise LLMUnavailable("Groq returned an empty response.")
    return _unwrap_fence(content)


def generate(prompt, settings):
    provider = settings.get("provider") or "Ollama"

    if provider == "Groq":
        return {
            "text": _call_groq(prompt, settings),
            "provider": "Groq",
            "model": _groq_model(settings),
            "fallback_reason": "",
        }

    reachable, reason = _ollama_reachable(settings)
    if reachable:
        try:
            return {
                "text": _call_ollama(prompt, settings),
                "provider": "Ollama",
                "model": _ollama_model(settings),
                "fallback_reason": "",
            }
        except LLMUnavailable as exc:
            reason = str(exc)

    if not (settings.get("groq_api_key") or "").strip():
        raise LLMUnavailable(
            f"{reason} Add a Groq API key in Settings to enable the hosted fallback."
        )

    return {
        "text": _call_groq(prompt, settings),
        "provider": "Groq",
        "model": _groq_model(settings),
        "fallback_reason": reason,
    }


def check_ollama(settings):
    reachable, reason = _ollama_reachable(settings)
    if reachable:
        return True, f"Ollama is reachable and '{_ollama_model(settings)}' is available."
    return False, reason


def check_groq(settings):
    try:
        _call_groq("Reply with the single word: ok", settings)
    except LLMUnavailable as exc:
        return False, str(exc)
    return True, f"Groq replied using '{_groq_model(settings)}'."
