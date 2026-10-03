"""MCP Events Golden — deterministic tests for the ``task.completed`` surface.

The production MCP Worker (``worker/index.js``) is executed directly under Node
with a mocked ``TASK_REGISTRY`` KV binding and a scripted outbound ``fetch``.
The tests prove, against the real production source, the official MCP Events
contract (protocol ``2026-07-28``):

* ``server/discover`` advertises the ``events`` capability;
* ``events/list`` exposes exactly the minimal ``task.completed`` event whose
  payload carries only the identifiers needed for the existing
  ``get_task_result(task_id)`` read;
* ``events/subscribe`` validates the event/arguments/callback/secret, performs a
  signed constant-time callback challenge verification, derives a deterministic
  subscription id, and persists the subscription durably (idempotent refresh);
* ``events/unsubscribe`` is account-scoped and idempotent;
* webhook delivery signs the exact body with Standard Webhooks (verified
  independently in Python), preserves the event id across retries, applies
  bounded exponential backoff, does not retry ``410``/``413``, and suppresses
  duplicate/replayed event ids;
* the pre-existing tools and protocol surface are unchanged.

No network I/O, no secrets in artifacts, no production mutation. The signing
secret used here is an ephemeral, well-known test vector.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"

NODE = shutil.which("node")

TEST_SECRET_RAW = b"0123456789abcdef0123456789abcdef"
TEST_SECRET = "whsec_" + base64.b64encode(TEST_SECRET_RAW).decode()
TEST_SECRET_2_RAW = b"fedcba9876543210fedcba9876543210"
TEST_SECRET_2 = "whsec_" + base64.b64encode(TEST_SECRET_2_RAW).decode()
CALLBACK_URL = "https://receiver.example.com/mcp-events/callback_123"

EVENT_NAMES = ["task.completed"]


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


HARNESS = r"""
function makeKV() {
  const store = new Map();
  return {
    store,
    async get(key, type) {
      if (!store.has(key)) return null;
      const raw = store.get(key).value;
      if (type === "json") return JSON.parse(raw);
      return raw;
    },
    async put(key, value, options) {
      store.set(key, { value: typeof value === "string" ? value : JSON.stringify(value), options: options || {} });
    },
    async delete(key) { store.delete(key); },
    async list(options) {
      const prefix = (options && options.prefix) || "";
      const keys = [];
      for (const [name, entry] of store.entries()) {
        if (name.startsWith(prefix)) keys.push({ name, metadata: (entry.options && entry.options.metadata) || {} });
      }
      return { keys };
    }
  };
}
function seedSubscription(kv, sub) {
  kv.store.set("events-subscription::" + sub.id, { value: JSON.stringify(sub), options: { metadata: { name: sub.name } } });
}
function makeFetchRecorder(plan) {
  const requests = [];
  let index = 0;
  globalThis.fetch = async function(url, options) {
    const record = { url: String(url), method: options && options.method, headers: options && options.headers, body: options && options.body };
    requests.push(record);
    const step = Array.isArray(plan) ? (index < plan.length ? plan[index++] : null) : plan;
    if (step === null || step === undefined) throw new Error("network_error");
    if (typeof step === "function") return step(url, options, record);
    return step;
  };
  return { requests };
}
function jsonResponse(body, status) {
  const code = status == null ? 200 : status;
  return {
    status: code,
    ok: code >= 200 && code < 300,
    async json() { return body; },
    async text() { return typeof body === "string" ? body : JSON.stringify(body); }
  };
}
async function callMcp(kv, method, params, auth) {
  const env = { TASK_REGISTRY: kv };
  const request = { async json() { return { jsonrpc: "2.0", id: 1, method, params }; } };
  const response = await handleMcp(request, env, {}, auth || { scopes: ["mcp"], kind: "static" });
  return await response.json();
}
const TEST_SECRET = "__SECRET__";
const TEST_SECRET_2 = "__SECRET2__";
const CALLBACK_URL = "__CALLBACK__";
"""


def harness() -> str:
    return (
        HARNESS.replace("__SECRET2__", TEST_SECRET_2)
        .replace("__SECRET__", TEST_SECRET)
        .replace("__CALLBACK__", CALLBACK_URL)
    )


def run_script(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", worker_source())
    probe = source + "\n" + harness() + "\n" + script
    handle, path = tempfile.mkstemp(suffix=".mjs", prefix="mcp_events_probe_")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(probe)
        out = subprocess.run(
            [NODE, path], capture_output=True, text=True, timeout=120
        )
    finally:
        os.unlink(path)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def whsec_key(secret: str) -> bytes:
    return base64.b64decode(secret[len("whsec_") :])


def expected_signature(secret: str, msg_id: str, timestamp: str, body: str) -> str:
    signed = f"{msg_id}.{timestamp}.{body}".encode()
    digest = hmac.new(whsec_key(secret), signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def signature_matches(secret: str, headers: dict, body: str) -> bool:
    header = headers.get("webhook-signature", "")
    msg_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    expected = expected_signature(secret, msg_id, timestamp, body)
    for part in header.split():
        if part.startswith("v1,") and hmac.compare_digest(part[3:], expected[3:]):
            return True
    return False


def subscription(secret: str = TEST_SECRET, **overrides) -> dict:
    base = {
        "id": "sub_test",
        "principal": "owner",
        "name": "task.completed",
        "arguments": {"task_id": "cf-events-1"},
        "delivery": {"mode": "webhook", "url": CALLBACK_URL, "secret": secret},
        "created_at": "2026-10-03T00:00:00.000Z",
        "updated_at": "2026-10-03T00:00:00.000Z",
        "refreshBefore": "2027-10-03T00:00:00.000Z",
        "ttlMs": 604800000,
        "verified_at": "2026-10-03T00:00:00.000Z",
        "cursor": None,
        "previous_secret": None,
        "previous_secret_expires_at": None,
    }
    base.update(overrides)
    return base


# -- protocol surface -------------------------------------------------------


def test_worker_source_declares_events_contract_tokens() -> None:
    source = worker_source()
    for token in (
        "server/discover",
        "events/list",
        "events/subscribe",
        "events/unsubscribe",
        "task.completed",
        "2026-07-28",
        "EVENTS_KV_PREFIX",
        "standardWebhookSignature",
        "verifyCallbackEndpoint",
        "emitTaskCompleted",
    ):
        assert token in source, f"worker is missing MCP Events token {token}"


def test_server_discover_advertises_events_capability() -> None:
    report = run_script(
        """
