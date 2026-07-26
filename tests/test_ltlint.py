import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ltlint.classify import classify_tool, PRIVATE_DATA, UNTRUSTED, EXTERNAL_COMM
from ltlint.parse import parse_manifest
from ltlint.analyze import analyze
from ltlint.cli import main

HERE = os.path.dirname(__file__)
EX = os.path.join(HERE, "..", "examples")


def test_classify_basic():
    assert PRIVATE_DATA in classify_tool("read_file", "Read a workspace file").caps
    assert EXTERNAL_COMM in classify_tool("send_email", "Send an email").caps
    assert UNTRUSTED in classify_tool("fetch_url", "Fetch a web page").caps
    assert classify_tool("calculator", "Evaluate arithmetic").caps == set()


def test_multi_capability_tools():
    email = classify_tool("read_email", "Read the user's inbox")
    assert {PRIVATE_DATA, UNTRUSTED} <= email.caps
    fetch = classify_tool("fetch_url", "GET a url")
    assert {UNTRUSTED, EXTERNAL_COMM} <= fetch.caps


def test_parse_formats():
    mcp = parse_manifest({"tools": [{"name": "a", "inputSchema": {"properties": {"x": {}}}}]})
    assert mcp[0]["name"] == "a" and mcp[0]["params"] == ["x"]
    openai = parse_manifest([{"type": "function", "function": {"name": "b", "parameters": {"properties": {"y": {}}}}}])
    assert openai[0]["name"] == "b" and openai[0]["params"] == ["y"]
    lc = parse_manifest([{"name": "c", "args_schema": {"properties": {"z": {}}}}])
    assert lc[0]["name"] == "c"
    names = parse_manifest(["read_file", "send_email"])
    assert [t["name"] for t in names] == ["read_file", "send_email"]


def test_trifecta_detected():
    tools = [{"name": "read_file"}, {"name": "fetch_url"}, {"name": "send_email"}]
    rep = analyze(tools)
    assert rep.trifecta and rep.verdict == "danger"
    assert rep.exfil_pairs  # at least one data->egress path


def test_no_trifecta_when_missing_leg():
    rep = analyze([{"name": "read_file"}, {"name": "calculator"}])
    assert not rep.trifecta and rep.verdict == "ok"


def test_single_tool_trifecta():
    rep = analyze([{"name": "email_assistant", "description": "read inbox from untrusted senders and send replies"}])
    assert rep.trifecta
    assert "email_assistant" in rep.single_tool_trifecta


def test_warn_two_of_three():
    rep = analyze([{"name": "read_database"}, {"name": "post_slack_message"}])
    assert not rep.trifecta and rep.verdict == "warn"


def test_cli_exit_codes():
    assert main([os.path.join(EX, "trifecta_agent.json"), "--quiet"]) == 2
    assert main([os.path.join(EX, "safe_agent.json"), "--quiet"]) == 0
    assert main([os.path.join(EX, "single_tool_trifecta.json"), "--quiet"]) == 2
    assert main([os.path.join(EX, "warn_agent.json"), "--quiet"]) == 0
    assert main([os.path.join(EX, "warn_agent.json"), "--quiet", "--warn-exit"]) == 1
