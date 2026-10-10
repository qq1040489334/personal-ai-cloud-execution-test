// PERSONAL_AI_DEPLOY_WRITE_SITE_CANDIDATE_CONTROL_PLANE_V0.1
//
// This module extends the EXISTING Personal AI Deploy & Write Site candidate
// creation path. It does not create a second Site, Worker, state store, router
// or deploy service. It is a fail-closed, deterministic gate that:
//
//   * authorizes candidate creation for an EXACT (commit, sha256) release tuple
//     only -- arbitrary commits/hashes are rejected;
//   * preserves strict inheritance from the current active Worker version;
//   * uploads a non-active version only and NEVER creates a deployment and
//     NEVER changes traffic;
//   * exposes an AUDIT action that makes no mutation at all.
//
// Publishing the Site control-plane change (this file) is explicitly approved.
// Production deployment/promotion remains behind the production deployment
// Human Gate.

export const SITE_NAME = "personal-ai-deploy-write-site";
// Server-owned mounting seam for the existing /knowledge Human Gate. No live
// route is enabled until deployed-source reconciliation supplies its verifier.
export { createKnowledgeApprovalRoute } from "./knowledge-approval.js";
export const CONTROL_PLANE = "existing-deploy-and-write-site";
export const SITE_CANDIDATE_CONTRACT =
  "PERSONAL_AI_DEPLOY_WRITE_SITE_CANDIDATE_CONTROL_PLANE_V0.1";
export const SITE_CANDIDATE_TOOL = "site_worker_candidate";

export const PRODUCTION_SERVICE = "personal-ai-execution-mcp";
export const PRODUCTION_ACCOUNT_ID = "78a22a0699aa94a39d8f7bfdbac18249";

// Exact allowlisted release tuples. Both tuples are exact (commit AND hash).
// The legacy SKILL tuple remains safely supported; the MCP Events Golden tuple
// is the narrowly owner-approved addition.
export const AUTHORIZED_RELEASE_TUPLES = Object.freeze([
  Object.freeze({
    label: "skill-candidate-writer-legacy",
    commit: "0ab0a3e4e6539fb0d99173e10dbb1351730058e0",
    sha256:
      "2559370db404e837a0bf0185f3194146c49697e465156581e7480237a41cac22",
    worker: PRODUCTION_SERVICE,
  }),
  Object.freeze({
    label: "mcp-events-golden",
    commit: "75af42b59e34e11195421f049bcfabcf86107301",
    sha256:
      "babe8187e7c58c1e388b6fbafed9fb46da956d496c73d9da4c40ef8cc41396de",
    worker: PRODUCTION_SERVICE,
  }),
]);

export const LEGACY_SKILL_TUPLE = AUTHORIZED_RELEASE_TUPLES[0];
export const MCP_EVENTS_TUPLE = AUTHORIZED_RELEASE_TUPLES[1];

export const CANDIDATE_ACTIONS = Object.freeze(["audit", "create"]);

// MCP tools/list schema for the refreshed EXISTING Site candidate tool.
export const SITE_CANDIDATE_TOOL_SCHEMA = Object.freeze({
  name: SITE_CANDIDATE_TOOL,
  description:
    "AUDIT or CREATE exactly one non-active Worker candidate for an exact " +
    "allowlisted (commit, sha256) release tuple in the existing Deploy & Write " +
    "Site. Uploads a version only; never creates a deployment and never changes " +
    "traffic. Production promotion stays behind the Human Gate.",
  inputSchema: {
    type: "object",
    properties: {
      action: { type: "string", enum: [...CANDIDATE_ACTIONS] },
      commit: { type: "string", pattern: "^[0-9a-f]{40}$" },
      worker_sha256: { type: "string", pattern: "^[0-9a-f]{64}$" },
    },
    required: ["action", "commit", "worker_sha256"],
    additionalProperties: false,
  },
});

// Calls that would mutate production state and are prohibited on this path.
export const PROHIBITED_MUTATIONS = Object.freeze([
  "createDeployment",
  "setTraffic",
  "promoteVersion",
  "deleteWorker",
  "updateBindings",
  "updateSecrets",
  "updateOAuth",
  "updateSchema",
]);