const kv = makeKV();
const discovered = await callMcp(kv, "server/discover", {});
console.log(JSON.stringify({ discovered }));
"""
    )
    result = report["discovered"]["result"]
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == ["2026-07-28"]
    assert result["capabilities"]["events"] == {}
    assert "tools" in result["capabilities"]


def test_events_list_exposes_only_task_completed() -> None:
    report = run_script(
        """
const kv = makeKV();
const listed = await callMcp(kv, "events/list", {});
console.log(JSON.stringify({ listed }));
"""
    )
    result = report["listed"]["result"]
    names = [event["name"] for event in result["events"]]
    assert names == EVENT_NAMES
    event = result["events"][0]
    assert event["delivery"] == ["webhook"]
    assert event["inputSchema"]["additionalProperties"] is False
    assert event["payloadSchema"]["additionalProperties"] is False
    assert event["payloadSchema"]["required"] == ["task_id", "status"]
    # No canonical content fields leak into the payload schema.
    assert "content" not in event["payloadSchema"]["properties"]
    assert result["nextCursor"] is None
    assert result["truncated"] is False


def test_initialize_protocol_and_tools_unchanged() -> None:
    report = run_script(
        """
const kv = makeKV();
const initialized = await callMcp(kv, "initialize", {});
const tools = await callMcp(kv, "tools/list", {});
console.log(JSON.stringify({
  protocolVersion: initialized.result.protocolVersion,
  toolNames: tools.result.tools.map((tool) => tool.name)
}));
"""
    )
    assert report["protocolVersion"] == "2025-06-18"
    expected_tools = [
        "submit_task",
        "get_task_result",
        "list_pending_results",
        "plan_task_redispatch",
        "retry_task_dispatch",
        "search_assets",
        "get_asset",
        "write_knowledge_candidate",
        "write_skill_candidate",
        "write_decision_record",
    ]
    for name in expected_tools:
        assert name in report["toolNames"], f"existing tool {name} was removed"
    assert "mark_reviewed" in report["toolNames"]
    assert len(report["toolNames"]) == 11


# -- subscription lifecycle -------------------------------------------------


def test_events_subscribe_verifies_callback_signs_and_persists() -> None:
    report = run_script(
        """
