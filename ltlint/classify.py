"""Classify each agent tool by the three capabilities of the *lethal trifecta*.

The "lethal trifecta" (Simon Willison, 2025) is the observation that an AI agent is
dangerous exactly when it combines three abilities:

  1. PRIVATE_DATA   — access to private / sensitive data
  2. UNTRUSTED      — exposure to untrusted content (which can carry injected instructions)
  3. EXTERNAL_COMM  — the ability to communicate externally (to exfiltrate)

Any single tool may provide more than one of these. We tag each tool from its name,
description, and parameter names using auditable keyword sets — a heuristic, not a proof.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PRIVATE_DATA = "private_data"
UNTRUSTED = "untrusted"
EXTERNAL_COMM = "external_comm"

CAPS = (PRIVATE_DATA, UNTRUSTED, EXTERNAL_COMM)

# Keyword seeds. Word-boundary matched, case-insensitive. Kept explicit so a reviewer
# can see and adjust exactly why a tool was tagged.
_SEEDS = {
    PRIVATE_DATA: [
        "read_file", "readfile", "read file", "get_file", "open_file", "cat_file",
        "filesystem", "fs_read", "list_dir", "list_directory", "glob", "grep",
        "database", "db_query", "sql", "select", "query", "datastore", "vector_store",
        "read_email", "get_email", "inbox", "gmail", "mailbox", "read_calendar",
        "calendar", "contacts", "address_book", "notion", "confluence", "gdrive",
        "google_drive", "dropbox", "onedrive", "sharepoint", "s3_get", "get_object",
        "secret", "credential", "api_key", "token", "env", "environment", "vault",
        "get_repo", "read_repo", "source_code", "read_code", "private", "internal",
        "customer", "user_data", "pii", "medical", "financial", "bank", "salary",
    ],
    UNTRUSTED: [
        "fetch_url", "fetch", "browse", "browser", "web_search", "websearch",
        "http_get", "get_url", "read_url", "read_webpage", "scrape", "crawl",
        "rss", "load_document", "load_url", "read_pdf", "parse_html", "url",
        "read_email", "get_email", "inbox", "read_issue", "read_pr",
        "read_comment", "read_review", "pull_request", "issue_body", "webhook_in",
        "incoming", "user_input", "external_content", "third_party", "attachment",
        "download",
    ],
    EXTERNAL_COMM: [
        "send_email", "send_mail", "sendmail", "smtp", "email_send", "post_message",
        "send_message", "send_slack", "slack_post", "post_slack", "discord",
        "telegram", "sms", "twilio", "http_post", "post_url", "webhook", "publish",
        "upload", "put_object", "s3_put", "create_issue", "create_pr", "comment",
        "tweet", "post_tweet", "notify", "http_request", "request", "curl", "fetch_url",
        "browse", "send", "share", "export", "forward",
    ],
}

# Tools that are inherently both: e.g. an email reader ingests untrusted content AND reads private mail.
_MULTI = {
    "read_email": (PRIVATE_DATA, UNTRUSTED),
    "get_email": (PRIVATE_DATA, UNTRUSTED),
    "inbox": (PRIVATE_DATA, UNTRUSTED),
    "gmail": (PRIVATE_DATA, UNTRUSTED),
    "fetch_url": (UNTRUSTED, EXTERNAL_COMM),   # a GET can smuggle data out in the query string
    "browse": (UNTRUSTED, EXTERNAL_COMM),
    "http_request": (UNTRUSTED, EXTERNAL_COMM),
}


def _matches(text: str, seeds):
    hits = []
    for kw in seeds:
        # word-ish boundary: allow _ and spaces as separators
        if re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", text):
            hits.append(kw)
    return hits


@dataclass
class ToolClass:
    name: str
    caps: set = field(default_factory=set)
    evidence: dict = field(default_factory=dict)   # cap -> [keywords]


def classify_tool(name: str, description: str = "", params=None) -> ToolClass:
    params = params or []
    blob = " ".join([str(name or ""), str(description or ""), " ".join(str(p) for p in params)]).lower()
    tc = ToolClass(name=name or "<unnamed>")
    for cap, seeds in _SEEDS.items():
        hits = _matches(blob, seeds)
        if hits:
            tc.caps.add(cap)
            tc.evidence[cap] = sorted(set(hits))[:6]
    # multi-capability shortcuts
    lname = (name or "").lower()
    for key, caps in _MULTI.items():
        if key in lname or key in blob:
            for c in caps:
                tc.caps.add(c)
                tc.evidence.setdefault(c, [])
                if key not in tc.evidence[c]:
                    tc.evidence[c].append(key)
    return tc
