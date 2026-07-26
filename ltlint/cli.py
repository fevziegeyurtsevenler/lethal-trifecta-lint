"""lethal-trifecta-lint — flag the lethal trifecta in an agent's tool manifest.

    python -m ltlint.cli examples/trifecta_agent.json
    python -m ltlint.cli manifest.json --json out.json --quiet

Exit code 2 if the lethal trifecta is present (fails a CI gate), 0 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys

from .parse import parse_file
from .analyze import analyze, CAP_LABEL, CAP_ICON, CAPS

RED = "\033[31m"; GRN = "\033[32m"; YEL = "\033[33m"; DIM = "\033[2m"; BLD = "\033[1m"; RST = "\033[0m"


def _c(s, color, use):
    return f"{color}{s}{RST}" if use else s


def render(rep, color=True):
    out = []
    icon = {"ok": "✅", "warn": "⚠️", "danger": "🛑"}[rep.verdict]
    out.append(f"\n{icon} {_c('lethal-trifecta-lint', BLD, color)} — {len(rep.tools)} tool(s)")
    # per-tool table
    for c in rep.tools:
        marks = "".join(CAP_ICON[cap] if cap in c.caps else "·" for cap in CAPS)
        line = f"  {marks}  {c.name}"
        if set(CAPS) <= c.caps:
            line += _c("  ← single-tool trifecta", RED, color)
        out.append(line)
    out.append(f"  {DIM if color else ''}legend: {CAP_ICON[CAPS[0]]} private-data  "
               f"{CAP_ICON[CAPS[1]]} untrusted-intake  {CAP_ICON[CAPS[2]]} external-comm{RST if color else ''}")

    present = ", ".join(CAP_LABEL[c] for c in CAPS if c in rep.present_caps) or "none"
    out.append(f"\n  Capabilities present across the agent: {present}")

    if rep.verdict == "danger":
        out.append(_c("\n  🛑 LETHAL TRIFECTA PRESENT", RED + BLD, color))
        out.append("     This agent can access private data, ingest untrusted content, AND "
                   "communicate externally.\n     Untrusted content can instruct it to read private "
                   "data and exfiltrate it.")
        for a, b, why in rep.exfil_pairs[:8]:
            out.append(_c(f"     • {why}", RED, color))
        out.append("\n  Fixes: remove one leg of the trifecta — drop the egress tool, sandbox the "
                   "data\n     source, or gate untrusted input behind human review / an allow-list.")
    elif rep.verdict == "warn":
        out.append(_c("\n  ⚠️  Two of three trifecta capabilities present — one tool away from danger.", YEL, color))
    else:
        out.append(_c("\n  ✅ No lethal trifecta: the agent lacks at least one of the three capabilities.", GRN, color))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lethal-trifecta-lint",
                                 description="Flag the lethal trifecta in an agent tool manifest.")
    ap.add_argument("manifest", help="path to a tool manifest (MCP tools/list, OpenAI tools, LangChain export, or name list)")
    ap.add_argument("--json", dest="json_out", default=None, help="write the report as JSON")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="suppress the human report (still sets exit code)")
    ap.add_argument("--warn-exit", action="store_true", help="also exit non-zero (1) on a 2-of-3 warning")
    args = ap.parse_args(argv)

    tools = parse_file(args.manifest)
    rep = analyze(tools)

    if args.json_out:
        payload = {
            "verdict": rep.verdict,
            "trifecta": rep.trifecta,
            "present_capabilities": sorted(rep.present_caps),
            "single_tool_trifecta": rep.single_tool_trifecta,
            "exfil_pairs": [{"data_tool": a, "egress_tool": b, "reason": w} for a, b, w in rep.exfil_pairs],
            "tools": [{"name": c.name, "capabilities": sorted(c.caps), "evidence": c.evidence} for c in rep.tools],
        }
        json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if not args.quiet:
        sys.stdout.write(render(rep, color=not args.no_color))

    if rep.verdict == "danger":
        return 2
    if rep.verdict == "warn" and args.warn_exit:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
