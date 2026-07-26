"""Aggregate tool capabilities and detect the lethal trifecta + toxic tool combinations."""
from __future__ import annotations

from dataclasses import dataclass, field

from .classify import classify_tool, PRIVATE_DATA, UNTRUSTED, EXTERNAL_COMM, CAPS

CAP_LABEL = {
    PRIVATE_DATA: "private-data access",
    UNTRUSTED: "untrusted-content intake",
    EXTERNAL_COMM: "external communication",
}
CAP_ICON = {PRIVATE_DATA: "🔒", UNTRUSTED: "🌐", EXTERNAL_COMM: "📤"}


@dataclass
class Report:
    tools: list = field(default_factory=list)          # list[ToolClass]
    present_caps: set = field(default_factory=set)      # union across all tools
    trifecta: bool = False
    exfil_pairs: list = field(default_factory=list)     # [(toolA, toolB, reason)]
    single_tool_trifecta: list = field(default_factory=list)  # tools that alone hold all 3
    verdict: str = "ok"                                 # ok | warn | danger


def analyze(tools):
    """tools: list of {name, description, params}. Returns a Report."""
    classes = [classify_tool(t.get("name", ""), t.get("description", ""), t.get("params", [])) for t in tools]
    present = set()
    for c in classes:
        present |= c.caps

    rep = Report(tools=classes, present_caps=present)
    rep.trifecta = set(CAPS) <= present

    # single tools that themselves hold all three (the most dangerous)
    rep.single_tool_trifecta = [c.name for c in classes if set(CAPS) <= c.caps]

    # toxic pairs: one tool reaches private data (and is exposed to untrusted content
    # somewhere in the agent), another can send externally.
    data_tools = [c for c in classes if PRIVATE_DATA in c.caps]
    egress_tools = [c for c in classes if EXTERNAL_COMM in c.caps]
    if UNTRUSTED in present:
        for d in data_tools:
            for e in egress_tools:
                if d.name != e.name:
                    rep.exfil_pairs.append((
                        d.name, e.name,
                        f"'{d.name}' reads private data and '{e.name}' can send it out, "
                        f"while the agent also ingests untrusted content"))
    # dedupe pairs (unordered)
    seen = set(); uniq = []
    for a, b, why in rep.exfil_pairs:
        k = tuple(sorted((a, b)))
        if k not in seen:
            seen.add(k); uniq.append((a, b, why))
    rep.exfil_pairs = uniq

    if rep.trifecta:
        rep.verdict = "danger"
    elif len(present) == 2:
        rep.verdict = "warn"
    else:
        rep.verdict = "ok"
    return rep
