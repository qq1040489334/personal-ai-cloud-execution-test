// Deterministic security tests for the EXISTING Deploy & Write Site candidate
// control plane. No network I/O, no production mutation, no secrets.
//
// Run: node --test site/tests/security.mjs

import test from "node:test";
import assert from "node:assert/strict";

import {
  SITE_CANDIDATE_TOOL,
  SITE_CANDIDATE_TOOL_SCHEMA,
  LEGACY_SKILL_TUPLE,
  MCP_EVENTS_TUPLE,
  PROHIBITED_MUTATIONS,
  auditCandidate,
  authorizeRelease,
  createCandidate,
  readCandidate,
  assertNoProhibitedMutation,
} from "../worker/index.js";

const ACTIVE_VERSION = {
  version_id: "3e2fed43",
  bindings: {
    ASSET_DB: "45d6f18a-3a34-4ccd-8337-c00a775cd7a2",
    TASK_REGISTRY: "60f6203f262d44378abd0accfa7fef46",
    GITHUB_REPO: "qq1040489334/personal-ai-cloud-execution-test",
  },
  compatibility_date: "2026-09-23",
  vars: {},
};

const PRODUCTION = {
  deployment_id: "dep-prod-3e2fed43",
  version_id: "3e2fed43",
  traffic_percent: 100,
  deployments: [
    { id: "dep-prod-3e2fed43", version_id: "3e2fed43", percentage: 100 },
  ],
};

function makeMockClient() {
  const calls = [];
  const versions = new Map();
  const state = { production: structuredClone(PRODUCTION) };
  return {
    calls,
    versions,
    state,
    async uploadVersion(payload) {
      calls.push({ name: "uploadVersion", payload });
      const id = `ver-cand-${versions.size + 1}`;
      const record = {
        id,
        etag: `etag-${id}`,
        active: false,
        traffic_percent: 0,
        bindings: { ...payload.bindings },
        compatibility_date: payload.compatibility_date,
        commit: payload.commit,
        worker_sha256: payload.worker_sha256,
      };
      versions.set(id, record);
      return record;
    },
    async getVersion(id) {
      calls.push({ name: "getVersion", id });
      return versions.get(id);
    },
    async readProduction() {
      calls.push({ name: "readProduction" });
      return structuredClone(state.production);
    },
    async createDeployment() {
      calls.push({ name: "createDeployment" });
      throw new Error("createDeployment is prohibited on the candidate path");
    },
    async setTraffic() {
      calls.push({ name: "setTraffic" });
      throw new Error("setTraffic is prohibited on the candidate path");
    },
  };
}

const mcpTupleParams = () => ({
  action: "create",
  commit: MCP_EVENTS_TUPLE.commit,
  worker_sha256: MCP_EVENTS_TUPLE.sha256,
});

test("candidate tool schema exposes audit and create with exact tuple inputs", () => {
  assert.equal(SITE_CANDIDATE_TOOL_SCHEMA.name, SITE_CANDIDATE_TOOL);
  const schema = SITE_CANDIDATE_TOOL_SCHEMA.inputSchema;
  assert.deepEqual(schema.properties.action.enum, ["audit", "create"]);
  assert.deepEqual(schema.required, ["action", "commit", "worker_sha256"]);
  assert.equal(schema.additionalProperties, false);
});

test("owner-approved MCP Events tuple is accepted exactly", () => {
  const decision = authorizeRelease({
    commit: MCP_EVENTS_TUPLE.commit,
    worker_sha256: MCP_EVENTS_TUPLE.sha256,
  });
  assert.equal(decision.authorized, true);
  assert.equal(decision.tuple.label, "mcp-events-golden");
});

test("legacy authorized SKILL commit remains safely supported", () => {
  const decision = authorizeRelease({
    commit: LEGACY_SKILL_TUPLE.commit,
    worker_sha256: LEGACY_SKILL_TUPLE.sha256,
  });
  assert.equal(decision.authorized, true);
  assert.equal(decision.tuple.label, "skill-candidate-writer-legacy");
});

test("wrong commit for the approved hash is rejected", () => {
  const decision = authorizeRelease({
    commit: "a".repeat(40),
    worker_sha256: MCP_EVENTS_TUPLE.sha256,
  });
  assert.equal(decision.authorized, false);
  assert.equal(decision.code, "COMMIT_NOT_ALLOWLISTED");
});

