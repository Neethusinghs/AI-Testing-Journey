import re

import requests
from requests.auth import HTTPBasicAuth

ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
AC_HEADING_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:acceptance criteria|acceptance criterion|ac)[ \t]*:?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
SECTION_LABEL_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?[A-Z][A-Za-z ]{1,40}:[ \t]*$", re.MULTILINE
)
FIELDS = "summary,description,issuetype,priority,status,labels"


class JiraError(Exception):
    pass


def parse_issue_key(text):
    if not text:
        return None
    match = ISSUE_KEY_RE.search(text.upper())
    return match.group(0) if match else None


def _adf_to_text(node):
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(
            part for part in (_adf_to_text(item) for item in node) if part
        )
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "text":
            return node.get("text", "")
        if node_type == "hardBreak":
            return "\n"
        text = _adf_to_text(node.get("content"))
        if node_type in ("paragraph", "heading", "listItem", "codeBlock", "blockquote"):
            return f"{text}\n"
        return text
    return ""


def _extract_acceptance_criteria(description):
    if not description:
        return ""
    match = AC_HEADING_RE.search(description)
    if not match:
        return ""
    section = description[match.end():]
    stop = SECTION_LABEL_RE.search(section)
    if stop:
        section = section[: stop.start()]
    return section.strip()


def fetch_issue(key, settings):
    base = (settings.get("jira_url") or "").strip().rstrip("/")
    if not base:
        raise JiraError("Jira URL is not set. Add it on the Settings screen.")

    try:
        response = requests.get(
            f"{base}/rest/api/2/issue/{key}",
            params={"fields": FIELDS},
            auth=HTTPBasicAuth(
                settings.get("jira_email", ""), settings.get("jira_token", "")
            ),
            headers={"Accept": "application/json"},
            timeout=15,
        )
    except requests.exceptions.Timeout:
        raise JiraError(f"Timed out reaching Jira at {base}.")
    except requests.exceptions.RequestException as exc:
        raise JiraError(f"Cannot reach Jira at {base}: {exc}")

    if response.status_code in (401, 403):
        raise JiraError(
            "Jira rejected the credentials. Re-check the email and API token in Settings."
        )
    if response.status_code == 404:
        raise JiraError(f"Issue {key} was not found on {base}.")
    if response.status_code >= 400:
        raise JiraError(f"Jira returned HTTP {response.status_code} for {key}.")

    payload = response.json()
    fields = payload.get("fields") or {}
    resolved_key = payload.get("key") or key
    description = _adf_to_text(fields.get("description")).strip()

    return {
        "key": resolved_key,
        "summary": (fields.get("summary") or "").strip(),
        "description": description,
        "acceptance_criteria": _extract_acceptance_criteria(description),
        "issue_type": ((fields.get("issuetype") or {}).get("name") or "").strip(),
        "priority": ((fields.get("priority") or {}).get("name") or "").strip(),
        "status": ((fields.get("status") or {}).get("name") or "").strip(),
        "labels": [str(label) for label in (fields.get("labels") or [])],
        "url": f"{base}/browse/{resolved_key}",
    }
