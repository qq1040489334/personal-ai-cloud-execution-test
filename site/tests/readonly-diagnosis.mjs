// Read-only diagnosis for the EXISTING Deploy & Write Site candidate control
// plane. Proves: one non-active candidate is created and read back with zero
// traffic, and production deployment/version/traffic are identical before and
// after. No network I/O, no production mutation, no secrets.
//
// Run: node --test site/tests/readonly-diagnosis.mjs

import test from "node:test";
import assert from "node:assert/strict";

import {
  LEGACY_SKILL_TUPLE,
  MCP_EVENTS_TUPLE,
  PRODUCTION_ACCOUNT_ID,
  PRODUCTION_SERVICE,
  auditCandidate,
  createCandidate,
  readCandidate,
  readProduction,
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
  };
}

test("production deployment/version/traffic identical before and after create", async () => {
  const client = makeMockClient();
  const before = await readProduction(client);

  const result = await createCandidate(
    {
      action: "create",
      commit: MCP_EVENTS_TUPLE.commit,
      worker_sha256: MCP_EVENTS_TUPLE.sha256,
    },
    { client, activeVersion: ACTIVE_VERSION },
  );

  const after = await readProduction(client);
  assert.deepEqual(after, before);
  assert.equal(result.candidate.active, false);
  assert.equal(result.candidate.traffic_percent, 0);
});

test("exactly one non-active candidate is created for the approved tuple", async () => {
  const client = makeMockClient();
  const result = await createCandidate(
    {
      action: "create",
      commit: MCP_EVENTS_TUPLE.commit,
      worker_sha256: MCP_EVENTS_TUPLE.sha256,
    },
    { client, activeVersion: ACTIVE_VERSION },
  );

  assert.equal(result.created, true);
  assert.equal(client.versions.size, 1);

  const uploaded = client.calls.filter((call) => call.name === "uploadVersion");
  assert.equal(uploaded.length, 1);
  assert.equal(uploaded[0].payload.worker, PRODUCTION_SERVICE);
  assert.equal(uploaded[0].payload.account_id, PRODUCTION_ACCOUNT_ID);
  assert.equal(uploaded[0].payload.non_active, true);
  assert.equal(uploaded[0].payload.commit, MCP_EVENTS_TUPLE.commit);
  assert.equal(uploaded[0].payload.worker_sha256, MCP_EVENTS_TUPLE.sha256);
});

test("candidate read-back has zero traffic and is absent from production", async () => {
  const client = makeMockClient();
  const result = await createCandidate(
    {
      action: "create",
      commit: MCP_EVENTS_TUPLE.commit,
      worker_sha256: MCP_EVENTS_TUPLE.sha256,
    },
    { client, activeVersion: ACTIVE_VERSION },
  );

  const candidate = await readCandidate(
    client,
    result.candidate.candidate_version_id,
  );
  assert.equal(candidate.active, false);
  assert.equal(candidate.traffic_percent, 0);
  assert.equal(candidate.candidate_version_id, result.candidate.candidate_version_id);

  const production = await readProduction(client);
  const liveVersionIds = production.deployments.map((dep) => dep.version_id);
  assert.equal(liveVersionIds.includes(candidate.candidate_version_id), false);
});

test("audit path performs no mutation and leaves production untouched", async () => {
  const client = makeMockClient();
  const before = await readProduction(client);

  for (const tuple of [MCP_EVENTS_TUPLE, LEGACY_SKILL_TUPLE]) {
    const audit = auditCandidate(
      { action: "audit", commit: tuple.commit, worker_sha256: tuple.sha256 },
      { activeVersion: ACTIVE_VERSION },
    );
    assert.equal(audit.authorized, true);
    assert.equal(audit.mutation, false);
  }

  const after = await readProduction(client);
  assert.deepEqual(after, before);
  assert.equal(client.versions.size, 0);
  assertNoProhibitedMutation(client.calls);
});

test("candidate creation records no prohibited mutation", async () => {
  const client = makeMockClient();
  await createCandidate(
    {
      action: "create",
      commit: MCP_EVENTS_TUPLE.commit,
      worker_sha256: MCP_EVENTS_TUPLE.sha256,
    },
    { client, activeVersion: ACTIVE_VERSION },
  );
  assert.doesNotThrow(() => assertNoProhibitedMutation(client.calls));
  const mutated = client.calls
    .map((call) => call.name)
    .filter((name) => ["createDeployment", "setTraffic", "promoteVersion"].includes(name));
  assert.deepEqual(mutated, []);
});
