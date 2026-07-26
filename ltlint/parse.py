"""Parse agent tool manifests from several common formats into a common shape:
a list of {name, description, params}.

Supported (auto-detected):
  - MCP `tools/list` response       : {"tools": [{"name","description","inputSchema":{"properties":{...}}}]}
  - OpenAI / Anthropic tools array  : [{"type":"function","function":{"name","description","parameters":{...}}}]
                                       or [{"name","description","input_schema"/"parameters":{...}}]
  - LangChain-style export          : [{"name","description","args"/"args_schema":{...}}]
  - a plain list of tool names      : ["read_file", "send_email", ...]
"""
from __future__ import annotations

import json


def _props(schema):
    if not isinstance(schema, dict):
        return []
    props = schema.get("properties") or {}
    if isinstance(props, dict):
        return list(props.keys())
    return []


def _one(obj):
    """Normalize a single tool-ish object to {name, description, params}."""
    if isinstance(obj, str):
        return {"name": obj, "description": "", "params": []}
    if not isinstance(obj, dict):
        return None
    # OpenAI function wrapper
    if obj.get("type") == "function" and isinstance(obj.get("function"), dict):
        f = obj["function"]
        return {"name": f.get("name", ""), "description": f.get("description", ""),
                "params": _props(f.get("parameters"))}
    name = obj.get("name") or obj.get("tool") or obj.get("tool_name") or ""
    desc = obj.get("description") or obj.get("desc") or ""
    schema = (obj.get("inputSchema") or obj.get("input_schema") or obj.get("parameters")
              or obj.get("args_schema") or obj.get("args") or {})
    params = _props(schema)
    if not params and isinstance(obj.get("args"), dict):
        params = list(obj["args"].keys())
    if not name:
        return None
    return {"name": name, "description": desc, "params": params}


def parse_manifest(data):
    """Accept a dict or list (already-parsed JSON) and return a list of tool dicts."""
    tools = []
    if isinstance(data, dict):
        if "tools" in data and isinstance(data["tools"], list):
            data = data["tools"]
        elif "functions" in data and isinstance(data["functions"], list):
            data = data["functions"]
        else:
            # maybe a single tool object
            one = _one(data)
            return [one] if one else []
    if isinstance(data, list):
        for item in data:
            t = _one(item)
            if t:
                tools.append(t)
    return tools


def parse_file(path):
    with open(path, encoding="utf-8") as fh:
        return parse_manifest(json.load(fh))