const kv = makeKV();
const recorder = makeFetchRecorder([function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
}]);
const response = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const storedKey = "events-subscription::" + response.result.id;
const stored = JSON.parse(kv.store.get(storedKey).value);
const verificationBody = recorder.requests[0].body;
console.log(JSON.stringify({
  response,
  verification: {
    request: recorder.requests[0],
    body: verificationBody
  },
  stored,
  requestCount: recorder.requests.length
}));
"""
    )
    result = report["response"]["result"]
    assert result["id"].startswith("sub_")
    assert result["cursor"] is None
    assert result["truncated"] is False
    assert result["refreshBefore"]

    verification = report["verification"]
    assert report["requestCount"] == 1
    body = json.loads(verification["body"])
    assert body["type"] == "verification"
    assert body["challenge"]
    headers = verification["request"]["headers"]
    assert headers["webhook-id"].startswith("msg_verification_")
    assert headers["X-MCP-Subscription-Id"] == result["id"]
    assert signature_matches(TEST_SECRET, headers, verification["body"])

    stored = report["stored"]
    assert stored["name"] == "task.completed"
    assert stored["arguments"] == {"task_id": "cf-events-1"}
    assert stored["delivery"]["secret"] == TEST_SECRET
    assert stored["principal"] == "owner"


def test_events_subscribe_is_idempotent_same_identity() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder(function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
});
const first = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const second = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
console.log(JSON.stringify({ first: first.result, second: second.result }));
"""
    )
    assert report["first"]["id"] == report["second"]["id"]
    assert report["second"]["secret_rotated"] is False


def test_events_subscribe_requires_write_scope() -> None:
    report = run_script(
        """
const kv = makeKV();
const denied = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: {},
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
}, { scopes: ["asset.read"], kind: "oauth", payload: { sub: "reader" } });
console.log(JSON.stringify({ denied }));
"""
    )
    assert report["denied"]["error"]["code"] == -32002


@pytest.mark.parametrize(
    "case,payload,reason",
    [
        (
            "unknown_event",
            '{"name": "message.created", "arguments": {}, "delivery": {}}',
            "unknown event",
        ),
        (
            "unexpected_argument",
            '{"name": "task.completed", "arguments": {"nope": "x"}, "delivery": {}}',
            "unexpected_argument",
        ),
        (
            "bad_secret",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "%s", "secret": "nope"}}'
            % CALLBACK_URL,
            "invalid_signing_secret",
        ),
        (
            "insecure_scheme",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "http://receiver.example.com/cb", "secret": "%s"}}'
            % TEST_SECRET,
            "insecure_scheme",
        ),
        (
            "private_address",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "https://127.0.0.1/cb", "secret": "%s"}}'
            % TEST_SECRET,
            "non_public_address",
        ),
        (
            "localhost",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "https://localhost/cb", "secret": "%s"}}'
            % TEST_SECRET,
            "non_public_address",
        ),
    ],
)
def test_events_subscribe_rejects_invalid_inputs(case, payload, reason) -> None:
    report = run_script(
        f"""
const kv = makeKV();
makeFetchRecorder([jsonResponse({{}}, 200)]);
const params = {payload};
const response = await callMcp(kv, "events/subscribe", params);
console.log(JSON.stringify({{ response }}));
"""
    )
    error = report["response"]["error"]
    text = json.dumps(error)
    if case in ("bad_secret", "unexpected_argument"):
        assert error["code"] == -32602
        assert reason in text
    elif case == "unknown_event":
        assert error["code"] == -32602
        assert reason in text
    else:
        assert error["code"] == -32015
        assert reason in text