test("wrong hash for the approved commit is rejected", () => {
  const decision = authorizeRelease({
    commit: MCP_EVENTS_TUPLE.commit,
    worker_sha256: "0".repeat(64),
  });
  assert.equal(decision.authorized, false);
  assert.equal(decision.code, "HASH_NOT_ALLOWLISTED");
});

test("malformed commit and hash fail closed", () => {
  assert.equal(
    authorizeRelease({ commit: "not-a-sha", worker_sha256: MCP_EVENTS_TUPLE.sha256 })
      .code,
    "INVALID_COMMIT",
  );
  assert.equal(
    authorizeRelease({ commit: MCP_EVENTS_TUPLE.commit, worker_sha256: "short" })
      .code,
    "INVALID_SHA256",
  );
});

test("audit authorizes without any mutation or upload", async () => {
  const client = makeMockClient();
  const result = auditCandidate(
    { action: "audit", ...mcpTupleParams() },
    { activeVersion: ACTIVE_VERSION },
  );
  assert.equal(result.authorized, true);
  assert.equal(result.mutation, false);
  assert.equal(result.will_create_deployment, false);
  assert.equal(result.will_change_traffic, false);
  assert.equal(client.calls.length, 0);
  assertNoProhibitedMutation(client.calls);
});

test("create rejects arbitrary commit without touching the client", async () => {
  const client = makeMockClient();
  const result = await createCandidate(
    { action: "create", commit: "b".repeat(40), worker_sha256: MCP_EVENTS_TUPLE.sha256 },
    { client, activeVersion: ACTIVE_VERSION },
  );
  assert.equal(result.created, false);
  assert.equal(result.code, "COMMIT_NOT_ALLOWLISTED");
  assert.equal(client.calls.length, 0);
  assert.equal(client.versions.size, 0);
});

test("create uploads a version only and never mutates production", async () => {
  const client = makeMockClient();
  const result = await createCandidate(mcpTupleParams(), {
    client,
    activeVersion: ACTIVE_VERSION,
  });
  assert.equal(result.created, true);
  assert.equal(result.candidate.active, false);
  assert.equal(result.candidate.traffic_percent, 0);
  assert.equal(result.candidate.deployment_created, false);
  assert.equal(result.candidate.traffic_changed, false);
  assert.equal(finalLeaves(client.calls), "uploadVersion");
  assertNoProhibitedMutation(client.calls);
  assert.equal(client.versions.size, 1);
  assert.equal(client.state.production.traffic_percent, 100);
});

test("candidate inherits bindings and config exactly from the active version", async () => {
  const client = makeMockClient();
  const result = await createCandidate(mcpTupleParams(), {
    client,
    activeVersion: ACTIVE_VERSION,
  });
  assert.deepEqual(result.candidate.inherited.bindings, ACTIVE_VERSION.bindings);
  assert.equal(
    result.candidate.inherited.compatibility_date,
    ACTIVE_VERSION.compatibility_date,
  );
  assert.equal(result.candidate.inherited_from_version, ACTIVE_VERSION.version_id);
});

test("candidate read-back is non-active with zero traffic", async () => {
  const client = makeMockClient();
  const created = await createCandidate(mcpTupleParams(), {
    client,
    activeVersion: ACTIVE_VERSION,
  });
  const read = await readCandidate(
    client,
    created.candidate.candidate_version_id,
  );
  assert.equal(read.active, false);
  assert.equal(read.traffic_percent, 0);
  assert.deepEqual(read.bindings, ACTIVE_VERSION.bindings);
});

test("prohibited mutation guard fails closed on deployment or traffic calls", () => {
  const forbidden = (calls) =>
    assert.throws(
      () => assertNoProhibitedMutation(calls),
      (error) => error.code === "PROHIBITED_MUTATION",
    );
  forbidden([{ name: "createDeployment" }]);
  forbidden([{ name: "setTraffic" }]);
  assert.equal(PROHIBITED_MUTATIONS.includes("promoteVersion"), true);
});

function finalLeaves(calls) {
  const names = calls.map((call) => call.name);
  return names[names.length - 1];
}