export class CandidateControlPlaneError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "CandidateControlPlaneError";
    this.code = code;
  }
}

const HEX40 = /^[0-9a-f]{40}$/;
const HEX64 = /^[0-9a-f]{64}$/;

export function normalizeCommit(value) {
  if (typeof value !== "string") return "";
  return value.trim().toLowerCase();
}

export function normalizeSha256(value) {
  if (typeof value !== "string") return "";
  return value.trim().toLowerCase().replace(/^sha256:/, "");
}

export function findAuthorizedTuple(commit, workerSha256) {
  const normalizedCommit = normalizeCommit(commit);
  const normalizedHash = normalizeSha256(workerSha256);
  return (
    AUTHORIZED_RELEASE_TUPLES.find(
      (tuple) =>
        tuple.commit === normalizedCommit && tuple.sha256 === normalizedHash,
    ) || null
  );
}

// Exact commit+hash authorization. Distinguishes malformed input from a
// well-formed but unauthorized commit/hash so callers fail closed precisely.
export function authorizeRelease({ commit, worker_sha256: workerSha256 } = {}) {
  const normalizedCommit = normalizeCommit(commit);
  const normalizedHash = normalizeSha256(workerSha256);
  if (!HEX40.test(normalizedCommit)) {
    return {
      authorized: false,
      code: "INVALID_COMMIT",
      reason: "commit must be a 40-character lowercase hex sha",
    };
  }
  if (!HEX64.test(normalizedHash)) {
    return {
      authorized: false,
      code: "INVALID_SHA256",
      reason: "worker_sha256 must be a 64-character lowercase hex sha256",
    };
  }
  const byCommit = AUTHORIZED_RELEASE_TUPLES.find(
    (tuple) => tuple.commit === normalizedCommit,
  );
  if (!byCommit) {
    return {
      authorized: false,
      code: "COMMIT_NOT_ALLOWLISTED",
      reason: "commit is not an allowlisted release tuple",
    };
  }
  if (byCommit.sha256 !== normalizedHash) {
    return {
      authorized: false,
      code: "HASH_NOT_ALLOWLISTED",
      reason: "worker_sha256 does not match the allowlisted tuple for commit",
    };
  }
  return { authorized: true, tuple: byCommit };
}

function requireAction(params) {
  if (!params || typeof params !== "object") {
    throw new CandidateControlPlaneError(
      "INVALID_PARAMS",
      "params must be an object",
    );
  }
  if (!CANDIDATE_ACTIONS.includes(params.action)) {
    throw new CandidateControlPlaneError(
      "INVALID_ACTION",
      `action must be one of ${CANDIDATE_ACTIONS.join(", ")}`,
    );
  }
}

function requireActiveVersion(activeVersion) {
  if (
    !activeVersion ||
    typeof activeVersion !== "object" ||
    !activeVersion.version_id
  ) {
    throw new CandidateControlPlaneError(
      "ACTIVE_VERSION_UNAVAILABLE",
      "current active Worker version is required for strict inheritance",
    );
  }
}

export function inheritedConfig(activeVersion) {
  requireActiveVersion(activeVersion);
  return {
    bindings: { ...(activeVersion.bindings || {}) },
    compatibility_date: activeVersion.compatibility_date,
    vars: { ...(activeVersion.vars || {}) },
  };
}

// AUDIT is strictly read-only: it authorizes and reports intent without any
// mutation, upload, deployment or traffic change.
export function auditCandidate(params, { activeVersion } = {}) {
  requireAction(params);
  const decision = authorizeRelease(params);
  if (!decision.authorized) {
    return {
      action: "audit",
      authorized: false,
      code: decision.code,
      reason: decision.reason,
      mutation: false,
    };
  }
  const config = inheritedConfig(activeVersion);
  return {
    action: "audit",
    authorized: true,
    mutation: false,
    label: decision.tuple.label,
    commit: decision.tuple.commit,
    worker_sha256: decision.tuple.sha256,
    worker: decision.tuple.worker,
    inherited_from_version: activeVersion.version_id,
    inherited: config,
    will_upload_version_only: true,
    will_create_deployment: false,
    will_change_traffic: false,
  };
}