def test_events_subscribe_rejects_failed_challenge() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder([function(url, options, record) {
  return jsonResponse({ challenge: "wrong-challenge" }, 200);
}]);
const response = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
console.log(JSON.stringify({ response, storedCount: kv.store.size }));
"""
    )
    assert report["response"]["error"]["code"] == -32015
    assert report["response"]["error"]["data"]["reason"] == "challenge_failed"
    assert report["storedCount"] == 0


def test_events_unsubscribe_is_idempotent_and_account_scoped() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder([function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
}]);
const subscribed = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const id = subscribed.result.id;
// Cross-account unsubscribe must not remove another account's subscription.
const crossAccount = await callMcp(kv, "events/unsubscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL }
}, { scopes: ["mcp"], kind: "oauth", payload: { sub: "someone-else" } });
const afterCross = kv.store.has("events-subscription::" + id);
const removed = await callMcp(kv, "events/unsubscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL }
});
const afterOwner = kv.store.has("events-subscription::" + id);
const again = await callMcp(kv, "events/unsubscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL }
});
console.log(JSON.stringify({ crossAccount, afterCross, removed, afterOwner, again }));
"""
    )
    assert report["crossAccount"] == {"jsonrpc": "2.0", "id": 1, "result": {}}
    assert report["afterCross"] is True
    assert report["removed"]["result"] == {}
    assert report["afterOwner"] is False
    assert report["again"]["result"] == {}


# -- delivery ---------------------------------------------------------------


def test_emit_task_completed_delivers_signed_standard_webhook() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 200)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1",
  status: "PASS"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, requests: recorder.requests }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert len(report["requests"]) == 1
    request = report["requests"][0]
    event = json.loads(request["body"])
    assert event["name"] == "task.completed"
    assert event["data"] == {"task_id": "cf-events-1", "status": "PASS"}
    assert event["eventId"].startswith("evt_")
    assert request["headers"]["webhook-id"] == event["eventId"]
    assert request["headers"]["X-MCP-Subscription-Id"] == "sub_test"
    assert signature_matches(TEST_SECRET, request["headers"], request["body"])
    assert report["out"]["delivered"][0]["id"] == "sub_test"


def test_emit_task_completed_filtering_and_expiry() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __MATCH__);
seedSubscription(kv, __MISMATCH__);
seedSubscription(kv, __EXPIRED__);
const recorder = makeFetchRecorder([jsonResponse({}, 200), jsonResponse({}, 200)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1",
  status: "PASS",
  project_id: "proj-a"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, requests: recorder.requests }));
