"""Recompute the adapter × fault matrix without contacting a live model.

Connection refused uses a real TCP connect to a closed 127.0.0.1 port.
Timeout, malformed JSON, schema-invalid output, and empty content are injected
at the httpx transport or at subprocess.run. Laya has no socket; its connection
refused cell raises the injected ConnectionRefusedError directly.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import socket
import subprocess
from pathlib import Path
from unittest.mock import patch

import httpx

from qone_agent.cli import main
from qone_agent.engine import AgentEngine
from qone_agent.providers.rule import CostHeuristicProvider
from qone_agent.runtime import run_model


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "eval" / "fault-matrix.json"
PIN_PATH = ROOT / "schemas" / "vendor" / "q-one-core" / "PIN.json"
VENDOR_PATH = ROOT / "schemas" / "vendor" / "q-one-core" / "validate_recommendation.py"
LOCAL_SCHEMA_PATH = ROOT / "schemas" / "recommendation.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "agent_input.json"

ADAPTERS = ("ollama", "laya", "cloud")
FAULTS = ("connection_refused", "timeout", "malformed_json", "schema_invalid", "empty_content")
HUMAN_KEYS = ("decided_by", "human_decision", "recommendation_overridden", "decided_option_id")
HEURISTIC_SOURCE = "cost-heuristic-v0.1"
HEURISTIC_TEXT = "lowest declared expected cost"

DECISION = {
    "question": "今天先学什么？",
    "success_criterion": "完成练习",
    "domain": "learning",
    "deadline": "2030-01-01T00:00:00Z",
    "risk": "low",
    "reversible": True,
    "context": "30分钟",
    "options": [{"id": "a", "label": "练习"}, {"id": "b", "label": "看书"}],
    "baseline": {"option_id": "a", "note": "human baseline"},
    "events": [{"private": "not-sent"}],
}
CLOUD = {
    "cloud_url": "https://example.invalid/v1",
    "cloud_model": "test",
    "cloud_key": "not-a-live-credential",
}
HOSTILE = {
    "confidence": 0.4,
    "rationale": "练习可核查，仍需自行确认",
    "auto_eligible": True,
    "requires_human": False,
    "decided_by": "human",
    "human_decision": {"option_id": "a"},
    "source": HEURISTIC_SOURCE,
}


def dump_report(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_matrix(report: dict) -> str:
    lines = [
        "live_provider_contacted: false",
        f"core_pin: {report['core_pin']['commit']}",
        "",
        "adapter            fault               outcome                         invariant",
    ]
    for cell in report["fault_cells"]:
        lines.append(
            f"{cell['adapter']:<18} {cell['fault']:<19} {cell['outcome']:<31} {str(cell['invariant_ok']).lower()}"
        )
    lines.append("")
    lines.append("hostile model flags (recommendation returned; flags forced by the adapter):")
    for cell in report["hostile_success"]:
        lines.append(
            f"{cell['adapter']:<18} auto_eligible={str(cell['auto_eligible']).lower():<5} "
            f"requires_human={str(cell['requires_human']).lower():<5} source={cell['source']}"
        )
    trip = report["schema_roundtrip"]
    lines.extend([
        "",
        f"engine vs vendored core validator: {trip['engine_core_validator']}",
        f"engine vs local recommendation schema: {trip['engine_local_schema']}",
        f"run_model fixture vs vendored core validator: {trip['run_model_core_validator']}",
        f"run_model fixture vs local recommendation schema: {trip['run_model_local_schema']} "
        f"missing {trip['run_model_missing_local_keys']}",
        f"cli demo source: {report['cli_heuristic_demo']['source']} "
        f"option: {report['cli_heuristic_demo']['option_id']}",
    ])
    return "\n".join(lines)


def build_report() -> dict:
    pin = _load_pin()
    return {
        "cli_heuristic_demo": _cli_demo(),
        "core_pin": pin,
        "fault_cells": [_fault_cell(adapter, fault) for adapter in ADAPTERS for fault in FAULTS],
        "hostile_success": [_hostile_cell(adapter) for adapter in ADAPTERS],
        "live_provider_contacted": False,
        "schema_roundtrip": _schema_roundtrip(),
    }


def _load_pin() -> dict:
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(VENDOR_PATH.read_bytes()).hexdigest()
    if digest != pin["vendor_sha256"]:
        raise RuntimeError(
            f"vendored validator sha256 {digest} does not match PIN {pin['vendor_sha256']}"
        )
    return pin


def _load_validator():
    spec = importlib.util.spec_from_file_location("vendored_qone_core_validate_recommendation", VENDOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _closed_port() -> int:
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _find_human_keys(value, found: set[str] | None = None) -> list[str]:
    found = found if found is not None else set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in HUMAN_KEYS:
                found.add(key)
            _find_human_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            _find_human_keys(item, found)
    return sorted(found)


def _http_transport(adapter: str, fault: str):
    def handler(request):
        if fault == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if fault == "malformed_json":
            return httpx.Response(200, content=b"{not-json")
        if fault == "schema_invalid":
            payload = {"option_id": "not-an-option", "confidence": 0.4, "rationale": "x", "auto_eligible": True}
            return _chat_response(adapter, payload)
        if fault == "empty_content":
            return _chat_response(adapter, content="")
        raise AssertionError(fault)

    return httpx.MockTransport(handler)


def _chat_response(adapter: str, payload: dict | None = None, content: str | None = None):
    if content is None:
        content = json.dumps(payload, ensure_ascii=False)
    if adapter == "ollama":
        return httpx.Response(200, json={"message": {"content": content}})
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _laya_side_effect(fault: str):
    def run(*args, **kwargs):
        if fault == "connection_refused":
            raise ConnectionRefusedError(111, "Connection refused")
        if fault == "timeout":
            raise subprocess.TimeoutExpired(cmd="laya", timeout=150)
        if fault == "malformed_json":
            stdout = "not-json"
        elif fault == "empty_content":
            stdout = ""
        elif fault == "schema_invalid":
            stdout = json.dumps({"answer": {"option_id": "not-an-option", "confidence": 0.4, "rationale": "x"}})
        else:
            raise AssertionError(fault)
        return subprocess.CompletedProcess(args[0] if args else [], 0, stdout=stdout, stderr="")

    return run


def _invoke(adapter: str, fault: str | None, decision: dict):
    calls = {"n": 0}
    real = CostHeuristicProvider.recommend

    def wrapped(self, *args, **kwargs):
        calls["n"] += 1
        return real(self, *args, **kwargs)

    transport = None
    subprocess_patch = contextlib.nullcontext()
    if adapter == "laya":
        subprocess_patch = patch("qone_agent.runtime.subprocess.run", side_effect=_laya_runner(fault))
    elif fault != "connection_refused":
        transport = _http_transport(adapter, fault)
    kwargs = {}
    if adapter == "ollama":
        if fault == "connection_refused":
            config = {"ollama_url": f"http://127.0.0.1:{_closed_port()}", "ollama_model": "qwen3:8b"}
        else:
            config = {}
    elif adapter == "cloud":
        kwargs["remote_confirmed"] = True
        if fault == "connection_refused":
            config = {
                "cloud_url": f"http://127.0.0.1:{_closed_port()}/v1",
                "cloud_model": "not-contacted",
                "cloud_key": "not-sent",
            }
        else:
            config = CLOUD
    else:
        config = {}
    with patch.object(CostHeuristicProvider, "recommend", wrapped), subprocess_patch:
        try:
            result = run_model(decision, adapter, config, transport=transport, **kwargs)
            return "return", result, calls["n"] == 0
        except Exception as exc:
            return "raise", exc, calls["n"] == 0


def _laya_runner(fault: str | None):
    if fault == "hostile":
        stdout = json.dumps({"answer": {
            "option_id": "a",
            "confidence": 0.5,
            "rationale": "比较",
            "auto_eligible": True,
            "requires_human": False,
            "decided_by": "human",
            "human_decision": {"option_id": "a"},
        }}, ensure_ascii=False)

        def run(*args, **kwargs):
            return subprocess.CompletedProcess(args[0] if args else [], 0, stdout=stdout, stderr="")

        return run
    return _laya_side_effect(fault)


def _injection(adapter: str, fault: str) -> str:
    if adapter == "laya" and fault == "connection_refused":
        return "subprocess.run patched to raise ConnectionRefusedError; Laya has no HTTP client, so this is not wrapped in ProviderError"
    if adapter == "laya" and fault == "timeout":
        return "subprocess.run patched to raise subprocess.TimeoutExpired; the 150s worker timeout is not waited"
    if adapter == "laya" and fault == "malformed_json":
        return "subprocess.run returns exit 0 and stdout not-json"
    if adapter == "laya" and fault == "schema_invalid":
        return "subprocess.run returns exit 0 and an answer whose option_id is outside the decision"
    if adapter == "laya" and fault == "empty_content":
        return "subprocess.run returns exit 0 and empty stdout"
    if fault == "connection_refused":
        where = "ollama_url" if adapter == "ollama" else "cloud_url"
        return (
            f"TCP connect to a closed ephemeral 127.0.0.1 port via {where}; "
            "no listener and no live model. Cloud loopback skips the HTTPS and remote-confirmation gates"
        )
    if fault == "timeout":
        return "httpx.MockTransport raises httpx.ReadTimeout; Client timeout is hard-coded to 120s and is not waited"
    if fault == "malformed_json":
        if adapter == "ollama":
            return "httpx.MockTransport returns HTTP 200 with body {not-json; the default 127.0.0.1:11434 URL is not dialed"
        return "httpx.MockTransport returns HTTP 200 with body {not-json; example.invalid is not dialed"
    if fault == "schema_invalid":
        return "httpx.MockTransport returns HTTP 200 whose content JSON has option_id not-an-option"
    return "httpx.MockTransport returns HTTP 200 whose message content is an empty string"


def _fault_cell(adapter: str, fault: str) -> dict:
    decision = copy.deepcopy(DECISION)
    before = copy.deepcopy(decision)
    kind, payload, heuristic_spared = _invoke(adapter, fault, decision)
    mutated = decision != before
    human_keys: list[str] = []
    heuristic = False
    auto_true = False
    requires_false = False
    if kind == "raise":
        message = str(payload)
        outcome = f"raise:{type(payload).__name__}"
        cause = type(payload.__cause__).__name__ if payload.__cause__ else None
        if HEURISTIC_SOURCE in message or HEURISTIC_TEXT in message:
            heuristic = True
    else:
        rec = payload.recommendation
        message = ""
        outcome = f"return:{rec.get('source')}"
        cause = None
        human_keys = _find_human_keys(rec)
        heuristic = rec.get("source") == HEURISTIC_SOURCE or HEURISTIC_TEXT in rec.get("rationale", "")
        auto_true = rec.get("auto_eligible") is True
        requires_false = rec.get("requires_human") is not True
    explicit = kind == "return" and isinstance(payload, dict) and payload.get("failure") is True
    outcome_kind = "explicit_failure" if explicit else kind
    invariant_ok = (
        outcome_kind in {"raise", "explicit_failure"}
        and not heuristic
        and heuristic_spared
        and not mutated
        and not human_keys
        and not auto_true
        and not requires_false
    )
    return {
        "adapter": adapter,
        "auto_eligible_true": auto_true,
        "cause_type": cause,
        "decision_mutated": mutated,
        "fault": fault,
        "heuristic_called": not heuristic_spared,
        "heuristic_emitted": heuristic,
        "human_decision_keys": human_keys,
        "injection": _injection(adapter, fault),
        "invariant_ok": invariant_ok,
        "message": message,
        "outcome": outcome,
        "outcome_kind": outcome_kind,
        "requires_human_false": requires_false,
    }


def _hostile_cell(adapter: str) -> dict:
    decision = copy.deepcopy(DECISION)
    kind, payload, heuristic_spared = _invoke_hostile(adapter, decision)
    if kind != "return":
        return {
            "adapter": adapter,
            "auto_eligible": None,
            "injection": "hostile fixture did not return a recommendation",
            "heuristic_called": not heuristic_spared,
            "heuristic_emitted": True,
            "human_decision_keys": [],
            "outcome_kind": kind,
            "requires_human": None,
            "source": "",
            "success_probability": None,
        }
    rec = payload.recommendation
    injection = {
        "ollama": "httpx.MockTransport; source suffix qwen3:8b is the code default, not a contacted model",
        "laya": "subprocess.run patched to return a choice; the checkpoint string is the code default, not a loaded weight",
        "cloud": "httpx.MockTransport; example.invalid is not dialed",
    }[adapter]
    return {
        "adapter": adapter,
        "auto_eligible": rec.get("auto_eligible"),
        "injection": injection,
        "heuristic_called": not heuristic_spared,
        "heuristic_emitted": rec.get("source") == HEURISTIC_SOURCE or HEURISTIC_TEXT in rec.get("rationale", ""),
        "human_decision_keys": _find_human_keys(rec),
        "outcome_kind": "return",
        "requires_human": rec.get("requires_human"),
        "source": rec.get("source"),
        "success_probability": rec.get("success_probability"),
    }


def _invoke_hostile(adapter: str, decision: dict):
    calls = {"n": 0}
    real = CostHeuristicProvider.recommend

    def wrapped(self, *args, **kwargs):
        calls["n"] += 1
        return real(self, *args, **kwargs)

    body = dict(HOSTILE)
    body["option_id"] = "b" if adapter == "cloud" else "a"
    if adapter == "laya":
        extra = patch("qone_agent.runtime.subprocess.run", side_effect=_laya_runner("hostile"))
        config = {}
        kwargs = {}
        transport = None
    else:
        extra = contextlib.nullcontext()
        transport = httpx.MockTransport(lambda request: _chat_response(adapter, body))
        if adapter == "cloud":
            config = CLOUD
            kwargs = {"remote_confirmed": True}
        else:
            config = {}
            kwargs = {}
    with patch.object(CostHeuristicProvider, "recommend", wrapped), extra:
        try:
            result = run_model(decision, adapter, config, transport=transport, **kwargs)
            return "return", result, calls["n"] == 0
        except Exception as exc:
            return "raise", exc, calls["n"] == 0


def _schema_errors(instance, schema, path="$") -> list[str]:
    errors: list[str] = []
    if "const" in schema and "type" not in schema:
        if instance != schema["const"]:
            errors.append(f"{path} const")
        return errors
    expected = schema.get("type")
    if isinstance(expected, list):
        if instance is None and "null" in expected:
            return errors
        non_null = [item for item in expected if item != "null"]
        if len(non_null) != 1:
            return [f"{path} union"]
        expected = non_null[0]
    if expected == "object":
        if not isinstance(instance, dict):
            return [f"{path} type"]
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}.{key} missing")
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}.{key} additional")
        for key, sub in props.items():
            if key in instance:
                errors.extend(_schema_errors(instance[key], sub, f"{path}.{key}"))
        return errors
    if expected == "string":
        if not isinstance(instance, str) or len(instance) < schema.get("minLength", 0):
            errors.append(f"{path} string")
        return errors
    if expected == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            errors.append(f"{path} number")
            return errors
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path} minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path} maximum")
        return errors
    if expected == "array":
        if not isinstance(instance, list):
            return [f"{path} array"]
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                errors.extend(_schema_errors(item, item_schema, f"{path}[{index}]"))
        return errors
    return [f"{path} unsupported schema"]


def _schema_roundtrip() -> dict:
    validator = _load_validator()
    local = json.loads(LOCAL_SCHEMA_PATH.read_text(encoding="utf-8"))
    raw = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    recommendation, _evidence = AgentEngine().recommend(raw)
    engine_dict = recommendation.to_dict()
    option_ids = {item["id"] for item in raw["options"]}
    validator.validate_recommendation(engine_dict, option_ids)
    engine_errors = _schema_errors(engine_dict, local)
    forced = validator.validate_recommendation(
        {
            "option_id": "meeting",
            "confidence": 0.5,
            "success_probability": None,
            "rationale": "x",
            "source": "unit",
            "requires_human": False,
            "auto_eligible": True,
        },
        {"meeting", "draft"},
    )
    decision = copy.deepcopy(DECISION)
    body = {
        "option_id": "a",
        "confidence": 0.7,
        "rationale": "练习可核查，仍需自行确认",
        "auto_eligible": True,
        "requires_human": False,
        "decided_by": "human",
    }
    transport = httpx.MockTransport(lambda request: _chat_response("cloud", body))
    result = run_model(decision, "cloud", CLOUD, remote_confirmed=True, transport=transport)
    validator.validate_recommendation(result.recommendation, {"a", "b"})
    run_errors = _schema_errors(result.recommendation, local)
    missing = [key for key in local["required"] if key not in result.recommendation]
    return {
        "engine_auto_eligible": engine_dict["auto_eligible"],
        "engine_core_validator": "accepted",
        "engine_human_decision_keys": _find_human_keys(engine_dict),
        "engine_local_schema": "accepted" if not engine_errors else "rejected",
        "engine_requires_human": engine_dict["requires_human"],
        "run_model_auto_eligible": result.recommendation["auto_eligible"],
        "run_model_core_validator": "accepted",
        "run_model_human_decision_keys": _find_human_keys(result.recommendation),
        "run_model_injection": "httpx.MockTransport returning a valid cloud JSON object; example.invalid is not dialed",
        "run_model_local_schema": "accepted" if not run_errors else "rejected",
        "run_model_local_schema_errors": run_errors,
        "run_model_missing_local_keys": missing,
        "run_model_requires_human": result.recommendation["requires_human"],
        "vendored_validator_overwrites_flags": forced["requires_human"] is True and forced["auto_eligible"] is False,
    }


def _cli_demo() -> dict:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(["recommend", "--decision-file", str(EXAMPLE_PATH)])
    text = buffer.getvalue()
    payload = json.loads(text)
    recommendation = payload["recommendation"]
    return {
        "auto_eligible": recommendation["auto_eligible"],
        "exit_code": code,
        "human_decision_keys": _find_human_keys(payload),
        "note": "Deterministic CLI demo. Not a model call and not a fallback from run_model.",
        "option_id": recommendation["option_id"],
        "requires_human": recommendation["requires_human"],
        "source": recommendation["source"],
        "stdout": text,
        "success_probability": recommendation["success_probability"],
    }