function requireClient(client) {
  if (!client || typeof client.uploadVersion !== "function") {
    throw new CandidateControlPlaneError(
      "CANDIDATE_CLIENT_UNAVAILABLE",
      "an existing candidate client with uploadVersion is required",
    );
  }
}

// CREATE authorizes the exact tuple, inherits strictly from the active version,
// and uploads exactly one non-active version. It never creates a deployment and
// never changes traffic.
export async function createCandidate(
  params,
  { client, activeVersion, now = () => new Date().toISOString() } = {},
) {
  requireAction(params);
  const decision = authorizeRelease(params);
  if (!decision.authorized) {
    return {
      action: "create",
      created: false,
      candidate: null,
      code: decision.code,
      reason: decision.reason,
      mutation: false,
    };
  }
  requireClient(client);
  const config = inheritedConfig(activeVersion);

  const uploaded = await client.uploadVersion({
    account_id: PRODUCTION_ACCOUNT_ID,
    worker: decision.tuple.worker,
    commit: decision.tuple.commit,
    worker_sha256: decision.tuple.sha256,
    bindings: config.bindings,
    compatibility_date: config.compatibility_date,
    vars: config.vars,
    non_active: true,
  });

  return {
    action: "create",
    created: true,
    mutation: true,
    code: "CANDIDATE_CREATED",
    candidate: {
      label: decision.tuple.label,
      commit: decision.tuple.commit,
      worker_sha256: decision.tuple.sha256,
      worker: decision.tuple.worker,
      candidate_version_id: uploaded.id,
      etag: uploaded.etag ?? null,
      active: false,
      traffic_percent: 0,
      deployment_created: false,
      traffic_changed: false,
      inherited_from_version: activeVersion.version_id,
      inherited: config,
      created_at: now(),
    },
  };
}

export async function readCandidate(client, versionId) {
  requireClient(client);
  if (typeof client.getVersion !== "function") {
    throw new CandidateControlPlaneError(
      "CANDIDATE_CLIENT_UNAVAILABLE",
      "candidate client must expose getVersion for read-back",
    );
  }
  const record = await client.getVersion(versionId);
  return {
    candidate_version_id: record.id,
    etag: record.etag ?? null,
    active: record.active === true,
    traffic_percent: Number(record.traffic_percent ?? 0),
    bindings: { ...(record.bindings || {}) },
    compatibility_date: record.compatibility_date,
  };
}

export async function readProduction(client) {
  if (!client || typeof client.readProduction !== "function") {
    throw new CandidateControlPlaneError(
      "PRODUCTION_READ_UNAVAILABLE",
      "production read-back client is required",
    );
  }
  const state = await client.readProduction();
  return {
    deployment_id: state.deployment_id,
    version_id: state.version_id,
    traffic_percent: state.traffic_percent,
    deployments: state.deployments ?? null,
  };
}

// Fail-closed assertion helper: any prohibited mutation recorded by a client is
// surfaced so a caller can abort before treating the run as clean.
export function assertNoProhibitedMutation(calls = []) {
  const names = calls.map((call) => call && call.name).filter(Boolean);
  const prohibited = names.filter((name) =>
    PROHIBITED_MUTATIONS.includes(name),
  );
  if (prohibited.length > 0) {
    throw new CandidateControlPlaneError(
      "PROHIBITED_MUTATION",
      `prohibited mutation(s) observed: ${prohibited.join(", ")}`,
    );
  }
  return true;
}

export default {
  SITE_NAME,
  CONTROL_PLANE,
  SITE_CANDIDATE_CONTRACT,
  SITE_CANDIDATE_TOOL,
  SITE_CANDIDATE_TOOL_SCHEMA,
  AUTHORIZED_RELEASE_TUPLES,
  LEGACY_SKILL_TUPLE,
  MCP_EVENTS_TUPLE,
  PROHIBITED_MUTATIONS,
  normalizeCommit,
  normalizeSha256,
  findAuthorizedTuple,
  authorizeRelease,
  inheritedConfig,
  auditCandidate,
  createCandidate,
  readCandidate,
  readProduction,
  assertNoProhibitedMutation,
};