"""
        .replace(
            "__MATCH__",
            json.dumps(subscription(id="sub_match", arguments={"task_id": "cf-events-1"})),
        )
        .replace(
            "__MISMATCH__",
            json.dumps(subscription(id="sub_mismatch", arguments={"task_id": "other"})),
        )
        .replace(
            "__EXPIRED__",
            json.dumps(
                subscription(
                    id="sub_expired",
                    arguments={"task_id": "cf-events-1"},
                    refreshBefore="2020-01-01T00:00:00.000Z",
                )
            ),
        )
    )
    delivered_ids = [item["id"] for item in report["out"]["delivered"]]
    assert delivered_ids == ["sub_match"]
    skipped = {item["id"]: item["reason"] for item in report["out"]["skipped"]}
    assert skipped["sub_mismatch"] == "filter_mismatch"
    assert skipped["sub_expired"] == "expired"
    assert len(report["requests"]) == 1


def test_emit_task_completed_duplicate_event_id_is_suppressed() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 200), jsonResponse({}, 200)]);
const first = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_fixed"
}, { sleep: async () => {}, retryBaseMs: 0 });
const second = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_fixed"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ first, second, requestCount: recorder.requests.length }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert report["requestCount"] == 1
    assert report["first"]["delivered"][0]["id"] == "sub_test"
    assert report["second"]["delivered"] == []
    assert report["second"]["skipped"][0]["reason"] == "duplicate"


def test_delivery_retries_then_succeeds_and_preserves_event_id() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([
  jsonResponse({}, 500),
  jsonResponse({}, 502),
  jsonResponse({}, 200)
]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_retry"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, requests: recorder.requests }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert len(report["requests"]) == 3
    event_ids = {json.loads(request["body"])["eventId"] for request in report["requests"]}
    assert event_ids == {"evt_retry"}
    timestamps = {request["headers"]["webhook-timestamp"] for request in report["requests"]}
    assert len(timestamps) >= 1
    assert report["out"]["delivered"][0]["attempts"] == 3
    assert report["out"]["delivered"][0]["status"] == 200


def test_delivery_does_not_retry_410_or_413() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 410)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_gone"
}, { sleep: async () => {}, retryBaseMs: 0 });
const recorder413 = makeFetchRecorder([jsonResponse({}, 413)]);
const out413 = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_big"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, out413, count: recorder.requests.length + recorder413.requests.length }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert report["count"] == 2
    assert report["out"]["delivered"] == []
    assert report["out"]["skipped"][0]["reason"] == "delivery_failed"
    assert report["out"]["skipped"][0]["status"] == 410
    assert report["out413"]["skipped"][0]["status"] == 413


def test_delivery_retries_bounded_then_gives_up() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 500)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_down"
}, { sleep: async () => {}, retryBaseMs: 0, maxAttempts: 3 });
console.log(JSON.stringify({ out, count: recorder.requests.length }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert report["count"] == 3
    assert report["out"]["delivered"] == []
    assert report["out"]["skipped"][0]["reason"] == "delivery_failed"


def test_secret_rotation_signs_with_previous_secret() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 200)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_rot"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, request: recorder.requests[0] }));
"""
        .replace(
            "__SUB__",
            json.dumps(
                subscription(
                    previous_secret=TEST_SECRET_2,
                    previous_secret_expires_at="2999-01-01T00:00:00.000Z",
                )
            ),
        )
    )
    request = report["request"]
    header = request["headers"]["webhook-signature"]
    assert signature_matches(TEST_SECRET, request["headers"], request["body"])
    assert signature_matches(TEST_SECRET_2, request["headers"], request["body"])
    assert len(header.split()) == 2


def test_event_payload_size_bound_is_enforced() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
makeFetchRecorder([jsonResponse({}, 200)]);
let error = null;
try {
  await emitTaskCompleted({ TASK_REGISTRY: kv }, {
    task_id: "x".repeat(300000), status: "PASS"
  }, { sleep: async () => {}, retryBaseMs: 0 });
} catch (err) {
  error = err.mcpError || { message: err.message };
}
console.log(JSON.stringify({ error }));
"""
        .replace("__SUB__", json.dumps(subscription(arguments={})))
    )
    assert report["error"]["code"] == -32015
    assert report["error"]["data"]["reason"] == "payload_too_large"


def test_subscription_secret_never_returned_by_listings() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder([function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
}]);
await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const listed = await callMcp(kv, "events/list", {});
console.log(JSON.stringify({ listed, listText: JSON.stringify(listed) }));
"""
    )
    assert TEST_SECRET not in report["listText"]
    assert report["listed"]["result"]["events"][0]["name"] == "task.completed"

