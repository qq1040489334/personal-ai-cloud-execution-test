// dispatch/production-knowledge-minimal-package-20261020/shared/knowledge-contract.mjs
var POLICY = "KNOWLEDGE_PROD_V02_COUNTER_V1";
var RP = "personal-ai-deploy-write-probe.tangyuandousha1010.chatgpt.site";
var SEED_EVIDENCE = "2e0db873fb4b983fab5dc8fbd7ac9b3ed3dfd8f1d6a4143d30d6aba544782171";
var hash = async (s) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s))), (b) => b.toString(16).padStart(2, "0")).join("");
var fail = (code) => {
  throw Error(code);
};
function exactTarget(p) {
  if (!/^knowledge[:-][a-zA-Z0-9:_-]+$/.test(p?.asset_id ?? "")) fail("KNOWLEDGE_ASSET_NAMESPACE_REQUIRED");
  if (p?.production_contract !== POLICY || p.operation !== "KNOWLEDGE_PROMOTION" || typeof p.candidate_id !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9:_-]{0,127}$/.test(p.candidate_id) || !Number.isSafeInteger(p.candidate_version) || p.candidate_version < 1 || !/^[a-f0-9]{64}$/.test(p.content_hash) || typeof p.asset_id !== "string" || !p.asset_id || p.review_result !== "PASS" || !p.reviewed_at || !/^[a-f0-9]{64}$/.test(p.review_evidence_sha256) || !(p.expected_asset_version === null || typeof p.expected_asset_version === "string" && p.expected_asset_version.length > 0)) fail("EXACT_REVIEWED_CANDIDATE_REQUIRED");
  return JSON.stringify({ operation: "KNOWLEDGE_PROMOTION", production_contract: POLICY, candidate_id: p.candidate_id, candidate_version: p.candidate_version, content_hash: p.content_hash, asset_id: p.asset_id, review_result: "PASS", reviewed_at: p.reviewed_at, review_evidence_sha256: p.review_evidence_sha256, expected_asset_version: p.expected_asset_version });
}
function candidatePayload(k) {
  return { operation: "KNOWLEDGE_PROMOTION", production_contract: POLICY, candidate_id: k.candidate_id, candidate_version: k.version, content_hash: k.content_hash, asset_id: k.asset_id, review_result: k.review_result, reviewed_at: k.reviewed_at, review_evidence_sha256: k.review_evidence_sha256, expected_asset_version: k.expected_asset_version };
}
function checkedProvenance(raw) {
  const p = typeof raw === "string" ? JSON.parse(raw) : raw;
  const required = [p?.source?.identity, p?.source?.location, p?.source_version, p?.content_version, p?.captured_at];
  if (required.some((x2) => typeof x2 !== "string" || !x2.trim()) || !Number.isFinite(Date.parse(p.captured_at))) fail("REVIEWED_SOURCE_EVIDENCE_REQUIRED");
  return p;
}
function sqlTokens(s) {
  let out = "", q = null;
  for (let i2 = 0; i2 < s.length; i2++) {
    const c = s[i2];
    if (q) {
      out += c;
      if (c === q) {
        if (s[i2 + 1] === q) out += s[++i2];
        else q = null;
      }
    } else if (c === "'" || c === '"' || c === "`") {
      q = c;
      out += c;
    } else if (!/\s/.test(c)) out += c;
  }
  return out;
}
async function checkedSchema(db, snapshot) {
  const q = await db.prepare("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name IN ('assets','asset_versions','asset_audit','approval_ledger_operations','personal_ai_approval_ledger','personal_ai_approval_ledger__project_status_backup','knowledge_candidates','approval_credential_counters_v1','approval_assertion_commits_v1') ORDER BY type,name").all();
  const rows = q.results;
  if (!Array.isArray(rows) || rows.length !== snapshot.length || !snapshot.every((e) => rows.some((r) => r.type === e.type && r.name === e.name && r.tbl_name === e.tbl_name && (e.sql === null ? r.sql === null : sqlTokens(e.sql) === sqlTokens(r.sql))))) fail("PRODUCTION_SCHEMA_DRIFT");
  const registry = (await db.prepare("SELECT * FROM approval_ledger_operations ORDER BY operation").all()).results;
  if (registry.length !== 6 || !registry.some((r) => r.operation === "KNOWLEDGE_PROMOTION" && r.asset_type === "KNOWLEDGE" && r.canonical_writer === "writeKnowledgeCandidate" && r.single_use === 1 && r.replay_guard === 1)) fail("PRODUCTION_REGISTRY_DRIFT");
}

// dispatch/production-knowledge-minimal-package-20261020/shared/schema-snapshot.mjs
var SNAPSHOT = [
  {
    "type": "index",
    "name": "idx_approval_ledger_binding",
    "tbl_name": "personal_ai_approval_ledger",
    "sql": "CREATE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,content_hash)"
  },
  {
    "type": "index",
    "name": "idx_approval_ledger_state",
    "tbl_name": "personal_ai_approval_ledger",
    "sql": "CREATE INDEX idx_approval_ledger_state ON personal_ai_approval_ledger(operation,consumed,invalidated)"
  },
  {
    "type": "index",
    "name": "idx_asset_audit_asset_time",
    "tbl_name": "asset_audit",
    "sql": "CREATE INDEX idx_asset_audit_asset_time ON asset_audit(asset_id,timestamp)"
  },
  {
    "type": "index",
    "name": "idx_assets_type_status_title",
    "tbl_name": "assets",
    "sql": "CREATE INDEX idx_assets_type_status_title ON assets(asset_type,status,title)"
  },
  {
    "type": "index",
    "name": "idx_knowledge_candidates_asset",
    "tbl_name": "knowledge_candidates",
    "sql": "CREATE INDEX idx_knowledge_candidates_asset ON knowledge_candidates(asset_id)"
  },
  {
    "type": "index",
    "name": "idx_knowledge_candidates_status",
    "tbl_name": "knowledge_candidates",
    "sql": "CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(status)"
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_approval_assertion_commits_v1_1",
    "tbl_name": "approval_assertion_commits_v1",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_approval_assertion_commits_v1_2",
    "tbl_name": "approval_assertion_commits_v1",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_approval_assertion_commits_v1_3",
    "tbl_name": "approval_assertion_commits_v1",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_approval_credential_counters_v1_1",
    "tbl_name": "approval_credential_counters_v1",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_approval_ledger_operations_1",
    "tbl_name": "approval_ledger_operations",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_asset_audit_1",
    "tbl_name": "asset_audit",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_asset_versions_1",
    "tbl_name": "asset_versions",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_assets_1",
    "tbl_name": "assets",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_knowledge_candidates_1",
    "tbl_name": "knowledge_candidates",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_personal_ai_approval_ledger_1",
    "tbl_name": "personal_ai_approval_ledger",
    "sql": null
  },
  {
    "type": "index",
    "name": "sqlite_autoindex_personal_ai_approval_ledger__project_status_backup_1",
    "tbl_name": "personal_ai_approval_ledger__project_status_backup",
    "sql": null
  },
  {
    "type": "table",
    "name": "approval_assertion_commits_v1",
    "tbl_name": "approval_assertion_commits_v1",
    "sql": "CREATE TABLE approval_assertion_commits_v1 (\n ceremony_id TEXT PRIMARY KEY NOT NULL CHECK(length(ceremony_id)=43),\n challenge_id TEXT UNIQUE NOT NULL,\n approval_id TEXT UNIQUE NOT NULL,\n owner_hash TEXT NOT NULL,\n rp_id TEXT NOT NULL,\n signer_identity TEXT NOT NULL,\n enrollment_epoch TEXT NOT NULL,\n expected_revision INTEGER NOT NULL,\n expected_mode TEXT NOT NULL CHECK(expected_mode='MONOTONIC'),\n expected_count INTEGER NOT NULL,\n sign_count INTEGER NOT NULL,\n exact_target TEXT NOT NULL CHECK(json_valid(exact_target)),\n payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),\n issued_at_ms INTEGER NOT NULL,\n expires_at_ms INTEGER NOT NULL,\n accepted_at_ms INTEGER NOT NULL,\n CHECK(expires_at_ms-issued_at_ms=300000),\n CHECK(approval_id='knowledge:'||ceremony_id),\n CHECK(substr(challenge_id,1,48)='PAI:'||ceremony_id||':')\n) STRICT"
  },
  {
    "type": "table",
    "name": "approval_credential_counters_v1",
    "tbl_name": "approval_credential_counters_v1",
    "sql": "CREATE TABLE approval_credential_counters_v1 (\n owner_hash TEXT NOT NULL CHECK(length(owner_hash)=64),\n rp_id TEXT NOT NULL,\n signer_identity TEXT NOT NULL CHECK(length(signer_identity)=73),\n enrollment_epoch TEXT NOT NULL,\n state TEXT NOT NULL CHECK(state IN ('ACTIVE','REVOKED')),\n mode TEXT NOT NULL CHECK(mode='MONOTONIC'),\n last_count INTEGER NOT NULL CHECK(last_count>=2 AND last_count<=4294967295),\n revision INTEGER NOT NULL CHECK(revision>=1),\n enrolled_at_ms INTEGER NOT NULL,\n updated_at_ms INTEGER NOT NULL,\n bootstrap_evidence_sha256 TEXT NOT NULL,\n PRIMARY KEY(owner_hash,rp_id,signer_identity)\n) STRICT"
  },
  {
    "type": "table",
    "name": "approval_ledger_operations",
    "tbl_name": "approval_ledger_operations",
    "sql": "CREATE TABLE approval_ledger_operations(operation TEXT PRIMARY KEY,asset_type TEXT NOT NULL,canonical_writer TEXT NOT NULL,single_use INTEGER NOT NULL DEFAULT 1,replay_guard INTEGER NOT NULL DEFAULT 1)"
  },
  {
    "type": "table",
    "name": "asset_audit",
    "tbl_name": "asset_audit",
    "sql": "CREATE TABLE asset_audit (\n  event_id TEXT PRIMARY KEY,\n  asset_id TEXT NOT NULL,\n  action TEXT NOT NULL,\n  version TEXT NOT NULL,\n  timestamp TEXT NOT NULL,\n  actor TEXT NOT NULL,\n  metadata TEXT NOT NULL,\n  FOREIGN KEY (asset_id,version) REFERENCES asset_versions(asset_id,version) ON DELETE RESTRICT\n)"
  },
  {
    "type": "table",
    "name": "asset_versions",
    "tbl_name": "asset_versions",
    "sql": "CREATE TABLE asset_versions (\n  asset_id TEXT NOT NULL,\n  version TEXT NOT NULL,\n  content TEXT NOT NULL,\n  content_hash TEXT NOT NULL CHECK (length(content_hash)=64),\n  provenance TEXT NOT NULL,\n  verification TEXT NOT NULL,\n  created_at TEXT NOT NULL,\n  created_by TEXT NOT NULL,\n  PRIMARY KEY (asset_id,version),\n  FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE RESTRICT\n)"
  },
  {
    "type": "table",
    "name": "assets",
    "tbl_name": "assets",
    "sql": "CREATE TABLE assets (\n  asset_id TEXT PRIMARY KEY,\n  asset_type TEXT NOT NULL CHECK (asset_type IN ('KNOWLEDGE','SKILL','REALITY','DECISION')),\n  schema_version TEXT NOT NULL,\n  title TEXT NOT NULL,\n  status TEXT NOT NULL CHECK (status IN ('staging','accepted','superseded','retired')),\n  current_version TEXT NOT NULL,\n  content_hash TEXT NOT NULL CHECK (length(content_hash)=64),\n  created_at TEXT NOT NULL,\n  updated_at TEXT NOT NULL\n)"
  },
  {
    "type": "table",
    "name": "knowledge_candidates",
    "tbl_name": "knowledge_candidates",
    "sql": "CREATE TABLE knowledge_candidates (\n candidate_id TEXT PRIMARY KEY NOT NULL,\n asset_id TEXT NOT NULL,\n title TEXT NOT NULL,\n status TEXT NOT NULL CHECK(status IN ('DRAFT','PENDING_REVIEW','APPROVED_FOR_PROMOTION','PROMOTION_RESERVED','CANONICAL_READBACK_VERIFIED')),\n content TEXT NOT NULL,\n content_hash TEXT NOT NULL CHECK(length(content_hash)=64),\n version INTEGER NOT NULL CHECK(version>=1),\n provenance TEXT NOT NULL CHECK(json_valid(provenance)),\n created_at TEXT NOT NULL,\n review_state TEXT NOT NULL,\n review_result TEXT,\n reviewed_by TEXT,\n reviewed_at TEXT,\n review_evidence_ref TEXT,\n review_evidence_sha256 TEXT,\n expected_asset_version TEXT,\n CHECK(status NOT IN ('APPROVED_FOR_PROMOTION','PROMOTION_RESERVED','CANONICAL_READBACK_VERIFIED') OR\n coalesce((review_state='PASS' AND review_result='PASS' AND length(reviewed_by)>0 AND length(reviewed_at)>0 AND length(review_evidence_ref)>0 AND length(review_evidence_sha256)=64),0))\n) STRICT"
  },
  {
    "type": "table",
    "name": "personal_ai_approval_ledger",
    "tbl_name": "personal_ai_approval_ledger",
    "sql": `CREATE TABLE "personal_ai_approval_ledger" ( approval_id TEXT PRIMARY KEY NOT NULL, requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64), operation TEXT NOT NULL CHECK (operation IN ('deploy_worker_version','write_decision_record','decision_write','knowledge_write','KNOWLEDGE_PROMOTION','write_project_status_record')), exact_target TEXT NOT NULL CHECK (length(exact_target) BETWEEN 1 AND 240), payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64), created_at INTEGER NOT NULL CHECK (created_at > 0), expires_at INTEGER NOT NULL CHECK (expires_at > created_at AND expires_at - created_at <= 300000), consumed_at INTEGER CHECK (consumed_at IS NULL OR consumed_at >= created_at) ,
asset_type TEXT,candidate_id TEXT,candidate_version INTEGER,content_hash TEXT,review_result TEXT,approved_by TEXT,state TEXT NOT NULL DEFAULT 'REGISTERED',consumed INTEGER NOT NULL DEFAULT 0,consume_count INTEGER NOT NULL DEFAULT 0,invalidated INTEGER NOT NULL DEFAULT 0,invalidated_at TEXT,
exact_target_json TEXT CHECK(exact_target_json IS NULL OR(json_valid(exact_target_json) AND exact_target IS NOT NULL AND payload_sha256 IS NOT NULL AND length(payload_sha256)=64 AND payload_sha256 NOT GLOB '*[^0-9a-f]*' AND operation IS 'KNOWLEDGE_PROMOTION' AND exact_target='knowledge:v1:sha256:'||payload_sha256)),
time_basis TEXT CHECK(time_basis IS NULL OR(time_basis='epoch_ms_v1' AND operation IS 'KNOWLEDGE_PROMOTION' AND exact_target_json IS NOT NULL AND typeof(created_at)='integer' AND created_at>0 AND created_at<=9007199254740991 AND typeof(expires_at)='integer' AND expires_at>created_at AND expires_at<=9007199254740991 AND expires_at-created_at<=300000 AND(consumed_at IS NULL OR(typeof(consumed_at)='integer' AND consumed_at>=created_at AND consumed_at<=9007199254740991)))),FOREIGN KEY(operation) REFERENCES approval_ledger_operations(operation)) STRICT`
  },
  {
    "type": "table",
    "name": "personal_ai_approval_ledger__project_status_backup",
    "tbl_name": "personal_ai_approval_ledger__project_status_backup",
    "sql": `CREATE TABLE "personal_ai_approval_ledger__project_status_backup" (
  approval_id TEXT PRIMARY KEY NOT NULL,
  requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation TEXT NOT NULL CHECK (operation IN ('deploy_worker_version', 'write_decision_record')),
  exact_target TEXT NOT NULL CHECK (length(exact_target) BETWEEN 1 AND 240),
  payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
  created_at INTEGER NOT NULL CHECK (created_at > 0),
  expires_at INTEGER NOT NULL CHECK (expires_at > created_at AND expires_at - created_at <= 300000),
  consumed_at INTEGER CHECK (consumed_at IS NULL OR consumed_at >= created_at)
) STRICT`
  },
  {
    "type": "trigger",
    "name": "assertion_v1_atomic",
    "tbl_name": "approval_assertion_commits_v1",
    "sql": "CREATE TRIGGER assertion_v1_atomic AFTER INSERT ON approval_assertion_commits_v1 BEGIN\n SELECT CASE WHEN NEW.rp_id!='personal-ai-deploy-write-probe.tangyuandousha1010.chatgpt.site'\n OR NEW.accepted_at_ms<NEW.issued_at_ms OR NEW.sign_count<=NEW.expected_count\n OR NEW.accepted_at_ms>CAST((julianday('now')-2440587.5)*86400000 AS INTEGER)+2000\n OR NEW.accepted_at_ms<CAST((julianday('now')-2440587.5)*86400000 AS INTEGER)-10000\n OR NEW.expires_at_ms<=CAST((julianday('now')-2440587.5)*86400000 AS INTEGER)\n THEN RAISE(ABORT,'ATOMIC_TIME_COUNT_OR_RP_INVALID') END;\n SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM knowledge_candidates k WHERE\n k.candidate_id=json_extract(NEW.exact_target,'$.candidate_id') AND k.version=json_extract(NEW.exact_target,'$.candidate_version')\n AND k.content_hash=json_extract(NEW.exact_target,'$.content_hash') AND k.asset_id=json_extract(NEW.exact_target,'$.asset_id')\n AND k.reviewed_at=json_extract(NEW.exact_target,'$.reviewed_at') AND k.review_evidence_sha256=json_extract(NEW.exact_target,'$.review_evidence_sha256')\n AND k.expected_asset_version IS json_extract(NEW.exact_target,'$.expected_asset_version')\n AND k.status='APPROVED_FOR_PROMOTION' AND k.review_state='PASS' AND k.review_result='PASS'\n AND json_extract(NEW.exact_target,'$.operation')='KNOWLEDGE_PROMOTION'\n AND json_extract(NEW.exact_target,'$.production_contract')='KNOWLEDGE_PROD_V02_COUNTER_V1')\n THEN RAISE(ABORT,'ATOMIC_CANDIDATE_CHANGED') END;\n UPDATE approval_credential_counters_v1 SET last_count=NEW.sign_count,revision=revision+1,updated_at_ms=NEW.accepted_at_ms\n WHERE owner_hash=NEW.owner_hash AND rp_id=NEW.rp_id AND signer_identity=NEW.signer_identity\n AND enrollment_epoch=NEW.enrollment_epoch AND state='ACTIVE' AND mode='MONOTONIC'\n AND revision=NEW.expected_revision AND last_count=NEW.expected_count;\n SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,'ATOMIC_COUNTER_CAS_REJECTED') END;\n UPDATE personal_ai_approval_ledger SET consumed_at=NEW.accepted_at_ms,state='CHALLENGE_CONSUMED',consumed=1,consume_count=consume_count+1,approved_by=NEW.signer_identity\n WHERE approval_id=NEW.challenge_id AND requesting_user_hash=NEW.owner_hash AND operation='KNOWLEDGE_PROMOTION'\n AND exact_target='knowledge:v1:sha256:'||NEW.payload_sha256 AND exact_target_json=NEW.exact_target AND payload_sha256=NEW.payload_sha256\n AND time_basis='epoch_ms_v1' AND state='CHALLENGE_PENDING' AND consumed_at IS NULL AND consumed=0 AND consume_count=0 AND invalidated=0\n AND candidate_id IS NULL AND candidate_version IS NULL AND asset_type IS NULL AND content_hash IS NULL AND review_result IS NULL\n AND created_at=NEW.issued_at_ms AND expires_at=NEW.expires_at_ms;\n SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,'ATOMIC_CHALLENGE_CAS_REJECTED') END;\n INSERT INTO personal_ai_approval_ledger\n (approval_id,requesting_user_hash,operation,exact_target,exact_target_json,payload_sha256,time_basis,created_at,expires_at,asset_type,candidate_id,candidate_version,content_hash,review_result,approved_by)\n VALUES(NEW.approval_id,NEW.owner_hash,'KNOWLEDGE_PROMOTION','knowledge:v1:sha256:'||NEW.payload_sha256,NEW.exact_target,NEW.payload_sha256,'epoch_ms_v1',NEW.accepted_at_ms,NEW.expires_at_ms,\n 'KNOWLEDGE',json_extract(NEW.exact_target,'$.candidate_id'),json_extract(NEW.exact_target,'$.candidate_version'),json_extract(NEW.exact_target,'$.content_hash'),'PASS',NEW.signer_identity);\n SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,'ATOMIC_APPROVAL_INSERT_REJECTED') END;\nEND"
  },
  {
    "type": "trigger",
    "name": "assertion_v1_delete_guard",
    "tbl_name": "approval_assertion_commits_v1",
    "sql": "CREATE TRIGGER assertion_v1_delete_guard BEFORE DELETE ON approval_assertion_commits_v1 BEGIN\n SELECT RAISE(ABORT,'COMMIT_IMMUTABLE');\nEND"
  },
  {
    "type": "trigger",
    "name": "assertion_v1_update_guard",
    "tbl_name": "approval_assertion_commits_v1",
    "sql": "CREATE TRIGGER assertion_v1_update_guard BEFORE UPDATE ON approval_assertion_commits_v1 BEGIN\n SELECT RAISE(ABORT,'COMMIT_IMMUTABLE');\nEND"
  },
  {
    "type": "trigger",
    "name": "counter_v1_delete_guard",
    "tbl_name": "approval_credential_counters_v1",
    "sql": "CREATE TRIGGER counter_v1_delete_guard BEFORE DELETE ON approval_credential_counters_v1 BEGIN\n SELECT RAISE(ABORT,'COUNTER_DELETE_FORBIDDEN');\nEND"
  },
  {
    "type": "trigger",
    "name": "counter_v1_insert_guard",
    "tbl_name": "approval_credential_counters_v1",
    "sql": "CREATE TRIGGER counter_v1_insert_guard BEFORE INSERT ON approval_credential_counters_v1 BEGIN\n SELECT CASE WHEN NEW.state!='ACTIVE' OR NEW.mode!='MONOTONIC' OR NEW.last_count!=2 OR NEW.revision!=1\n OR NEW.rp_id!='personal-ai-deploy-write-probe.tangyuandousha1010.chatgpt.site'\n OR NEW.bootstrap_evidence_sha256!='2e0db873fb4b983fab5dc8fbd7ac9b3ed3dfd8f1d6a4143d30d6aba544782171'\n OR length(NEW.enrollment_epoch)<16 OR NEW.enrolled_at_ms<=0 OR NEW.updated_at_ms<NEW.enrolled_at_ms\n OR EXISTS(SELECT 1 FROM approval_assertion_commits_v1 WHERE owner_hash=NEW.owner_hash)\n OR EXISTS(SELECT 1 FROM personal_ai_approval_ledger WHERE requesting_user_hash=NEW.owner_hash AND operation='KNOWLEDGE_PROMOTION')\n THEN RAISE(ABORT,'COUNTER_IMPORT_ABSENT_HISTORY_REQUIRED') END;\nEND"
  },
  {
    "type": "trigger",
    "name": "counter_v1_update_guard",
    "tbl_name": "approval_credential_counters_v1",
    "sql": "CREATE TRIGGER counter_v1_update_guard BEFORE UPDATE ON approval_credential_counters_v1 BEGIN\n SELECT CASE WHEN NEW.owner_hash!=OLD.owner_hash OR NEW.rp_id!=OLD.rp_id OR NEW.signer_identity!=OLD.signer_identity\n OR NEW.enrollment_epoch!=OLD.enrollment_epoch OR NEW.enrolled_at_ms!=OLD.enrolled_at_ms\n OR NEW.bootstrap_evidence_sha256!=OLD.bootstrap_evidence_sha256 OR OLD.state!='ACTIVE'\n OR NOT ((NEW.state='REVOKED' AND NEW.mode=OLD.mode AND NEW.last_count=OLD.last_count AND NEW.revision=OLD.revision AND NEW.updated_at_ms=OLD.updated_at_ms)\n OR (NEW.state='ACTIVE' AND NEW.mode='MONOTONIC' AND NEW.last_count>OLD.last_count AND NEW.revision=OLD.revision+1 AND NEW.updated_at_ms>=OLD.updated_at_ms))\n THEN RAISE(ABORT,'COUNTER_TRANSITION_INVALID') END;\nEND"
  }
];
var SCHEMA_GUARD = `(SELECT count(*) FROM sqlite_master WHERE tbl_name IN ('assets','asset_versions','asset_audit','personal_ai_approval_ledger','personal_ai_approval_ledger__project_status_backup','approval_ledger_operations','knowledge_candidates','approval_credential_counters_v1','approval_assertion_commits_v1'))=32 AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_approval_ledger_binding' AND tbl_name='personal_ai_approval_ledger' AND sql IS 'CREATE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,content_hash)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_approval_ledger_state' AND tbl_name='personal_ai_approval_ledger' AND sql IS 'CREATE INDEX idx_approval_ledger_state ON personal_ai_approval_ledger(operation,consumed,invalidated)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_asset_audit_asset_time' AND tbl_name='asset_audit' AND sql IS 'CREATE INDEX idx_asset_audit_asset_time ON asset_audit(asset_id,timestamp)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_assets_type_status_title' AND tbl_name='assets' AND sql IS 'CREATE INDEX idx_assets_type_status_title ON assets(asset_type,status,title)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_knowledge_candidates_asset' AND tbl_name='knowledge_candidates' AND sql IS 'CREATE INDEX idx_knowledge_candidates_asset ON knowledge_candidates(asset_id)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_knowledge_candidates_status' AND tbl_name='knowledge_candidates' AND sql IS 'CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(status)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_approval_assertion_commits_v1_1' AND tbl_name='approval_assertion_commits_v1' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_approval_assertion_commits_v1_2' AND tbl_name='approval_assertion_commits_v1' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_approval_assertion_commits_v1_3' AND tbl_name='approval_assertion_commits_v1' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_approval_credential_counters_v1_1' AND tbl_name='approval_credential_counters_v1' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_approval_ledger_operations_1' AND tbl_name='approval_ledger_operations' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_asset_audit_1' AND tbl_name='asset_audit' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_asset_versions_1' AND tbl_name='asset_versions' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_assets_1' AND tbl_name='assets' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_knowledge_candidates_1' AND tbl_name='knowledge_candidates' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_personal_ai_approval_ledger_1' AND tbl_name='personal_ai_approval_ledger' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='index' AND name='sqlite_autoindex_personal_ai_approval_ledger__project_status_backup_1' AND tbl_name='personal_ai_approval_ledger__project_status_backup' AND sql IS NULL) AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='approval_assertion_commits_v1' AND tbl_name='approval_assertion_commits_v1' AND sql IS 'CREATE TABLE approval_assertion_commits_v1 (
 ceremony_id TEXT PRIMARY KEY NOT NULL CHECK(length(ceremony_id)=43),
 challenge_id TEXT UNIQUE NOT NULL,
 approval_id TEXT UNIQUE NOT NULL,
 owner_hash TEXT NOT NULL,
 rp_id TEXT NOT NULL,
 signer_identity TEXT NOT NULL,
 enrollment_epoch TEXT NOT NULL,
 expected_revision INTEGER NOT NULL,
 expected_mode TEXT NOT NULL CHECK(expected_mode=''MONOTONIC''),
 expected_count INTEGER NOT NULL,
 sign_count INTEGER NOT NULL,
 exact_target TEXT NOT NULL CHECK(json_valid(exact_target)),
 payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
 issued_at_ms INTEGER NOT NULL,
 expires_at_ms INTEGER NOT NULL,
 accepted_at_ms INTEGER NOT NULL,
 CHECK(expires_at_ms-issued_at_ms=300000),
 CHECK(approval_id=''knowledge:''||ceremony_id),
 CHECK(substr(challenge_id,1,48)=''PAI:''||ceremony_id||'':'')
) STRICT') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='approval_credential_counters_v1' AND tbl_name='approval_credential_counters_v1' AND sql IS 'CREATE TABLE approval_credential_counters_v1 (
 owner_hash TEXT NOT NULL CHECK(length(owner_hash)=64),
 rp_id TEXT NOT NULL,
 signer_identity TEXT NOT NULL CHECK(length(signer_identity)=73),
 enrollment_epoch TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN (''ACTIVE'',''REVOKED'')),
 mode TEXT NOT NULL CHECK(mode=''MONOTONIC''),
 last_count INTEGER NOT NULL CHECK(last_count>=2 AND last_count<=4294967295),
 revision INTEGER NOT NULL CHECK(revision>=1),
 enrolled_at_ms INTEGER NOT NULL,
 updated_at_ms INTEGER NOT NULL,
 bootstrap_evidence_sha256 TEXT NOT NULL,
 PRIMARY KEY(owner_hash,rp_id,signer_identity)
) STRICT') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='approval_ledger_operations' AND tbl_name='approval_ledger_operations' AND sql IS 'CREATE TABLE approval_ledger_operations(operation TEXT PRIMARY KEY,asset_type TEXT NOT NULL,canonical_writer TEXT NOT NULL,single_use INTEGER NOT NULL DEFAULT 1,replay_guard INTEGER NOT NULL DEFAULT 1)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='asset_audit' AND tbl_name='asset_audit' AND sql IS 'CREATE TABLE asset_audit (
  event_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  action TEXT NOT NULL,
  version TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  actor TEXT NOT NULL,
  metadata TEXT NOT NULL,
  FOREIGN KEY (asset_id,version) REFERENCES asset_versions(asset_id,version) ON DELETE RESTRICT
)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='asset_versions' AND tbl_name='asset_versions' AND sql IS 'CREATE TABLE asset_versions (
  asset_id TEXT NOT NULL,
  version TEXT NOT NULL,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL CHECK (length(content_hash)=64),
  provenance TEXT NOT NULL,
  verification TEXT NOT NULL,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  PRIMARY KEY (asset_id,version),
  FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE RESTRICT
)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='assets' AND tbl_name='assets' AND sql IS 'CREATE TABLE assets (
  asset_id TEXT PRIMARY KEY,
  asset_type TEXT NOT NULL CHECK (asset_type IN (''KNOWLEDGE'',''SKILL'',''REALITY'',''DECISION'')),
  schema_version TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN (''staging'',''accepted'',''superseded'',''retired'')),
  current_version TEXT NOT NULL,
  content_hash TEXT NOT NULL CHECK (length(content_hash)=64),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge_candidates' AND tbl_name='knowledge_candidates' AND sql IS 'CREATE TABLE knowledge_candidates (
 candidate_id TEXT PRIMARY KEY NOT NULL,
 asset_id TEXT NOT NULL,
 title TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN (''DRAFT'',''PENDING_REVIEW'',''APPROVED_FOR_PROMOTION'',''PROMOTION_RESERVED'',''CANONICAL_READBACK_VERIFIED'')),
 content TEXT NOT NULL,
 content_hash TEXT NOT NULL CHECK(length(content_hash)=64),
 version INTEGER NOT NULL CHECK(version>=1),
 provenance TEXT NOT NULL CHECK(json_valid(provenance)),
 created_at TEXT NOT NULL,
 review_state TEXT NOT NULL,
 review_result TEXT,
 reviewed_by TEXT,
 reviewed_at TEXT,
 review_evidence_ref TEXT,
 review_evidence_sha256 TEXT,
 expected_asset_version TEXT,
 CHECK(status NOT IN (''APPROVED_FOR_PROMOTION'',''PROMOTION_RESERVED'',''CANONICAL_READBACK_VERIFIED'') OR
 coalesce((review_state=''PASS'' AND review_result=''PASS'' AND length(reviewed_by)>0 AND length(reviewed_at)>0 AND length(review_evidence_ref)>0 AND length(review_evidence_sha256)=64),0))
) STRICT') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_ai_approval_ledger' AND tbl_name='personal_ai_approval_ledger' AND sql IS 'CREATE TABLE "personal_ai_approval_ledger" ( approval_id TEXT PRIMARY KEY NOT NULL, requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64), operation TEXT NOT NULL CHECK (operation IN (''deploy_worker_version'',''write_decision_record'',''decision_write'',''knowledge_write'',''KNOWLEDGE_PROMOTION'',''write_project_status_record'')), exact_target TEXT NOT NULL CHECK (length(exact_target) BETWEEN 1 AND 240), payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64), created_at INTEGER NOT NULL CHECK (created_at > 0), expires_at INTEGER NOT NULL CHECK (expires_at > created_at AND expires_at - created_at <= 300000), consumed_at INTEGER CHECK (consumed_at IS NULL OR consumed_at >= created_at) ,
asset_type TEXT,candidate_id TEXT,candidate_version INTEGER,content_hash TEXT,review_result TEXT,approved_by TEXT,state TEXT NOT NULL DEFAULT ''REGISTERED'',consumed INTEGER NOT NULL DEFAULT 0,consume_count INTEGER NOT NULL DEFAULT 0,invalidated INTEGER NOT NULL DEFAULT 0,invalidated_at TEXT,
exact_target_json TEXT CHECK(exact_target_json IS NULL OR(json_valid(exact_target_json) AND exact_target IS NOT NULL AND payload_sha256 IS NOT NULL AND length(payload_sha256)=64 AND payload_sha256 NOT GLOB ''*[^0-9a-f]*'' AND operation IS ''KNOWLEDGE_PROMOTION'' AND exact_target=''knowledge:v1:sha256:''||payload_sha256)),
time_basis TEXT CHECK(time_basis IS NULL OR(time_basis=''epoch_ms_v1'' AND operation IS ''KNOWLEDGE_PROMOTION'' AND exact_target_json IS NOT NULL AND typeof(created_at)=''integer'' AND created_at>0 AND created_at<=9007199254740991 AND typeof(expires_at)=''integer'' AND expires_at>created_at AND expires_at<=9007199254740991 AND expires_at-created_at<=300000 AND(consumed_at IS NULL OR(typeof(consumed_at)=''integer'' AND consumed_at>=created_at AND consumed_at<=9007199254740991)))),FOREIGN KEY(operation) REFERENCES approval_ledger_operations(operation)) STRICT') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_ai_approval_ledger__project_status_backup' AND tbl_name='personal_ai_approval_ledger__project_status_backup' AND sql IS 'CREATE TABLE "personal_ai_approval_ledger__project_status_backup" (
  approval_id TEXT PRIMARY KEY NOT NULL,
  requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation TEXT NOT NULL CHECK (operation IN (''deploy_worker_version'', ''write_decision_record'')),
  exact_target TEXT NOT NULL CHECK (length(exact_target) BETWEEN 1 AND 240),
  payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
  created_at INTEGER NOT NULL CHECK (created_at > 0),
  expires_at INTEGER NOT NULL CHECK (expires_at > created_at AND expires_at - created_at <= 300000),
  consumed_at INTEGER CHECK (consumed_at IS NULL OR consumed_at >= created_at)
) STRICT') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='assertion_v1_atomic' AND tbl_name='approval_assertion_commits_v1' AND sql IS 'CREATE TRIGGER assertion_v1_atomic AFTER INSERT ON approval_assertion_commits_v1 BEGIN
 SELECT CASE WHEN NEW.rp_id!=''personal-ai-deploy-write-probe.tangyuandousha1010.chatgpt.site''
 OR NEW.accepted_at_ms<NEW.issued_at_ms OR NEW.sign_count<=NEW.expected_count
 OR NEW.accepted_at_ms>CAST((julianday(''now'')-2440587.5)*86400000 AS INTEGER)+2000
 OR NEW.accepted_at_ms<CAST((julianday(''now'')-2440587.5)*86400000 AS INTEGER)-10000
 OR NEW.expires_at_ms<=CAST((julianday(''now'')-2440587.5)*86400000 AS INTEGER)
 THEN RAISE(ABORT,''ATOMIC_TIME_COUNT_OR_RP_INVALID'') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM knowledge_candidates k WHERE
 k.candidate_id=json_extract(NEW.exact_target,''$.candidate_id'') AND k.version=json_extract(NEW.exact_target,''$.candidate_version'')
 AND k.content_hash=json_extract(NEW.exact_target,''$.content_hash'') AND k.asset_id=json_extract(NEW.exact_target,''$.asset_id'')
 AND k.reviewed_at=json_extract(NEW.exact_target,''$.reviewed_at'') AND k.review_evidence_sha256=json_extract(NEW.exact_target,''$.review_evidence_sha256'')
 AND k.expected_asset_version IS json_extract(NEW.exact_target,''$.expected_asset_version'')
 AND k.status=''APPROVED_FOR_PROMOTION'' AND k.review_state=''PASS'' AND k.review_result=''PASS''
 AND json_extract(NEW.exact_target,''$.operation'')=''KNOWLEDGE_PROMOTION''
 AND json_extract(NEW.exact_target,''$.production_contract'')=''KNOWLEDGE_PROD_V02_COUNTER_V1'')
 THEN RAISE(ABORT,''ATOMIC_CANDIDATE_CHANGED'') END;
 UPDATE approval_credential_counters_v1 SET last_count=NEW.sign_count,revision=revision+1,updated_at_ms=NEW.accepted_at_ms
 WHERE owner_hash=NEW.owner_hash AND rp_id=NEW.rp_id AND signer_identity=NEW.signer_identity
 AND enrollment_epoch=NEW.enrollment_epoch AND state=''ACTIVE'' AND mode=''MONOTONIC''
 AND revision=NEW.expected_revision AND last_count=NEW.expected_count;
 SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,''ATOMIC_COUNTER_CAS_REJECTED'') END;
 UPDATE personal_ai_approval_ledger SET consumed_at=NEW.accepted_at_ms,state=''CHALLENGE_CONSUMED'',consumed=1,consume_count=consume_count+1,approved_by=NEW.signer_identity
 WHERE approval_id=NEW.challenge_id AND requesting_user_hash=NEW.owner_hash AND operation=''KNOWLEDGE_PROMOTION''
 AND exact_target=''knowledge:v1:sha256:''||NEW.payload_sha256 AND exact_target_json=NEW.exact_target AND payload_sha256=NEW.payload_sha256
 AND time_basis=''epoch_ms_v1'' AND state=''CHALLENGE_PENDING'' AND consumed_at IS NULL AND consumed=0 AND consume_count=0 AND invalidated=0
 AND candidate_id IS NULL AND candidate_version IS NULL AND asset_type IS NULL AND content_hash IS NULL AND review_result IS NULL
 AND created_at=NEW.issued_at_ms AND expires_at=NEW.expires_at_ms;
 SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,''ATOMIC_CHALLENGE_CAS_REJECTED'') END;
 INSERT INTO personal_ai_approval_ledger
 (approval_id,requesting_user_hash,operation,exact_target,exact_target_json,payload_sha256,time_basis,created_at,expires_at,asset_type,candidate_id,candidate_version,content_hash,review_result,approved_by)
 VALUES(NEW.approval_id,NEW.owner_hash,''KNOWLEDGE_PROMOTION'',''knowledge:v1:sha256:''||NEW.payload_sha256,NEW.exact_target,NEW.payload_sha256,''epoch_ms_v1'',NEW.accepted_at_ms,NEW.expires_at_ms,
 ''KNOWLEDGE'',json_extract(NEW.exact_target,''$.candidate_id''),json_extract(NEW.exact_target,''$.candidate_version''),json_extract(NEW.exact_target,''$.content_hash''),''PASS'',NEW.signer_identity);
 SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,''ATOMIC_APPROVAL_INSERT_REJECTED'') END;
END') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='assertion_v1_delete_guard' AND tbl_name='approval_assertion_commits_v1' AND sql IS 'CREATE TRIGGER assertion_v1_delete_guard BEFORE DELETE ON approval_assertion_commits_v1 BEGIN
 SELECT RAISE(ABORT,''COMMIT_IMMUTABLE'');
END') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='assertion_v1_update_guard' AND tbl_name='approval_assertion_commits_v1' AND sql IS 'CREATE TRIGGER assertion_v1_update_guard BEFORE UPDATE ON approval_assertion_commits_v1 BEGIN
 SELECT RAISE(ABORT,''COMMIT_IMMUTABLE'');
END') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='counter_v1_delete_guard' AND tbl_name='approval_credential_counters_v1' AND sql IS 'CREATE TRIGGER counter_v1_delete_guard BEFORE DELETE ON approval_credential_counters_v1 BEGIN
 SELECT RAISE(ABORT,''COUNTER_DELETE_FORBIDDEN'');
END') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='counter_v1_insert_guard' AND tbl_name='approval_credential_counters_v1' AND sql IS 'CREATE TRIGGER counter_v1_insert_guard BEFORE INSERT ON approval_credential_counters_v1 BEGIN
 SELECT CASE WHEN NEW.state!=''ACTIVE'' OR NEW.mode!=''MONOTONIC'' OR NEW.last_count!=2 OR NEW.revision!=1
 OR NEW.rp_id!=''personal-ai-deploy-write-probe.tangyuandousha1010.chatgpt.site''
 OR NEW.bootstrap_evidence_sha256!=''2e0db873fb4b983fab5dc8fbd7ac9b3ed3dfd8f1d6a4143d30d6aba544782171''
 OR length(NEW.enrollment_epoch)<16 OR NEW.enrolled_at_ms<=0 OR NEW.updated_at_ms<NEW.enrolled_at_ms
 OR EXISTS(SELECT 1 FROM approval_assertion_commits_v1 WHERE owner_hash=NEW.owner_hash)
 OR EXISTS(SELECT 1 FROM personal_ai_approval_ledger WHERE requesting_user_hash=NEW.owner_hash AND operation=''KNOWLEDGE_PROMOTION'')
 THEN RAISE(ABORT,''COUNTER_IMPORT_ABSENT_HISTORY_REQUIRED'') END;
END') AND EXISTS(SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='counter_v1_update_guard' AND tbl_name='approval_credential_counters_v1' AND sql IS 'CREATE TRIGGER counter_v1_update_guard BEFORE UPDATE ON approval_credential_counters_v1 BEGIN
 SELECT CASE WHEN NEW.owner_hash!=OLD.owner_hash OR NEW.rp_id!=OLD.rp_id OR NEW.signer_identity!=OLD.signer_identity
 OR NEW.enrollment_epoch!=OLD.enrollment_epoch OR NEW.enrolled_at_ms!=OLD.enrolled_at_ms
 OR NEW.bootstrap_evidence_sha256!=OLD.bootstrap_evidence_sha256 OR OLD.state!=''ACTIVE''
 OR NOT ((NEW.state=''REVOKED'' AND NEW.mode=OLD.mode AND NEW.last_count=OLD.last_count AND NEW.revision=OLD.revision AND NEW.updated_at_ms=OLD.updated_at_ms)
 OR (NEW.state=''ACTIVE'' AND NEW.mode=''MONOTONIC'' AND NEW.last_count>OLD.last_count AND NEW.revision=OLD.revision+1 AND NEW.updated_at_ms>=OLD.updated_at_ms))
 THEN RAISE(ABORT,''COUNTER_TRANSITION_INVALID'') END;
END') AND (SELECT json_group_array(json_array(operation,asset_type,canonical_writer,single_use,replay_guard)) FROM (SELECT * FROM approval_ledger_operations ORDER BY operation))='[["KNOWLEDGE_PROMOTION","KNOWLEDGE","writeKnowledgeCandidate",1,1],["decision_write","DECISION","writeDecisionRecord",1,1],["deploy_worker_version","DEPLOY","deployWorkerVersion",1,1],["knowledge_write","KNOWLEDGE","writeKnowledgeCandidate",1,1],["write_decision_record","DECISION","writeDecisionRecord",1,1],["write_project_status_record","REALITY","writeProjectStatusRecord",1,1]]'`;

// dispatch/production-knowledge-minimal-package-20261020/worker/knowledge-production.mjs
var reject = (code, outcome = "NOT_ATTEMPTED") => ({ isError: true, text: code, structuredContent: { status: "BLOCKED", reason: code, outcome, retry_allowed: false, canonical_write_performed: outcome === "NOT_ATTEMPTED" ? false : null } });
async function guardedKnowledgePromote(env, input, { writer, verifyVersion }) {
  let stage = "preflight", attempted = false;
  try {
    if (!input || Object.keys(input).some((k2) => !["candidate_operation", "candidate_id", "candidate_version", "content_hash", "approval_id"].includes(k2)) || input.candidate_operation !== "promote" || typeof input.candidate_id !== "string" || !Number.isSafeInteger(input.candidate_version) || !/^[a-f0-9]{64}$/.test(input.content_hash) || !/^knowledge:[A-Za-z0-9_-]{43}$/.test(input.approval_id)) return reject("EXACT_REGISTERED_KNOWLEDGE_APPROVAL_REQUIRED");
    const db = env?.ASSET_DB;
    if (!db) return reject("ASSET_WRITE_UNAVAILABLE");
    await checkedSchema(db, SNAPSHOT);
    const k = await db.prepare("SELECT * FROM knowledge_candidates WHERE candidate_id=?").bind(input.candidate_id).first();
    if (!k || k.version !== input.candidate_version || k.content_hash !== input.content_hash || k.status !== "APPROVED_FOR_PROMOTION" || k.review_state !== "PASS" || k.review_result !== "PASS") return reject("CANDIDATE_NOT_REVIEWED_PASS");
    const exact = exactTarget(candidatePayload(k)), digest = await hash(exact);
    if (await hash(k.content) !== k.content_hash) return reject("CANDIDATE_HASH_CHANGED");
    const p = checkedProvenance(k.provenance);
    const target = await db.prepare("SELECT asset_type,current_version,content_hash FROM assets WHERE asset_id=?").bind(k.asset_id).first();
    if (target && target.asset_type !== "KNOWLEDGE" || (target?.current_version ?? null) !== k.expected_asset_version) return reject("TARGET_VERSION_CHANGED");
    if (target?.content_hash === k.content_hash) return reject("DUPLICATE_CANONICAL_NO_WRITE");
    const a = await db.prepare("SELECT * FROM personal_ai_approval_ledger WHERE approval_id=?").bind(input.approval_id).first();
    const c = await db.prepare("SELECT * FROM approval_assertion_commits_v1 WHERE approval_id=?").bind(input.approval_id).first();
    if (!a || !c) return reject("TRUSTED_ATOMIC_APPROVAL_REQUIRED");
    const counter = await db.prepare("SELECT * FROM approval_credential_counters_v1 WHERE owner_hash=? AND rp_id=? AND signer_identity=?").bind(c.owner_hash, RP, c.signer_identity).first();
    const now = Date.now();
    if (a.operation !== "KNOWLEDGE_PROMOTION" || a.asset_type !== "KNOWLEDGE" || a.exact_target !== "knowledge:v1:sha256:" + digest || a.exact_target_json !== exact || a.payload_sha256 !== digest || a.time_basis !== "epoch_ms_v1" || a.candidate_id !== k.candidate_id || a.candidate_version !== k.version || a.content_hash !== k.content_hash || a.review_result !== "PASS" || a.state !== "REGISTERED" || a.consumed !== 0 || a.consume_count !== 0 || a.consumed_at !== null || a.invalidated !== 0 || !Number.isSafeInteger(a.expires_at) || a.expires_at <= now || a.created_at > now || a.expires_at - a.created_at > 3e5 || a.requesting_user_hash !== c.owner_hash || a.approved_by !== c.signer_identity || c.exact_target !== exact || c.payload_sha256 !== digest || c.rp_id !== RP || !counter || counter.state !== "ACTIVE" || counter.enrollment_epoch !== c.enrollment_epoch || counter.revision < c.expected_revision + 1 || counter.last_count < c.sign_count || counter.bootstrap_evidence_sha256 !== SEED_EVIDENCE) return reject("APPROVAL_BINDING_OR_TTL_INVALID");
    const claim = db.prepare(`UPDATE knowledge_candidates SET status='PROMOTION_RESERVED' WHERE candidate_id=? AND version=? AND content_hash=? AND asset_id=? AND reviewed_at=? AND review_evidence_sha256=? AND content=? AND status='APPROVED_FOR_PROMOTION' AND review_state='PASS' AND review_result='PASS' AND expected_asset_version IS ? AND ((? IS NULL AND NOT EXISTS(SELECT 1 FROM assets WHERE asset_id=?)) OR EXISTS(SELECT 1 FROM assets WHERE asset_id=? AND asset_type='KNOWLEDGE' AND current_version=?)) AND (${SCHEMA_GUARD})`).bind(k.candidate_id, k.version, k.content_hash, k.asset_id, k.reviewed_at, k.review_evidence_sha256, k.content, k.expected_asset_version, k.expected_asset_version, k.asset_id, k.asset_id, k.expected_asset_version);
    const consume = db.prepare(`UPDATE personal_ai_approval_ledger SET consumed=1,state='CONSUMED',consume_count=consume_count+1,consumed_at=CAST((julianday('now')-2440587.5)*86400000 AS INTEGER) WHERE approval_id=? AND requesting_user_hash=? AND approved_by=? AND operation='KNOWLEDGE_PROMOTION' AND candidate_id=? AND candidate_version=? AND content_hash=? AND exact_target=? AND exact_target_json=? AND payload_sha256=? AND time_basis='epoch_ms_v1' AND state='REGISTERED' AND consumed=0 AND consume_count=0 AND consumed_at IS NULL AND invalidated=0 AND created_at<=CAST((julianday('now')-2440587.5)*86400000 AS INTEGER) AND expires_at>CAST((julianday('now')-2440587.5)*86400000 AS INTEGER) AND EXISTS(SELECT 1 FROM knowledge_candidates WHERE candidate_id=? AND status='PROMOTION_RESERVED' AND version=? AND content_hash=? AND reviewed_at=?) AND (${SCHEMA_GUARD})`).bind(a.approval_id, c.owner_hash, c.signer_identity, k.candidate_id, k.version, k.content_hash, "knowledge:v1:sha256:" + digest, exact, digest, k.candidate_id, k.version, k.content_hash, k.reviewed_at);
    const guard = db.prepare("SELECT CASE WHEN changes()=1 THEN 1 ELSE json('KNOWLEDGE_APPROVAL_CAS_LOST') END AS ok");
    stage = "claim_consume";
    attempted = true;
    const receipt = await db.batch([claim, guard, consume, guard]);
    if (receipt[0]?.meta?.changes !== 1 || receipt[2]?.meta?.changes !== 1) return reject("CLAIM_CONSUME_OUTCOME_UNKNOWN", "UNKNOWN_RECONCILE_REQUIRED");
    stage = "canonical_writer";
    const result = await writer(env, { __knowledge_gate: "KNOWLEDGE_PROD_V02_COUNTER_V1", expected_current_version: k.expected_asset_version, asset_id: k.asset_id, title: k.title, content: k.content, source_identity: p.source.identity, source_location: p.source.location, source_version: p.source_version, content_version: p.content_version, source_content_hash: p.source_content_hash ?? null, captured_at: p.captured_at, supersedes: [...p.supersedes ?? [], ...k.expected_asset_version === null ? [] : [k.asset_id + "@" + k.expected_asset_version]], promotion_decision: "PROMOTE", promotion_event: "knowledge-approval:" + a.approval_id, actor: a.approved_by, created_by: a.approved_by });
    if (result?.isError || !result?.structuredContent) return reject("CANONICAL_WRITE_OUTCOME_UNKNOWN", "UNKNOWN_RECONCILE_REQUIRED");
    const written = result.structuredContent;
    if (written.asset_id !== k.asset_id || written.content_hash !== k.content_hash || Number(written.version) !== Number(k.expected_asset_version ?? 0) + 1 || !await verifyVersion(db, k.asset_id, written.version, k.content_hash, k.content)) return reject("CANONICAL_READBACK_UNKNOWN", "UNKNOWN_RECONCILE_REQUIRED");
    stage = "status_readback";
    const q = await db.prepare("UPDATE knowledge_candidates SET status='CANONICAL_READBACK_VERIFIED' WHERE candidate_id=? AND status='PROMOTION_RESERVED' AND version=? AND content_hash=? AND reviewed_at=?").bind(k.candidate_id, k.version, k.content_hash, k.reviewed_at).run();
    if (q.meta?.changes !== 1) return reject("CANDIDATE_CLOSEOUT_UNKNOWN", "UNKNOWN_RECONCILE_REQUIRED");
    const final = { ...written, candidate_id: k.candidate_id, candidate_status: "CANONICAL_READBACK_VERIFIED", approval_id: a.approval_id, retry_allowed: false, read_back_verified: true, canonical_write_performed: true };
    return { ...result, text: JSON.stringify(final), structuredContent: final };
  } catch {
    return reject("KNOWLEDGE_" + stage.toUpperCase() + "_STOPPED", attempted ? "UNKNOWN_RECONCILE_REQUIRED" : "NOT_ATTEMPTED");
  }
}


// src/index.js
var u8 = Uint8Array;
var u16 = Uint16Array;
var i32 = Int32Array;
var fleb = new u8([
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  1,
  1,
  1,
  1,
  2,
  2,
  2,
  2,
  3,
  3,
  3,
  3,
  4,
  4,
  4,
  4,
  5,
  5,
  5,
  5,
  0,
  /* unused */
  0,
  0,
  /* impossible */
  0
]);
var fdeb = new u8([
  0,
  0,
  0,
  0,
  1,
  1,
  2,
  2,
  3,
  3,
  4,
  4,
  5,
  5,
  6,
  6,
  7,
  7,
  8,
  8,
  9,
  9,
  10,
  10,
  11,
  11,
  12,
  12,
  13,
  13,
  /* unused */
  0,
  0
]);
var clim = new u8([16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]);
var freb = function(eb, start) {
  var b = new u16(31);
  for (var i2 = 0; i2 < 31; ++i2) {
    b[i2] = start += 1 << eb[i2 - 1];
  }
  var r = new i32(b[30]);
  for (var i2 = 1; i2 < 30; ++i2) {
    for (var j = b[i2]; j < b[i2 + 1]; ++j) {
      r[j] = j - b[i2] << 5 | i2;
    }
  }
  return { b, r };
};
var _a = freb(fleb, 2);
var fl = _a.b;
var revfl = _a.r;
fl[28] = 258, revfl[258] = 28;
var _b = freb(fdeb, 0);
var fd = _b.b;
var revfd = _b.r;
var rev = new u16(32768);
for (i = 0; i < 32768; ++i) {
  x = (i & 43690) >> 1 | (i & 21845) << 1;
  x = (x & 52428) >> 2 | (x & 13107) << 2;
  x = (x & 61680) >> 4 | (x & 3855) << 4;
  rev[i] = ((x & 65280) >> 8 | (x & 255) << 8) >> 1;
}
var x;
var i;
var hMap = (function(cd, mb, r) {
  var s = cd.length;
  var i2 = 0;
  var l = new u16(mb);
  for (; i2 < s; ++i2) {
    if (cd[i2])
      ++l[cd[i2] - 1];
  }
  var le = new u16(mb);
  for (i2 = 1; i2 < mb; ++i2) {
    le[i2] = le[i2 - 1] + l[i2 - 1] << 1;
  }
  var co;
  if (r) {
    co = new u16(1 << mb);
    var rvb = 15 - mb;
    for (i2 = 0; i2 < s; ++i2) {
      if (cd[i2]) {
        var sv = i2 << 4 | cd[i2];
        var r_1 = mb - cd[i2];
        var v = le[cd[i2] - 1]++ << r_1;
        for (var m = v | (1 << r_1) - 1; v <= m; ++v) {
          co[rev[v] >> rvb] = sv;
        }
      }
    }
  } else {
    co = new u16(s);
    for (i2 = 0; i2 < s; ++i2) {
      if (cd[i2]) {
        co[i2] = rev[le[cd[i2] - 1]++] >> 15 - cd[i2];
      }
    }
  }
  return co;
});
var flt = new u8(288);
for (i = 0; i < 144; ++i)
  flt[i] = 8;
var i;
for (i = 144; i < 256; ++i)
  flt[i] = 9;
var i;
for (i = 256; i < 280; ++i)
  flt[i] = 7;
var i;
for (i = 280; i < 288; ++i)
  flt[i] = 8;
var i;
var fdt = new u8(32);
for (i = 0; i < 32; ++i)
  fdt[i] = 5;
var i;
var flrm = /* @__PURE__ */ hMap(flt, 9, 1);
var fdrm = /* @__PURE__ */ hMap(fdt, 5, 1);
var max = function(a) {
  var m = a[0];
  for (var i2 = 1; i2 < a.length; ++i2) {
    if (a[i2] > m)
      m = a[i2];
  }
  return m;
};
var bits = function(d, p, m) {
  var o = p / 8 | 0;
  return (d[o] | d[o + 1] << 8) >> (p & 7) & m;
};
var bits16 = function(d, p) {
  var o = p / 8 | 0;
  return (d[o] | d[o + 1] << 8 | d[o + 2] << 16) >> (p & 7);
};
var shft = function(p) {
  return (p + 7) / 8 | 0;
};
var slc = function(v, s, e) {
  if (s == null || s < 0)
    s = 0;
  if (e == null || e > v.length)
    e = v.length;
  return new u8(v.subarray(s, e));
};
var ec = [
  "unexpected EOF",
  "invalid block type",
  "invalid length/literal",
  "invalid distance",
  "stream finished",
  "no stream handler",
  ,
  // determined by compression function
  "no callback",
  "invalid UTF-8 data",
  "extra field too long",
  "date not in range 1980-2099",
  "filename too long",
  "stream finishing",
  "invalid zip data"
  // determined by unknown compression method
];
var err = function(ind, msg, nt) {
  var e = new Error(msg || ec[ind]);
  e.code = ind;
  if (Error.captureStackTrace)
    Error.captureStackTrace(e, err);
  if (!nt)
    throw e;
  return e;
};
var inflt = function(dat, st, buf, dict) {
  var sl = dat.length, dl = dict ? dict.length : 0;
  if (!sl || st.f && !st.l)
    return buf || new u8(0);
  var noBuf = !buf;
  var resize = noBuf || st.i != 2;
  var noSt = st.i;
  if (noBuf)
    buf = new u8(sl * 3);
  var cbuf = function(l2) {
    var bl = buf.length;
    if (l2 > bl) {
      var nbuf = new u8(Math.max(bl * 2, l2));
      nbuf.set(buf);
      buf = nbuf;
    }
  };
  var final = st.f || 0, pos = st.p || 0, bt = st.b || 0, lm = st.l, dm = st.d, lbt = st.m, dbt = st.n;
  var tbts = sl * 8;
  do {
    if (!lm) {
      final = bits(dat, pos, 1);
      var type = bits(dat, pos + 1, 3);
      pos += 3;
      if (!type) {
        var s = shft(pos) + 4, l = dat[s - 4] | dat[s - 3] << 8, t = s + l;
        if (t > sl) {
          if (noSt)
            err(0);
          break;
        }
        if (resize)
          cbuf(bt + l);
        buf.set(dat.subarray(s, t), bt);
        st.b = bt += l, st.p = pos = t * 8, st.f = final;
        continue;
      } else if (type == 1)
        lm = flrm, dm = fdrm, lbt = 9, dbt = 5;
      else if (type == 2) {
        var hLit = bits(dat, pos, 31) + 257, hcLen = bits(dat, pos + 10, 15) + 4;
        var tl = hLit + bits(dat, pos + 5, 31) + 1;
        pos += 14;
        var ldt = new u8(tl);
        var clt = new u8(19);
        for (var i2 = 0; i2 < hcLen; ++i2) {
          clt[clim[i2]] = bits(dat, pos + i2 * 3, 7);
        }
        pos += hcLen * 3;
        var clb = max(clt), clbmsk = (1 << clb) - 1;
        var clm = hMap(clt, clb, 1);
        for (var i2 = 0; i2 < tl; ) {
          var r = clm[bits(dat, pos, clbmsk)];
          pos += r & 15;
          var s = r >> 4;
          if (s < 16) {
            ldt[i2++] = s;
          } else {
            var c = 0, n = 0;
            if (s == 16)
              n = 3 + bits(dat, pos, 3), pos += 2, c = ldt[i2 - 1];
            else if (s == 17)
              n = 3 + bits(dat, pos, 7), pos += 3;
            else if (s == 18)
              n = 11 + bits(dat, pos, 127), pos += 7;
            while (n--)
              ldt[i2++] = c;
          }
        }
        var lt = ldt.subarray(0, hLit), dt = ldt.subarray(hLit);
        lbt = max(lt);
        dbt = max(dt);
        lm = hMap(lt, lbt, 1);
        dm = hMap(dt, dbt, 1);
      } else
        err(1);
      if (pos > tbts) {
        if (noSt)
          err(0);
        break;
      }
    }
    if (resize)
      cbuf(bt + 131072);
    var lms = (1 << lbt) - 1, dms = (1 << dbt) - 1;
    var lpos = pos;
    for (; ; lpos = pos) {
      var c = lm[bits16(dat, pos) & lms], sym = c >> 4;
      pos += c & 15;
      if (pos > tbts) {
        if (noSt)
          err(0);
        break;
      }
      if (!c)
        err(2);
      if (sym < 256)
        buf[bt++] = sym;
      else if (sym == 256) {
        lpos = pos, lm = null;
        break;
      } else {
        var add = sym - 254;
        if (sym > 264) {
          var i2 = sym - 257, b = fleb[i2];
          add = bits(dat, pos, (1 << b) - 1) + fl[i2];
          pos += b;
        }
        var d = dm[bits16(dat, pos) & dms], dsym = d >> 4;
        if (!d)
          err(3);
        pos += d & 15;
        var dt = fd[dsym];
        if (dsym > 3) {
          var b = fdeb[dsym];
          dt += bits16(dat, pos) & (1 << b) - 1, pos += b;
        }
        if (pos > tbts) {
          if (noSt)
            err(0);
          break;
        }
        if (resize)
          cbuf(bt + 131072);
        var end = bt + add;
        if (bt < dt) {
          var shift = dl - dt, dend = Math.min(dt, end);
          if (shift + bt < 0)
            err(3);
          for (; bt < dend; ++bt)
            buf[bt] = dict[shift + bt];
        }
        for (; bt < end; ++bt)
          buf[bt] = buf[bt - dt];
      }
    }
    st.l = lm, st.p = lpos, st.b = bt, st.f = final;
    if (lm)
      final = 1, st.m = lbt, st.d = dm, st.n = dbt;
  } while (!final);
  return bt != buf.length && noBuf ? slc(buf, 0, bt) : buf.subarray(0, bt);
};
var et = /* @__PURE__ */ new u8(0);
var b2 = function(d, b) {
  return d[b] | d[b + 1] << 8;
};
var b4 = function(d, b) {
  return (d[b] | d[b + 1] << 8 | d[b + 2] << 16 | d[b + 3] << 24) >>> 0;
};
var b8 = function(d, b) {
  return b4(d, b) + b4(d, b + 4) * 4294967296;
};
function inflateSync(data, opts) {
  return inflt(data, { i: 2 }, opts && opts.out, opts && opts.dictionary);
}
var td = typeof TextDecoder != "undefined" && /* @__PURE__ */ new TextDecoder();
var tds = 0;
try {
  td.decode(et, { stream: true });
  tds = 1;
} catch (e) {
}
var dutf8 = function(d) {
  for (var r = "", i2 = 0; ; ) {
    var c = d[i2++];
    var eb = (c > 127) + (c > 223) + (c > 239);
    if (i2 + eb > d.length)
      return { s: r, r: slc(d, i2 - 1) };
    if (!eb)
      r += String.fromCharCode(c);
    else if (eb == 3) {
      c = ((c & 15) << 18 | (d[i2++] & 63) << 12 | (d[i2++] & 63) << 6 | d[i2++] & 63) - 65536, r += String.fromCharCode(55296 | c >> 10, 56320 | c & 1023);
    } else if (eb & 1)
      r += String.fromCharCode((c & 31) << 6 | d[i2++] & 63);
    else
      r += String.fromCharCode((c & 15) << 12 | (d[i2++] & 63) << 6 | d[i2++] & 63);
  }
};
function strFromU8(dat, latin1) {
  if (latin1) {
    var r = "";
    for (var i2 = 0; i2 < dat.length; i2 += 16384)
      r += String.fromCharCode.apply(null, dat.subarray(i2, i2 + 16384));
    return r;
  } else if (td) {
    return td.decode(dat);
  } else {
    var _a2 = dutf8(dat), s = _a2.s, r = _a2.r;
    if (r.length)
      err(8);
    return s;
  }
}
var slzh = function(d, b) {
  return b + 30 + b2(d, b + 26) + b2(d, b + 28);
};
var zh = function(d, b, z) {
  var fnl = b2(d, b + 28), efl = b2(d, b + 30), fn = strFromU8(d.subarray(b + 46, b + 46 + fnl), !(b2(d, b + 8) & 2048)), es = b + 46 + fnl;
  var _a2 = z64hs(d, es, efl, z, b4(d, b + 20), b4(d, b + 24), b4(d, b + 42)), sc = _a2[0], su = _a2[1], off = _a2[2];
  return [b2(d, b + 10), sc, su, fn, es + efl + b2(d, b + 32), off];
};
var z64hs = function(d, b, l, z, sc, su, off) {
  var nsc = sc == 4294967295, nsu = su == 4294967295, noff = off == 4294967295, e = b + l;
  var nf = nsc + nsu + noff;
  if (z && nf) {
    for (; b + 4 < e; b += 4 + b2(d, b + 2)) {
      if (b2(d, b) == 1) {
        return [
          nsc ? b8(d, b + 4 + 8 * nsu) : sc,
          nsu ? b8(d, b + 4) : su,
          noff ? b8(d, b + 4 + 8 * (nsu + nsc)) : off,
          1
        ];
      }
    }
    if (z < 2)
      err(13);
  }
  return [sc, su, off, 0];
};
function unzipSync(data, opts) {
  var files = {};
  var e = data.length - 22;
  for (; b4(data, e) != 101010256; --e) {
    if (!e || data.length - e > 65558)
      err(13);
  }
  ;
  var c = b2(data, e + 8);
  if (!c)
    return {};
  var o = b4(data, e + 16);
  var z = b4(data, e - 20) == 117853008;
  if (z) {
    var ze = b4(data, e - 12);
    z = b4(data, ze) == 101075792;
    if (z) {
      c = b4(data, ze + 32);
      o = b4(data, ze + 48);
    }
  }
  var fltr = opts && opts.filter;
  for (var i2 = 0; i2 < c; ++i2) {
    var _a2 = zh(data, o, z), c_2 = _a2[0], sc = _a2[1], su = _a2[2], fn = _a2[3], no = _a2[4], off = _a2[5], b = slzh(data, off);
    o = no;
    if (!fltr || fltr({
      name: fn,
      size: sc,
      originalSize: su,
      compression: c_2
    })) {
      if (!c_2)
        files[fn] = slc(data, b, b + sc);
      else if (c_2 == 8)
        files[fn] = inflateSync(data.subarray(b, b + sc), { out: new u8(su) });
      else
        err(14, "unknown compression type " + c_2);
    }
  }
  return files;
}
var API = "https://api.github.com";
var EVENT_TYPE = "gpt_task";
var RESULT_FILENAME = "execution_result.json";
var EXECUTION_STATUS_PENDING = "PENDING";
var EXECUTION_STATUS_PASS = "PASS";
var EXECUTION_STATUS_FAIL = "FAIL";
var EXECUTION_STATUS_BLOCKED = "BLOCKED";
var EXECUTION_STATUSES = [
  EXECUTION_STATUS_PENDING,
  EXECUTION_STATUS_PASS,
  EXECUTION_STATUS_FAIL,
  EXECUTION_STATUS_BLOCKED
];
var TERMINAL_EXECUTION_STATUSES = [
  EXECUTION_STATUS_PASS,
  EXECUTION_STATUS_FAIL,
  EXECUTION_STATUS_BLOCKED
];
var REVIEW_VERDICTS_CANONICAL = [
  EXECUTION_STATUS_PASS,
  EXECUTION_STATUS_FAIL,
  EXECUTION_STATUS_BLOCKED
];
var WORKFLOW_CONCLUSION_STATUS = {
  success: "PASS",
  failure: "FAIL",
  startup_failure: "FAIL",
  error: "FAIL",
  cancelled: "BLOCKED",
  canceled: "BLOCKED",
  timed_out: "BLOCKED",
  action_required: "BLOCKED",
  stale: "BLOCKED",
  neutral: "BLOCKED",
  skipped: "BLOCKED"
};
var SELF_REPORTED_FAILURE_STATUSES = [
  "failure",
  "failed",
  "fail",
  "error",
  "errored",
  "timed_out"
];
var SELF_REPORTED_SUCCESS_STATUSES = [
  "success",
  "succeeded",
  "pass",
  "passed",
  "ok",
  "complete",
  "completed"
];
var PROTOCOL_VERSION = "2025-06-18";
var EVENTS_PROTOCOL_VERSION = "2026-07-28";
var EVENTS_KV_PREFIX = "events-subscription::";
var EVENTS_DELIVERY_PREFIX = "events-delivered::";
var EVENT_MAX_BYTES = 262144;
var EVENT_DEFAULT_TTL_MS = 7 * 24 * 60 * 60 * 1000;
var EVENT_MIN_TTL_MS = 60 * 1000;
var EVENT_MAX_ATTEMPTS = 4;
var EVENT_RETRY_BASE_MS = 25;
var EVENT_CALLBACK_TIMEOUT_MS = 10000;
var EVENT_SIGNATURE_TOLERANCE_SEC = 300;
var TASK_COMPLETED_EVENT = "task.completed";
var EVENTS = [
  {
    name: TASK_COMPLETED_EVENT,
    description: "A Personal AI execution task reached a terminal result. Read the full evidence with the existing get_task_result(task_id) tool; the payload carries identifiers only.",
    delivery: ["webhook"],
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string", description: "Only deliver completions for this task id." },
        project_id: { type: "string", description: "Only deliver completions for this project lineage." }
      },
      additionalProperties: false
    },
    payloadSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        status: { type: "string" },
        project_id: { type: "string" }
      },
      required: ["task_id", "status"],
      additionalProperties: false
    }
  }
];
function canonicalJson(value) {
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonicalJson(value[k])).join(",") + "}";
  }
  return JSON.stringify(value);
}
function bytesToB64(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}
function decodeWhsec(secret) {
  if (typeof secret !== "string" || !secret.startsWith("whsec_")) return null;
  const raw = secret.slice(6);
  if (!raw || !/^[A-Za-z0-9+/=_-]+$/.test(raw)) return null;
  try {
    const b64 = raw.replace(/-/g, "+").replace(/_/g, "/");
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i2 = 0; i2 < bin.length; i2++) bytes[i2] = bin.charCodeAt(i2);
    if (bytes.length < 24 || bytes.length > 64) return null;
    return bytes;
  } catch {
    return null;
  }
}
async function standardWebhookSignature(secret, msgId, timestamp, body) {
  const raw = decodeWhsec(secret);
  if (!raw) throw mcpError(-32602, "INVALID_PARAMS", "invalid_signing_secret");
  const key = await crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${msgId}.${timestamp}.${body}`));
  return "v1," + bytesToB64(new Uint8Array(sig));
}
async function verifyStandardWebhookSignature(secret, msgId, timestamp, body, header, toleranceSec) {
  if (typeof header !== "string") return false;
  const ts = Number(timestamp);
  if (!Number.isFinite(ts)) return false;
  const tolerance = toleranceSec == null ? EVENT_SIGNATURE_TOLERANCE_SEC : Number(toleranceSec);
  if (Math.abs(nowSec() - ts) > tolerance) return false;
  const expected = await standardWebhookSignature(secret, msgId, String(timestamp), body);
  const expectedSig = expected.slice(expected.indexOf(",") + 1);
  for (const part of header.split(/\s+/).filter(Boolean)) {
    const comma = part.indexOf(",");
    const version = comma === -1 ? "" : part.slice(0, comma);
    const sig = comma === -1 ? part : part.slice(comma + 1);
    if (version === "v1" && timingSafeEqual(sig, expectedSig)) return true;
  }
  return false;
}
function mcpError(code, message, data) {
  const err = new Error(message);
  let payload = null;
  if (typeof data === "string") payload = { reason: data };
  else if (data && typeof data === "object") payload = data;
  err.mcpError = { code, message, data: payload };
  return err;
}
function callbackUrlError(reason) {
  return mcpError(-32015, "CallbackEndpointError", reason);
}
function validateCallbackUrl(rawUrl) {
  let parsed;
  try {
    parsed = new URL(String(rawUrl || ""));
  } catch {
    throw callbackUrlError("invalid_url");
  }
  if (parsed.protocol !== "https:") throw callbackUrlError("insecure_scheme");
  if (parsed.username || parsed.password) throw callbackUrlError("userinfo_not_allowed");
  const host = parsed.hostname.toLowerCase();
  if (host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local") || host.endsWith(".internal")) {
    throw callbackUrlError("non_public_address");
  }
  const ipv4 = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (ipv4) {
    const parts = ipv4.slice(1).map(Number);
    if (parts.some((n) => n > 255)) throw callbackUrlError("invalid_url");
    const [a, b] = parts;
    if (a === 0 || a === 10 || a === 127 || a >= 224 || a === 169 && b === 254 || a === 172 && b >= 16 && b <= 31 || a === 192 && b === 168 || a === 100 && b >= 64 && b <= 127 || a === 198 && (b === 18 || b === 19)) {
      throw callbackUrlError("non_public_address");
    }
  } else if (host.includes(":")) {
    const h = host.replace(/^\[|\]$/g, "");
    if (h === "::" || h === "::1" || h.startsWith("fe80") || h.startsWith("fc") || h.startsWith("fd") || h.startsWith("ff")) {
      throw callbackUrlError("non_public_address");
    }
  }
  return parsed;
}
async function eventFetch(url, options) {
  validateCallbackUrl(url);
  if (typeof fetch !== "function") throw callbackUrlError("network_unavailable");
  return fetch(url, options);
}
function utf8ByteLength(text) {
  return new TextEncoder().encode(text).length;
}
function authPrincipal(auth) {
  if (auth && auth.payload && auth.payload.sub) return String(auth.payload.sub);
  return "owner";
}
function validateEventArgs(args, schema) {
  const value = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  const props = schema.properties || {};
  for (const key of Object.keys(value)) {
    if (!props[key]) return { ok: false, reason: `unexpected_argument:${key}` };
    const type = props[key].type;
    if (type && typeof value[key] !== type) return { ok: false, reason: `invalid_argument:${key}` };
  }
  for (const required of schema.required || []) {
    if (value[required] === void 0 || value[required] === null || value[required] === "") {
      return { ok: false, reason: `missing_argument:${required}` };
    }
  }
  return { ok: true, value };
}
function resolveTtlMs(requested) {
  if (requested === null || requested === void 0) return EVENT_DEFAULT_TTL_MS;
  const value = Number(requested);
  if (!Number.isFinite(value) || value < 0) return EVENT_DEFAULT_TTL_MS;
  return Math.max(EVENT_MIN_TTL_MS, Math.min(value, EVENT_DEFAULT_TTL_MS));
}
function newEventId() {
  if (crypto.randomUUID) return "evt_" + crypto.randomUUID().replace(/-/g, "");
  return "evt_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
}
function newChallenge() {
  if (crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
async function deterministicSubscriptionId(principal, url, name, args) {
  const fingerprint = `${principal}
${url}
${name}
${canonicalJson(args || {})}`;
  return "sub_" + (await sha256Hex(fingerprint)).slice(0, 32);
}
function listEvents() {
  return { events: EVENTS, nextCursor: null, truncated: false };
}
async function listSubscriptions(env) {
  if (!env.TASK_REGISTRY || typeof env.TASK_REGISTRY.list !== "function") return [];
  const listed = await env.TASK_REGISTRY.list({ prefix: EVENTS_KV_PREFIX });
  const subscriptions = [];
  for (const key of listed.keys || []) {
    const sub = await env.TASK_REGISTRY.get(key.name, "json");
    if (sub) subscriptions.push(sub);
  }
  return subscriptions;
}
function matchEventFilter(args, data) {
  const filter = args && typeof args === "object" ? args : {};
  for (const key of Object.keys(filter)) {
    if (filter[key] === void 0 || filter[key] === null) continue;
    if (String(data[key]) !== String(filter[key])) return false;
  }
  return true;
}
function isSubscriptionExpired(sub, nowMs) {
  if (!sub || !sub.refreshBefore) return false;
  const expiry = Date.parse(sub.refreshBefore);
  return Number.isFinite(expiry) && expiry <= nowMs;
}
async function verifyCallbackEndpoint(sub) {
  const challenge = newChallenge();
  const msgId = "msg_verification_" + challenge.slice(0, 16);
  const timestamp = String(nowSec());
  const body = JSON.stringify({ type: "verification", challenge });
  let response;
  try {
    const signature = await standardWebhookSignature(sub.secret, msgId, timestamp, body);
    response = await eventFetch(sub.url, {
      method: "POST",
      redirect: "error",
      signal: typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(EVENT_CALLBACK_TIMEOUT_MS) : void 0,
      headers: {
        "Content-Type": "application/json",
        "webhook-id": msgId,
        "webhook-timestamp": timestamp,
        "webhook-signature": signature,
        "X-MCP-Subscription-Id": sub.id
      },
      body
    });
  } catch (err) {
    return { ok: false, reason: err && err.mcpError && err.mcpError.data ? err.mcpError.data.reason : "timeout" };
  }
  if (!response || response.status < 200 || response.status >= 300) return { ok: false, reason: "challenge_failed" };
  let echoed = null;
  try {
    echoed = await response.json();
  } catch {
    echoed = null;
  }
  if (!echoed || typeof echoed.challenge !== "string" || !timingSafeEqual(echoed.challenge, challenge)) {
    return { ok: false, reason: "challenge_failed" };
  }
  return { ok: true, reason: null };
}
async function handleEventsSubscribe(env, auth, params) {
  if (!env.TASK_REGISTRY) throw mcpError(-32000, "UNSUPPORTED", "TASK_REGISTRY_UNAVAILABLE");
  const name = String(params.name || "");
  const definition = EVENTS.find((event) => event.name === name);
  if (!definition) throw mcpError(-32602, "INVALID_PARAMS", `unknown event: ${name}`);
  const validated = validateEventArgs(params.arguments || {}, definition.inputSchema);
  if (!validated.ok) throw mcpError(-32602, "INVALID_PARAMS", validated.reason);
  const delivery = params.delivery && typeof params.delivery === "object" ? params.delivery : {};
  const mode = String(delivery.mode || "webhook");
  if (mode !== "webhook") throw mcpError(-32602, "INVALID_PARAMS", "unsupported_delivery_mode");
  const url = validateCallbackUrl(delivery.url).toString();
  if (decodeWhsec(delivery.secret) === null) throw mcpError(-32602, "INVALID_PARAMS", "invalid_signing_secret");
  const principal = authPrincipal(auth);
  const id = await deterministicSubscriptionId(principal, url, name, validated.value);
  const key = EVENTS_KV_PREFIX + id;
  let existing = null;
  try {
    existing = await env.TASK_REGISTRY.get(key, "json");
  } catch {
    existing = null;
  }
  const verified = await verifyCallbackEndpoint({ id, url, secret: delivery.secret });
  if (!verified.ok) throw mcpError(-32015, "CallbackEndpointError", verified.reason || "challenge_failed");
  const now = /* @__PURE__ */ new Date();
  const ttlMs = resolveTtlMs(params.ttlMs);
  const refreshBefore = ttlMs === null ? null : new Date(now.getTime() + ttlMs).toISOString();
  const secretRotated = Boolean(existing && existing.delivery && existing.delivery.secret && existing.delivery.secret !== delivery.secret);
  const record = {
    id,
    principal,
    name,
    arguments: validated.value,
    delivery: { mode: "webhook", url, secret: delivery.secret },
    created_at: existing && existing.created_at ? existing.created_at : now.toISOString(),
    updated_at: now.toISOString(),
    refreshBefore,
    ttlMs,
    verified_at: now.toISOString(),
    cursor: null,
    previous_secret: secretRotated ? existing.delivery.secret : null,
    previous_secret_expires_at: secretRotated ? new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString() : null
  };
  await env.TASK_REGISTRY.put(key, JSON.stringify(record), { metadata: { name, principal } });
  return { id, refreshBefore, cursor: null, truncated: false, secret_rotated: secretRotated };
}
async function handleEventsUnsubscribe(env, auth, params) {
  if (!env.TASK_REGISTRY) throw mcpError(-32000, "UNSUPPORTED", "TASK_REGISTRY_UNAVAILABLE");
  const name = String(params.name || "");
  const definition = EVENTS.find((event) => event.name === name);
  if (!definition) throw mcpError(-32602, "INVALID_PARAMS", `unknown event: ${name}`);
  const validated = validateEventArgs(params.arguments || {}, definition.inputSchema);
  if (!validated.ok) throw mcpError(-32602, "INVALID_PARAMS", validated.reason);
  const delivery = params.delivery && typeof params.delivery === "object" ? params.delivery : {};
  const url = validateCallbackUrl(delivery.url).toString();
  const principal = authPrincipal(auth);
  const id = await deterministicSubscriptionId(principal, url, name, validated.value);
  const key = EVENTS_KV_PREFIX + id;
  let existing = null;
  try {
    existing = await env.TASK_REGISTRY.get(key, "json");
  } catch {
    existing = null;
  }
  if (existing && existing.principal === principal && typeof env.TASK_REGISTRY.delete === "function") {
    try {
      await env.TASK_REGISTRY.delete(key);
    } catch {
    }
  }
  return {};
}
function retryDelayMs(attempt, options) {
  const base = options && options.retryBaseMs != null ? options.retryBaseMs : EVENT_RETRY_BASE_MS;
  return base * Math.pow(2, Math.max(0, attempt - 1));
}
async function sleepMs(ms, options) {
  if (options && typeof options.sleep === "function") return options.sleep(ms);
  if (!ms || ms <= 0) return;
  return new Promise((resolve) => setTimeout(resolve, ms));
}
async function sendEventToSubscription(env, sub, event, options) {
  const opts = options || {};
  const maxAttempts = Math.max(1, Number(opts.maxAttempts) || EVENT_MAX_ATTEMPTS);
  const body = JSON.stringify(event);
  if (utf8ByteLength(body) > EVENT_MAX_BYTES) throw callbackUrlError("payload_too_large");
  const attempts = [];
  const secrets = [sub.delivery && sub.delivery.secret ? sub.delivery.secret : sub.secret];
  const previous = sub.previous_secret || sub.delivery && sub.delivery.previous_secret;
  if (previous && (!sub.previous_secret_expires_at || Date.parse(sub.previous_secret_expires_at) > Date.now())) secrets.push(previous);
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const signedAt = opts.now ? new Date(opts.now) : /* @__PURE__ */ new Date();
    const timestamp = String(Math.floor(signedAt.getTime() / 1e3));
    const signatures = [];
    for (const secret of secrets) signatures.push(await standardWebhookSignature(secret, event.eventId, timestamp, body));
    let response = null;
    try {
      response = await eventFetch(sub.delivery.url, {
        method: "POST",
        redirect: "error",
        signal: typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(EVENT_CALLBACK_TIMEOUT_MS) : void 0,
        headers: {
          "Content-Type": "application/json",
          "webhook-id": event.eventId,
          "webhook-timestamp": timestamp,
          "webhook-signature": signatures.join(" "),
          "X-MCP-Subscription-Id": sub.id
        },
        body
      });
    } catch (err) {
      attempts.push({ attempt, status: null, error: "network_error" });
      if (attempt < maxAttempts) await sleepMs(retryDelayMs(attempt, opts), opts);
      continue;
    }
    const status = response ? response.status : null;
    attempts.push({ attempt, status });
    if (status != null && status >= 200 && status < 300) return { accepted: true, status, attempts };
    if (status === 410 || status === 413) return { accepted: false, status, attempts, retryable: false };
    if (attempt < maxAttempts) await sleepMs(retryDelayMs(attempt, opts), opts);
  }
  const last = attempts[attempts.length - 1] || {};
  return { accepted: false, status: last.status == null ? null : last.status, attempts, retryable: true };
}
async function readDeliveryMarker(env, subscriptionId, eventId) {
  if (!env.TASK_REGISTRY || typeof env.TASK_REGISTRY.get !== "function") return null;
  try {
    return await env.TASK_REGISTRY.get(EVENTS_DELIVERY_PREFIX + subscriptionId + "::" + eventId, "text");
  } catch {
    return null;
  }
}
async function writeDeliveryMarker(env, subscriptionId, eventId) {
  if (!env.TASK_REGISTRY || typeof env.TASK_REGISTRY.put !== "function") return;
  try {
    await env.TASK_REGISTRY.put(EVENTS_DELIVERY_PREFIX + subscriptionId + "::" + eventId, "1", { expirationTtl: 86400 });
  } catch {
  }
}
async function emitTaskCompleted(env, input, options) {
  const opts = options || {};
  if (!env || !env.TASK_REGISTRY) return { eventId: null, delivered: [], skipped: [], reason: "TASK_REGISTRY_UNAVAILABLE" };
  const data = {
    task_id: String(input && input.task_id ? input.task_id : ""),
    status: String(input && input.status ? input.status : "")
  };
  if (input && input.project_id) data.project_id = String(input.project_id);
  if (!data.task_id || !data.status) return { eventId: null, delivered: [], skipped: [], reason: "INVALID_EVENT_DATA" };
  const event = {
    eventId: input.event_id ? String(input.event_id) : newEventId(),
    name: TASK_COMPLETED_EVENT,
    timestamp: new Date(opts.now ? opts.now : Date.now()).toISOString(),
    data,
    cursor: null
  };
  const nowMs = opts.now ? new Date(opts.now).getTime() : Date.now();
  const subscriptions = await listSubscriptions(env);
  const delivered = [];
  const skipped = [];
  for (const sub of subscriptions) {
    if (!sub || sub.name !== event.name) continue;
    if (isSubscriptionExpired(sub, nowMs)) {
      skipped.push({ id: sub.id, reason: "expired" });
      continue;
    }
    if (!matchEventFilter(sub.arguments, event.data)) {
      skipped.push({ id: sub.id, reason: "filter_mismatch" });
      continue;
    }
    if (await readDeliveryMarker(env, sub.id, event.eventId)) {
      skipped.push({ id: sub.id, reason: "duplicate" });
      continue;
    }
    const result = await sendEventToSubscription(env, sub, event, opts);
    if (result.accepted) {
      await writeDeliveryMarker(env, sub.id, event.eventId);
      delivered.push({ id: sub.id, status: result.status, attempts: result.attempts.length });
    } else {
      skipped.push({ id: sub.id, reason: "delivery_failed", status: result.status });
    }
  }
  return { eventId: event.eventId, delivered, skipped };
}
var ACCESS_TTL = 3600;
var REFRESH_TTL = 60 * 60 * 24 * 30;
var CODE_TTL = 300;
var SCOPE = "mcp";
var ASSET_READ_SCOPE = "asset.read";
var ASSET_TYPES = /* @__PURE__ */ new Set(["KNOWLEDGE", "SKILL", "REALITY", "DECISION"]);
var ASSET_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
var ASSET_SUBTYPE_SCHEMA = { "wechat-conversation-snapshot-v0.1": "wechat_conversation_snapshot" };
var CHATGPT_REDIRECT = "https://chatgpt.com/connector_platform_oauth_redirect";
var CHATGPT_REDIRECT_PREFIX = "https://chatgpt.com/connector/oauth/";
var ALLOWLIST = ["hello.py", "test_hello.py"];
var FORBIDDEN_PREFIXES = [".github/workflows/"];
var FORBIDDEN_SUBSTRINGS = ["secret", "token", "credential", ".env", ".pem", ".key"];
var READONLY_MODES = /* @__PURE__ */ new Set(["readonly", "read_only", "read-only"]);
var WRITE_MODES = /* @__PURE__ */ new Set(["write", "readwrite", "read_write", "read-write"]);
function resolveMode(raw) {
  if (raw === void 0 || raw === null || String(raw).trim() === "") return "write";
  const mode = String(raw).trim().toLowerCase();
  if (READONLY_MODES.has(mode)) return "readonly";
  if (WRITE_MODES.has(mode)) return "write";
  return null;
}
function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, Mcp-Session-Id, Accept",
    "Access-Control-Max-Age": "86400"
  };
}
function json(body, status, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...extra }
  });
}
function originOf(request) {
  return new URL(request.url).origin;
}
function bytesToB64url(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlEncode(str) {
  return bytesToB64url(new TextEncoder().encode(str));
}
function b64urlDecode(str) {
  const pad = str.length % 4 === 0 ? "" : "=".repeat(4 - str.length % 4);
  const b64 = str.replace(/-/g, "+").replace(/_/g, "/") + pad;
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i2 = 0; i2 < bin.length; i2++) bytes[i2] = bin.charCodeAt(i2);
  return new TextDecoder().decode(bytes);
}
async function hmacKey(secret) {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"]
  );
}
async function signPayload(payload, secret) {
  const body = b64urlEncode(JSON.stringify(payload));
  const key = await hmacKey(secret);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  return `${body}.${bytesToB64url(new Uint8Array(sig))}`;
}
async function verifyPayload(token, secret) {
  if (typeof token !== "string" || !token.includes(".")) return null;
  const [body, sig] = token.split(".");
  try {
    const key = await hmacKey(secret);
    const ok = await crypto.subtle.verify(
      "HMAC",
      key,
      Uint8Array.from(atob(sig.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0)),
      new TextEncoder().encode(body)
    );
    if (!ok) return null;
    const payload = JSON.parse(b64urlDecode(body));
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1e3)) return null;
    return payload;
  } catch {
    return null;
  }
}
async function sha256B64url(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return bytesToB64url(new Uint8Array(digest));
}
function timingSafeEqual(a, b) {
  const ab = new TextEncoder().encode(a);
  const bb = new TextEncoder().encode(b);
  if (ab.length !== bb.length) return false;
  let diff = 0;
  for (let i2 = 0; i2 < ab.length; i2++) diff |= ab[i2] ^ bb[i2];
  return diff === 0;
}
function nowSec() {
  return Math.floor(Date.now() / 1e3);
}
function normalizeScopes(value) {
  if (typeof value !== 'string' || !value || value.length>128 || !/^[a-z.]+(?: [a-z.]+)*$/.test(value)) return [];
  const scopes=[...new Set(value.split(' '))];
  if(scopes.some(scope=>![SCOPE,ASSET_READ_SCOPE,TASK_READ_SCOPE].includes(scope)))return [];
  if(scopes.includes(TASK_READ_SCOPE)&&scopes.length!==1)return [];
  return scopes;
}
function scopeString(value) {
  const scopes=normalizeScopes(value);
  if(!scopes.length)throw Error('INVALID_SCOPE');
  return scopes.join(' ');
}
function validGrantScope(payload,form) {
  const original=normalizeScopes(payload?.scope);
  if(!original.length||original.includes(TASK_READ_SCOPE)&&payload.task_project!==TASK_READ_PROJECT)return null;
  const requested=form.has('scope')?normalizeScopes(form.get('scope')):original;
  if(!requested.length||requested.some(s=>!original.includes(s)))return null;
  return requested.join(' ');
}
function hasReadScope(auth) {
  return Boolean(auth && auth.scopes && (auth.scopes.includes(ASSET_READ_SCOPE) || auth.scopes.includes(SCOPE)));
}
function hasWriteScope(auth) {
  return Boolean(auth && auth.scopes && auth.scopes.includes(SCOPE));
}
function protectedResourceMetadata(origin) {
  return {
    resource: origin,
    authorization_servers: [origin],
    scopes_supported: [SCOPE, ASSET_READ_SCOPE, TASK_READ_SCOPE],
    bearer_methods_supported: ["header"],
    resource_documentation: `${origin}/`
  };
}
function authorizationServerMetadata(origin) {
  return {
    issuer: origin,
    authorization_endpoint: `${origin}/authorize`,
    token_endpoint: `${origin}/token`,
    registration_endpoint: `${origin}/register`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code", "refresh_token"],
    code_challenge_methods_supported: ["S256"],
    token_endpoint_auth_methods_supported: ["none"],
    scopes_supported: [SCOPE, ASSET_READ_SCOPE, TASK_READ_SCOPE],
    authorization_response_iss_parameter_supported: false
  };
}
async function registerClient(request, env, origin) {
  let body = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  const redirectUris = Array.isArray(body.redirect_uris) ? body.redirect_uris.map(String) : [];
  const clientId = await signPayload(
    { kind: "client", redirect_uris: redirectUris, exp: nowSec() + 60 * 60 * 24 * 365 },
    env.OAUTH_SIGNING_KEY
  );
  return json(
    {
      client_id: clientId,
      client_id_issued_at: nowSec(),
      redirect_uris: redirectUris,
      token_endpoint_auth_method: "none",
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"]
    },
    201
  );
}
async function resolveRedirectUris(clientId, env) {
  if (!clientId) return [];
  if (clientId.startsWith("https://")) {
    try {
      const res = await fetch(clientId, { headers: { "User-Agent": "personal-ai-execution-mcp/0.1" } });
      if (!res.ok) return [];
      const doc = await res.json();
      return Array.isArray(doc.redirect_uris) ? doc.redirect_uris.map(String) : [];
    } catch {
      return [];
    }
  }
  const payload = await verifyPayload(clientId, env.OAUTH_SIGNING_KEY);
  return payload && Array.isArray(payload.redirect_uris) ? payload.redirect_uris : [];
}
function redirectAllowed(registered, redirectUri) {
  if (!redirectUri) return false;
  if (redirectUri === CHATGPT_REDIRECT || redirectUri.startsWith(CHATGPT_REDIRECT_PREFIX)) return true;
  return registered.includes(redirectUri);
}
function consentPage(params, error) {
  const hidden = Object.entries(params).map(([k, v]) => `<input type="hidden" name="${k}" value="${String(v).replace(/"/g, "&quot;")}">`).join("");
  const message = error ? `<p style="color:#b00">${error}</p>` : "";
  return `<!doctype html><html><head><meta charset="utf-8"><title>Authorize Personal AI Execution</title></head>
<body style="font-family:system-ui;max-width:520px;margin:48px auto">
<h2>Authorize <em>Personal AI Execution</em></h2>
${normalizeScopes(params.scope).includes(TASK_READ_SCOPE)?'<p>Scope: <code>task.read</code>. Fixed project: <code>cloud-assets-activation</code>.</p><p>Only <code>list_pending_results</code> and <code>get_task_result</code> are allowed. No registry synchronization writes; no dispatch, retry, asset or Canonical writes.</p>':'<p>This grants the requesting MCP client access to <code>submit_task</code> and <code>get_task_result</code>.</p>'}
${message}
<form method="post" action="/authorize">
${hidden}
<label>Owner password<br><input type="password" name="password" autocomplete="current-password" style="width:100%"></label>
<p><button type="submit" style="padding:8px 16px">Authorize</button></p>
</form>
</body></html>`;
}
async function authorizeGet(request, env) {
  const url = new URL(request.url);
  const p = Object.fromEntries(url.searchParams);
  if (!normalizeScopes(p.scope).length) return json({error:"invalid_scope"},400);
  if (p.response_type !== "code") return json({ error: "unsupported_response_type" }, 400);
  if (p.code_challenge_method && p.code_challenge_method !== "S256") {
    return json({ error: "invalid_request", error_description: "PKCE S256 required" }, 400);
  }
  if (!p.code_challenge) return json({ error: "invalid_request", error_description: "code_challenge required" }, 400);
  const registered = await resolveRedirectUris(p.client_id, env);
  if (!redirectAllowed(registered, p.redirect_uri)) {
    return json({ error: "invalid_request", error_description: "redirect_uri not allowed" }, 400);
  }
  return new Response(consentPage(p), { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } });
}
async function authorizePost(request, env) {
  const form = await request.formData();
  const p = Object.fromEntries(form.entries());
  if (!normalizeScopes(p.scope).length) return json({error:"invalid_scope"},400);
  const registered = await resolveRedirectUris(p.client_id, env);
  if (!redirectAllowed(registered, p.redirect_uri)) {
    return json({ error: "invalid_request", error_description: "redirect_uri not allowed" }, 400);
  }
  if (!env.OWNER_PASSWORD || !timingSafeEqual(String(p.password || ""), env.OWNER_PASSWORD)) {
    return new Response(consentPage(p, "Incorrect owner password."), {
      status: 401,
      headers: { "Content-Type": "text/html; charset=utf-8" }
    });
  }
  const code = await signPayload(
    {
      kind: "code",
      client_id: p.client_id,
      redirect_uri: p.redirect_uri,
      code_challenge: p.code_challenge,
      scope: scopeString(p.scope),
      ...(normalizeScopes(p.scope).includes(TASK_READ_SCOPE)?{task_project:TASK_READ_PROJECT}:{}),
      exp: nowSec() + CODE_TTL
    },
    env.OAUTH_SIGNING_KEY
  );
  const target = new URL(p.redirect_uri);
  target.searchParams.set("code", code);
  if (p.state) target.searchParams.set("state", p.state);
  return Response.redirect(target.toString(), 302);
}
async function tokenEndpoint(request, env) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ error: "invalid_request" }, 400);
  }
  const grantType = String(form.get("grant_type") || "");
  if (grantType === "authorization_code") {
    const payload = await verifyPayload(String(form.get("code") || ""), env.OAUTH_SIGNING_KEY);
    if (!payload || payload.kind !== "code") return json({ error: "invalid_grant" }, 400);
    if (payload.redirect_uri !== String(form.get("redirect_uri") || "")) {
      return json({ error: "invalid_grant", error_description: "redirect_uri mismatch" }, 400);
    }
    const verifier = String(form.get("code_verifier") || "");
    if (!verifier) return json({ error: "invalid_grant", error_description: "code_verifier required" }, 400);
    const challenge = await sha256B64url(verifier);
    if (challenge !== payload.code_challenge) {
      return json({ error: "invalid_grant", error_description: "PKCE verification failed" }, 400);
    }
    const scope=validGrantScope(payload,form);
    if(!scope)return json({error:"invalid_scope"},400);
    return json(await issueTokens(env, scope));
  }
  if (grantType === "refresh_token") {
    const payload = await verifyPayload(String(form.get("refresh_token") || ""), env.OAUTH_SIGNING_KEY);
    if (!payload || payload.kind !== "refresh") return json({ error: "invalid_grant" }, 400);
    const scope=validGrantScope(payload,form);
    if(!scope)return json({error:"invalid_scope"},400);
    return json(await issueTokens(env, scope));
  }
  return json({ error: "unsupported_grant_type" }, 400);
}
async function issueTokens(env, scope) {
  scope = scopeString(scope);
  const access = await signPayload(
    { kind: "access", sub: "owner", scope, ...(scope===TASK_READ_SCOPE?{task_project:TASK_READ_PROJECT}:{}), aud: "mcp", exp: nowSec() + ACCESS_TTL },
    env.OAUTH_SIGNING_KEY
  );
  const refresh = await signPayload(
    { kind: "refresh", sub: "owner", scope, ...(scope===TASK_READ_SCOPE?{task_project:TASK_READ_PROJECT}:{}), exp: nowSec() + REFRESH_TTL },
    env.OAUTH_SIGNING_KEY
  );
  return {
    access_token: access,
    token_type: "Bearer",
    expires_in: ACCESS_TTL,
    refresh_token: refresh,
    scope
  };
}
async function mcpAuthorized(request, env) {
  const header = request.headers.get("Authorization") || "";
  if (!header.startsWith("Bearer ")) return false;
  const presented = header.slice("Bearer ".length).trim();
  if (env.MCP_AUTH_TOKEN && timingSafeEqual(presented, env.MCP_AUTH_TOKEN)) {
    return { scopes: [SCOPE, ASSET_READ_SCOPE], kind: "static" };
  }
  const payload = await verifyPayload(presented, env.OAUTH_SIGNING_KEY);
  if(!payload||payload.kind!=="access")return false;
  const scopes=normalizeScopes(payload.scope);
  if(!scopes.length||scopes.includes(TASK_READ_SCOPE)&&payload.task_project!==TASK_READ_PROJECT)return false;
  return {scopes,kind:"oauth",payload};
}
function unauthorized(origin) {
  return json(
    { error: "UNAUTHORIZED" },
    401,
    {
      "WWW-Authenticate": `Bearer resource_metadata="${origin}/.well-known/oauth-protected-resource", scope="${SCOPE} ${ASSET_READ_SCOPE}"`
    }
  );
}
function newTaskId() {
  return `cf-${crypto.randomUUID().replace(/-/g, "").slice(0, 12)}`;
}
function buildContract(goal, instructions, acceptance, expectedFiles, lineage, mode) {
  const resolvedMode = resolveMode(mode);
  const expected_files = expectedFiles === void 0 ? resolvedMode === "readonly" ? [] : [...ALLOWLIST] : Array.isArray(expectedFiles) ? expectedFiles.map(String) : [];
  const contract = {
    task_id: newTaskId(),
    goal: String(goal ?? ""),
    instructions: Array.isArray(instructions) ? instructions.map(String) : [],
    risk_level: "LOW",
    mode: resolvedMode === null ? String(mode) : resolvedMode,
    expected_files,
    acceptance: Array.isArray(acceptance) ? acceptance.map(String) : []
  };
  const source = lineage && typeof lineage === "object" ? lineage : {};
  if (source.project_id) contract.project_id = String(source.project_id);
  if (source.root_task_id) contract.root_task_id = String(source.root_task_id);
  if (source.parent_task_id) contract.parent_task_id = String(source.parent_task_id);
  return contract;
}
function validateContract(contract) {
  const errors = [];
  if (!contract.goal.trim()) errors.push("goal must be non-empty");
  if (!contract.instructions.length) errors.push("instructions must be a non-empty list");
  if (!contract.acceptance.length) errors.push("acceptance must be a non-empty list");
  if (resolveMode(contract.mode) === null) {
    errors.push(`mode not acceptable: ${contract.mode} (allowed: readonly, write)`);
  }
  for (const path of contract.expected_files) {
    if (typeof path !== "string" || !path.trim()) {
      errors.push(`expected_file must be a non-empty string: ${path}`);
      continue;
    }
    const normalized = path.replace(/\\/g, "/");
    const low = String(path).toLowerCase();
    const absolute = normalized.startsWith("/") || normalized.startsWith("//") || /^[A-Za-z]:\//.test(normalized);
    const parent = normalized.split("/").includes("..");
    if (absolute || parent) {
      errors.push(`unsafe expected_file path: ${path}`);
    } else if (FORBIDDEN_PREFIXES.some((p) => low.startsWith(p)) || FORBIDDEN_SUBSTRINGS.some((s) => low.includes(s))) {
      errors.push(`forbidden expected_file: ${path}`);
    }
  }
  return errors;
}
function ghHeaders(env) {
  return {
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "personal-ai-execution-mcp-worker/0.1",
    "Content-Type": "application/json"
  };
}
function safeGithubResponseBody(raw) {
  return String(raw || "")
    .slice(0, 512)
    .replace(/gh[pousr]_[A-Za-z0-9_\-]+/gi, "[REDACTED]")
    .replace(/github_pat_[A-Za-z0-9_]+/gi, "[REDACTED]")
    .replace(/("?(?:token|secret|password|authorization)"?\s*:\s*")([^"\\]*)"/gi, "$1[REDACTED]\"");
}
async function dispatchTask(env, contract) {
  const res = await fetch(`${API}/repos/${env.GITHUB_REPO}/dispatches`, {
    method: "POST",
    headers: ghHeaders(env),
    body: JSON.stringify({ event_type: EVENT_TYPE, client_payload: { task: contract } })
  });
  const bodySafe = safeGithubResponseBody(await res.text());
  return {
    ok: res.ok,
    status: res.status,
    requestId: res.headers.get("x-github-request-id") || null,
    bodySafe
  };
}
var DISPATCH_MARKER_PREFIX = "dispatch:";
var DISPATCH_STATE_PENDING = "PENDING";
var DISPATCH_STATE_DISPATCHED = "DISPATCHED";
var DISPATCH_STATE_FAILED = "FAILED";
var DISPATCH_REASON_DISPATCHED = "DISPATCHED";
var DISPATCH_REASON_ALREADY = "ALREADY_DISPATCHED";
var DISPATCH_REASON_VERDICT = "VERDICT_NOT_PASS";
var DISPATCH_REASON_NO_CHILD = "NO_APPROVED_NEXT_TASK";
var DISPATCH_REASON_INVALID = "INVALID_APPROVED_NEXT_TASK";
var DISPATCH_REASON_UNAVAILABLE = "DISPATCH_MARKER_UNAVAILABLE";
var DISPATCH_REASON_FAILED = "DISPATCH_FAILED";
function dispatchMarkerKey(parentTaskId) {
  return `${DISPATCH_MARKER_PREFIX}${parentTaskId}`;
}
async function readDispatchMarker(env, parentTaskId) {
  if (!env.ASSET_DB) return null;
  try {
    return await env.ASSET_DB.prepare(
      "SELECT dispatch_key, parent_task_id, review_verdict, review_timestamp, child_task_id, dispatch_state, dispatch_status, github_http_status, github_request_id, dispatched_at FROM task_dispatch_markers WHERE dispatch_key = ?"
    ).bind(dispatchMarkerKey(parentTaskId)).first();
  } catch {
    return null;
  }
}
async function claimDispatchMarker(env, parentTaskId, childTaskId, verdict, reviewTimestamp, reviewNote, options) {
  if (!env.ASSET_DB) return { status: "unavailable", claimed: false };
  const opts = options && typeof options === "object" ? options : {};
  const claimKey = opts.claimKey ? String(opts.claimKey) : dispatchMarkerKey(parentTaskId);
  const markerParent = opts.markerParent != null ? String(opts.markerParent) : parentTaskId;
  const nowIso = (/* @__PURE__ */ new Date()).toISOString();
  try {
    const res = await env.ASSET_DB.prepare(
      "INSERT OR IGNORE INTO task_dispatch_markers (dispatch_key, parent_task_id, review_verdict, review_timestamp, review_note, child_task_id, dispatch_state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
      claimKey,
      markerParent,
      verdict,
      reviewTimestamp ?? null,
      reviewNote ?? null,
      childTaskId,
      DISPATCH_STATE_PENDING,
      nowIso,
      nowIso
    ).run();
    const changes = res && res.meta ? Number(res.meta.changes) || 0 : 0;
    return changes > 0 ? { status: "claimed", claimed: true, claim_key: claimKey } : { status: "duplicate", claimed: false, claim_key: claimKey };
  } catch {
    return { status: "unavailable", claimed: false, claim_key: claimKey };
  }
}
async function finalizeDispatchMarker(env, parentTaskId, patch, options) {
  if (!env.ASSET_DB) return;
  const opts = options && typeof options === "object" ? options : {};
  const key = opts.claimKey ? String(opts.claimKey) : dispatchMarkerKey(parentTaskId);
  const nowIso = (/* @__PURE__ */ new Date()).toISOString();
  try {
    await env.ASSET_DB.prepare(
      "UPDATE task_dispatch_markers SET dispatch_state = ?, dispatch_status = ?, github_http_status = ?, github_request_id = ?, dispatched_at = ?, updated_at = ? WHERE dispatch_key = ?"
    ).bind(
      patch.state,
      patch.dispatchStatus ?? null,
      patch.httpStatus ?? null,
      patch.requestId ?? null,
      patch.dispatchedAt ?? null,
      nowIso,
      key
    ).run();
  } catch {
  }
}
function buildApprovedChildContract(approvedNextTask, parentLineage) {
  const inherited = parentLineage && typeof parentLineage === "object" ? parentLineage : {};
  const contract = buildContract(
    approvedNextTask.goal,
    approvedNextTask.instructions,
    approvedNextTask.acceptance,
    approvedNextTask.expected_files,
    {
      project_id: approvedNextTask.project_id || inherited.project_id,
      root_task_id: approvedNextTask.root_task_id || inherited.root_task_id,
      parent_task_id: inherited.parent_task_id
    },
    approvedNextTask.mode
  );
  return { contract, errors: validateContract(contract) };
}
async function dispatchApprovedChild(env, parentTaskId, verdict, approvedNextTask, reviewTimestamp, reviewNote) {
  const base = {
    parent_task_id: String(parentTaskId),
    attempted: false,
    dispatched: false,
    idempotent: false,
    child_task_id: null,
    dispatch_state: null,
    reason: null
  };
  if (verdict !== EXECUTION_STATUS_PASS) return { ...base, reason: DISPATCH_REASON_VERDICT };
  if (approvedNextTask == null) return { ...base, reason: DISPATCH_REASON_NO_CHILD };
  if (typeof approvedNextTask !== "object" || Array.isArray(approvedNextTask)) {
    return {
      ...base,
      attempted: true,
      reason: DISPATCH_REASON_INVALID,
      errors: ["approved_next_task must be an object"]
    };
  }
  const existing = await readDispatchMarker(env, parentTaskId);
  if (existing && existing.child_task_id) {
    return {
      ...base,
      idempotent: true,
      child_task_id: existing.child_task_id,
      dispatch_state: existing.dispatch_state ?? null,
      reason: DISPATCH_REASON_ALREADY
    };
  }
  let parentRecord = null;
  try {
    parentRecord = await readTask(env, parentTaskId);
  } catch {
    parentRecord = null;
  }
  const parentLineage = {
    project_id: parentRecord && parentRecord.project_id ? String(parentRecord.project_id) : null,
    root_task_id: parentRecord && parentRecord.root_task_id ? String(parentRecord.root_task_id) : String(parentTaskId),
    parent_task_id: String(parentTaskId)
  };
  const { contract, errors } = buildApprovedChildContract(approvedNextTask, parentLineage);
  if (errors.length) {
    return { ...base, attempted: true, reason: DISPATCH_REASON_INVALID, errors };
  }
  const claim = await claimDispatchMarker(
    env,
    parentTaskId,
    contract.task_id,
    verdict,
    reviewTimestamp,
    reviewNote
  );
  if (claim.status === "unavailable") {
    return { ...base, attempted: true, reason: DISPATCH_REASON_UNAVAILABLE };
  }
  if (!claim.claimed) {
    const marker2 = await readDispatchMarker(env, parentTaskId);
    return {
      ...base,
      idempotent: true,
      child_task_id: marker2 && marker2.child_task_id ? marker2.child_task_id : null,
      dispatch_state: marker2 && marker2.dispatch_state ? marker2.dispatch_state : null,
      reason: DISPATCH_REASON_ALREADY
    };
  }
  let dispatch;
  try {
    dispatch = await dispatchTask(env, contract);
  } catch (err2) {
    await finalizeDispatchMarker(env, parentTaskId, {
      state: DISPATCH_STATE_FAILED,
      dispatchStatus: "network_error"
    });
    return {
      ...base,
      attempted: true,
      child_task_id: contract.task_id,
      dispatch_state: DISPATCH_STATE_FAILED,
      reason: DISPATCH_REASON_FAILED,
      error: safeGithubResponseBody(err2?.message || "request failed")
    };
  }
  if (!dispatch.ok) {
    await finalizeDispatchMarker(env, parentTaskId, {
      state: DISPATCH_STATE_FAILED,
      dispatchStatus: "github_rejected",
      httpStatus: dispatch.status,
      requestId: dispatch.requestId
    });
    return {
      ...base,
      attempted: true,
      child_task_id: contract.task_id,
      dispatch_state: DISPATCH_STATE_FAILED,
      reason: DISPATCH_REASON_FAILED,
      dispatch_status: "github_rejected",
      github_http_status: dispatch.status,
      github_request_id: dispatch.requestId
    };
  }
  const dispatchedAt = (/* @__PURE__ */ new Date()).toISOString();
  await finalizeDispatchMarker(env, parentTaskId, {
    state: DISPATCH_STATE_DISPATCHED,
    dispatchStatus: "accepted",
    httpStatus: dispatch.status,
    requestId: dispatch.requestId,
    dispatchedAt
  });
  try {
    await recordTask(env, contract);
  } catch {
  }
  return {
    ...base,
    attempted: true,
    dispatched: true,
    child_task_id: contract.task_id,
    dispatch_state: DISPATCH_STATE_DISPATCHED,
    reason: DISPATCH_REASON_DISPATCHED,
    dispatch_status: "accepted",
    github_http_status: dispatch.status,
    github_request_id: dispatch.requestId,
    dispatched_at: dispatchedAt
  };
}
function reviewDispatchAudit(taskId, verdict, timestamp, dispatch) {
  return {
    parent_task_id: String(taskId),
    child_task_id: dispatch.child_task_id ?? null,
    dispatch_state: dispatch.dispatch_state ?? null,
    dispatch_status: dispatch.dispatch_status ?? null,
    dispatched_at: dispatch.dispatched_at ?? null,
    review_verdict: verdict,
    review_timestamp: timestamp ?? null,
    reason: dispatch.reason ?? null
  };
}
async function findArtifact(env, name, readOptions = {}) {
  const res = await fetch(
    `${API}/repos/${env.GITHUB_REPO}/actions/artifacts?name=${encodeURIComponent(name)}`,
    { ...readOptions, headers: ghHeaders(env) }
  );
  if (readOptions.redirect === "manual") rejectObservationRedirect(res, "artifacts");
  if (!res.ok) throw new Error(`GitHub artifact lookup failed HTTP ${res.status}`);
  const payload = await res.json();
  const artifacts = payload.artifacts || [];
  if (!artifacts.length) return null;
  artifacts.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  return artifacts[0];
}
async function downloadArtifactJson(env, artifactId) {
  const url = `${API}/repos/${env.GITHUB_REPO}/actions/artifacts/${artifactId}/zip`;
  let res = await fetch(url, { headers: ghHeaders(env), redirect: "manual" });
  if (res.status >= 300 && res.status < 400) {
    const location = res.headers.get("location");
    if (!location) throw new Error("artifact redirect without location");
    res = await fetch(location);
  }
  if (!res.ok) throw new Error(`artifact download failed HTTP ${res.status}`);
  const files = unzipSync(new Uint8Array(await res.arrayBuffer()));
  const name = Object.keys(files).find((n) => n.endsWith(RESULT_FILENAME));
  if (!name) throw new Error(`${RESULT_FILENAME} not found in artifact`);
  return JSON.parse(new TextDecoder().decode(files[name]));
}
async function getArtifactWorkflowRun(env, artifact, readOptions = {}) {
  const runId = artifact?.workflow_run?.id;
  if (!runId) throw new Error("artifact missing workflow_run.id");
  const res = await fetch(`${API}/repos/${env.GITHUB_REPO}/actions/runs/${runId}`, {
    ...readOptions, headers: ghHeaders(env)
  });
  if (readOptions.redirect === "manual") rejectObservationRedirect(res, "run_detail");
  if (!res.ok) throw new Error(`GitHub workflow lookup failed HTTP ${res.status}`);
  const run = await res.json();
  return {
    id: run.id,
    repository_full_name: run.repository?.full_name ?? null,
    display_title: run.display_title ?? null,
    event: run.event ?? null,
    path: run.path ?? null,
    run_number: run.run_number ?? null,
    run_attempt: run.run_attempt ?? null,
    run_started_at: run.run_started_at ?? null,
    status: run.status,
    conclusion: run.conclusion,
    html_url: run.html_url,
    created_at: run.created_at ?? null,
    updated_at: run.updated_at ?? null,
    completed_at: run.completed_at ?? null
  };
}
function canonicalWorkflowStatus(conclusion) {
  const key = String(conclusion == null ? "" : conclusion).trim().toLowerCase();
  return WORKFLOW_CONCLUSION_STATUS[key] || EXECUTION_STATUS_BLOCKED;
}
function normalizeSelfReportedStatus(rawStatus) {
  const text = String(rawStatus == null ? "" : rawStatus).trim().toLowerCase();
  if (SELF_REPORTED_FAILURE_STATUSES.includes(text)) return EXECUTION_STATUS_FAIL;
  if (SELF_REPORTED_SUCCESS_STATUSES.includes(text)) return EXECUTION_STATUS_PASS;
  return EXECUTION_STATUS_BLOCKED;
}
function verifiedResultStatus(rawStatus, run) {
  if (!run || run.status !== "completed") return EXECUTION_STATUS_PENDING;
  const canonical = canonicalWorkflowStatus(run.conclusion);
  if (canonical !== EXECUTION_STATUS_PASS) return canonical;
  const self = normalizeSelfReportedStatus(rawStatus);
  return self === EXECUTION_STATUS_FAIL ? EXECUTION_STATUS_FAIL : EXECUTION_STATUS_PASS;
}
var REG_PREFIX = "task:";
var BLOCKED_AFTER_MS = 15 * 60 * 1e3;
var TASK_DISPATCH_CONFIRM_GRACE_MS = 15 * 60 * 1e3;
var TASK_DISPATCH_MAX_ATTEMPTS = 3;
var TASK_DISPATCH_STATE_PENDING = "PENDING_DISPATCH";
var TASK_DISPATCH_STATE_ACCEPTED = "ACCEPTED";
var TASK_DISPATCH_STATE_CONFIRMED = "CONFIRMED";
var TASK_DISPATCH_STATE_UNCONFIRMED = "UNCONFIRMED";
var TASK_DISPATCH_STATE_RETRY = "RETRY_DISPATCHED";
var TASK_DISPATCH_STATE_FAILED = "DISPATCH_FAILED";
var TASK_DISPATCH_STATE_EXHAUSTED = "EXHAUSTED";
var TASK_DISPATCH_ACTION_WAIT = "wait";
var TASK_DISPATCH_ACTION_RETRY = "retry";
var TASK_DISPATCH_ACTION_INSPECT = "inspect";
var TASK_DISPATCH_ACTION_NONE = "none";
var RETRY_DISPATCH_PREFIX = "retry:";
var RETRY_DISPATCH_VERDICT = "RETRY";
var DISPATCH_REASON_REDISPATCHED = "REDISPATCHED";
var DISPATCH_REASON_RETRY_ALREADY = "ALREADY_RETRIED";
var DISPATCH_REASON_AUTHORITATIVE = "AUTHORITATIVE_RESULT";
var DISPATCH_REASON_NOT_RETRYABLE = "NOT_RETRYABLE";
var DISPATCH_REASON_NO_CONTRACT = "NO_DISPATCH_CONTRACT";
var DISPATCH_REASON_RETRY_UNAVAILABLE = "RETRY_CLAIM_UNAVAILABLE";
var DISPATCH_REASON_RETRY_FAILED = "RETRY_DISPATCH_FAILED";
function retryDispatchKey(taskId, attempt) {
  return `${RETRY_DISPATCH_PREFIX}${taskId}:${attempt}`;
}
var LINEAGE_PROJECT_FIELD = "project_id";
var LINEAGE_ROOT_FIELD = "root_task_id";
var LINEAGE_PARENT_FIELD = "parent_task_id";
var LINEAGE_KIND_PROJECT = "project";
var LINEAGE_KIND_ROOT = "root";
var MAX_LINEAGE_WALK = 64;
function taskDispatchConfirmed(options) {
  const opts = options && typeof options === "object" ? options : {};
  if (opts.hasArtifact === true) return true;
  if (opts.runConclusion != null && String(opts.runConclusion).trim()) return true;
  const status = opts.runStatus == null ? "" : String(opts.runStatus).trim().toLowerCase();
  return status === "in_progress" || status === "completed";
}
function classifyTaskDispatchLiveness(task, options) {
  const opts = options && typeof options === "object" ? options : {};
  const now = opts.now == null ? Date.now() : Number(opts.now);
  const graceMs = opts.graceMs == null ? TASK_DISPATCH_CONFIRM_GRACE_MS : Number(opts.graceMs);
  const maxAttempts = Math.max(1, Number(opts.maxAttempts) || TASK_DISPATCH_MAX_ATTEMPTS);
  const taskId = String(task && task.task_id || "");
  const attempt = Math.max(1, Number(task && task.dispatch_attempt) || 1);
  const acceptedRaw = task && (task.dispatch_accepted_at || task.dispatch_at || task.created_at || task.updated_at);
  const acceptedAt = acceptedRaw ? Date.parse(acceptedRaw) || null : null;
  const deadlineRaw = task && task.dispatch_confirm_deadline;
  const deadline = deadlineRaw ? Date.parse(deadlineRaw) || null : acceptedAt == null ? null : acceptedAt + graceMs;
  const leaseExpired = deadline != null && now > deadline;
  const confirmed = taskDispatchConfirmed(opts);
  const authoritative = Boolean(task && (task.reviewed === true || task.terminal === true || task.result_available === true));
  const recordedState = String(task && task.dispatch_state || "").trim().toUpperCase();
  let state;
  let action;
  let retryable;
  let reason;
  if (authoritative) {
    state = TASK_DISPATCH_STATE_CONFIRMED;
    action = TASK_DISPATCH_ACTION_NONE;
    retryable = false;
    reason = "authoritative result or review already recorded";
  } else if (recordedState === TASK_DISPATCH_STATE_FAILED) {
    retryable = attempt < maxAttempts;
    state = TASK_DISPATCH_STATE_FAILED;
    action = retryable ? TASK_DISPATCH_ACTION_RETRY : TASK_DISPATCH_ACTION_INSPECT;
    reason = "dispatch HTTP call failed" + (retryable ? "; retryable" : "; attempts exhausted");
  } else if (confirmed) {
    state = TASK_DISPATCH_STATE_CONFIRMED;
    const runStatus = opts.runStatus == null ? "" : String(opts.runStatus).trim().toLowerCase();
    action = runStatus === "in_progress" ? TASK_DISPATCH_ACTION_WAIT : TASK_DISPATCH_ACTION_NONE;
    retryable = false;
    reason = "job-start evidence observed; awaiting authoritative result";
  } else if (!leaseExpired) {
    state = recordedState === TASK_DISPATCH_STATE_PENDING || recordedState === TASK_DISPATCH_STATE_RETRY ? recordedState : TASK_DISPATCH_STATE_ACCEPTED;
    action = TASK_DISPATCH_ACTION_WAIT;
    retryable = false;
    reason = "dispatch lease active; awaiting job start";
  } else if (attempt >= maxAttempts) {
    state = TASK_DISPATCH_STATE_EXHAUSTED;
    action = TASK_DISPATCH_ACTION_INSPECT;
    retryable = false;
    reason = "dispatch accepted but no job started before the deadline and attempts are exhausted";
  } else {
    state = TASK_DISPATCH_STATE_UNCONFIRMED;
    action = TASK_DISPATCH_ACTION_RETRY;
    retryable = true;
    reason = "dispatch accepted but no job started before the deadline (queued run cancelled before job start)";
  }
  return {
    task_id: taskId,
    dispatch_state: state,
    recommended_action: action,
    retryable,
    confirmed,
    lease_expired: leaseExpired,
    attempt,
    max_attempts: maxAttempts,
    dispatch_accepted_at: acceptedAt == null ? null : new Date(acceptedAt).toISOString(),
    dispatch_confirm_deadline: deadline == null ? null : new Date(deadline).toISOString(),
    reason
  };
}
function planTaskDispatchRetry(task, options) {
  const report = classifyTaskDispatchLiveness(task, options);
  const taskId = String(task && task.task_id || "");
  const attempt = Number(report.attempt) || 1;
  const shouldRetry = report.recommended_action === TASK_DISPATCH_ACTION_RETRY;
  const nextAttempt = shouldRetry ? attempt + 1 : attempt;
  return {
    task_id: taskId,
    should_retry: shouldRetry,
    same_task_id: true,
    next_attempt: nextAttempt,
    idempotency_key: shouldRetry && taskId ? `retry:${taskId}:${nextAttempt}` : null,
    retry_claim_scope: shouldRetry ? "task_dispatch_markers" : null,
    dispatch_state: report.dispatch_state,
    recommended_action: report.recommended_action,
    retryable: report.retryable,
    reason: report.reason
  };
}
function regKey(taskId) {
  return `${REG_PREFIX}${taskId}`;
}
function resolveLineage(record, index) {
  const taskId = String(record && record.task_id || "");
  const projectId = record && record.project_id;
  if (projectId) return { kind: LINEAGE_KIND_PROJECT, key: String(projectId) };
  const root = record && record.root_task_id;
  if (root) return { kind: LINEAGE_KIND_ROOT, key: String(root) };
  let parent = record && record.parent_task_id;
  const seen = /* @__PURE__ */ new Set();
  while (parent && !seen.has(String(parent)) && seen.size < MAX_LINEAGE_WALK) {
    seen.add(String(parent));
    const ancestor = index.get(String(parent));
    if (!ancestor) break;
    if (ancestor.root_task_id) return { kind: LINEAGE_KIND_ROOT, key: String(ancestor.root_task_id) };
    if (ancestor.project_id) return { kind: LINEAGE_KIND_PROJECT, key: String(ancestor.project_id) };
    parent = ancestor.parent_task_id;
  }
  return { kind: LINEAGE_KIND_ROOT, key: taskId };
}
function lineageInScope(record, scope, index) {
  if (!scope) return true;
  const projectId = scope.project_id;
  const rootTaskId = scope.root_task_id;
  if (!projectId && !rootTaskId) return true;
  const resolved = resolveLineage(record, index);
  if (projectId) return resolved.kind === LINEAGE_KIND_PROJECT && resolved.key === String(projectId);
  return resolved.kind === LINEAGE_KIND_ROOT && resolved.key === String(rootTaskId);
}
function resolveLineageState(record, index, unresolved) {
  const taskId = String(record && record.task_id || "");
  const projectId = record && record.project_id;
  if (projectId) return { kind: LINEAGE_KIND_PROJECT, key: String(projectId), resolved: true };
  const root = record && record.root_task_id;
  if (root) return { kind: LINEAGE_KIND_ROOT, key: String(root), resolved: true };
  let parent = record && record.parent_task_id;
  const seen = /* @__PURE__ */ new Set();
  while (parent && !seen.has(String(parent)) && seen.size < MAX_LINEAGE_WALK) {
    seen.add(String(parent));
    if (unresolved && unresolved.has(String(parent))) {
      return { kind: null, key: null, resolved: false };
    }
    const ancestor = index.get(String(parent));
    if (!ancestor) break;
    if (ancestor.root_task_id) return { kind: LINEAGE_KIND_ROOT, key: String(ancestor.root_task_id), resolved: true };
    if (ancestor.project_id) return { kind: LINEAGE_KIND_PROJECT, key: String(ancestor.project_id), resolved: true };
    parent = ancestor.parent_task_id;
  }
  return { kind: LINEAGE_KIND_ROOT, key: taskId, resolved: true };
}
var LINEAGE_MEMBERSHIP_MATCH = "match";
var LINEAGE_MEMBERSHIP_NONMATCH = "nonmatch";
var LINEAGE_MEMBERSHIP_UNRESOLVED = "unresolved";
function classifyLineageMembership(record, scope, index, unresolved, taskId) {
  const id = String(taskId != null ? taskId : record && record.task_id || "");
  if (unresolved && unresolved.has(id)) return LINEAGE_MEMBERSHIP_UNRESOLVED;
  const state = resolveLineageState(record, index, unresolved);
  if (!state.resolved) return LINEAGE_MEMBERSHIP_UNRESOLVED;
  if (!scope) return LINEAGE_MEMBERSHIP_MATCH;
  const projectId = scope.project_id;
  const rootTaskId = scope.root_task_id;
  if (!projectId && !rootTaskId) return LINEAGE_MEMBERSHIP_MATCH;
  if (projectId) {
    return state.kind === LINEAGE_KIND_PROJECT && state.key === String(projectId) ? LINEAGE_MEMBERSHIP_MATCH : LINEAGE_MEMBERSHIP_NONMATCH;
  }
  return state.kind === LINEAGE_KIND_ROOT && state.key === String(rootTaskId) ? LINEAGE_MEMBERSHIP_MATCH : LINEAGE_MEMBERSHIP_NONMATCH;
}
var TASK_METADATA_MAX_BYTES = 1024;
var TASK_METADATA_STRING_LIMIT = 256;
var TASK_METADATA_LINEAGE_FIELDS = ["project_id", "root_task_id", "parent_task_id"];
var TASK_METADATA_LINEAGE_COMPLETE_FLAG = "lineage_in_metadata_complete";
var TASK_METADATA_CORE_FIELDS = [
  "status",
  "normalized_status",
  "execution_status",
  "terminal",
  "result_available",
  "reviewed",
  "review_verdict",
  "created_at",
  "updated_at",
  "dispatch_state",
  "dispatch_attempt"
];
var TASK_METADATA_FIELDS = [
  // execution state consumed by listing / pending-review reconciliation
  "status",
  "normalized_status",
  "execution_status",
  "workflow_conclusion",
  "workflow_verified",
  "terminal",
  "result_available",
  "synced",
  // review consumer (verdict + timestamps only; never the note payload)
  "reviewed",
  "verdict",
  "review_verdict",
  "review_state",
  "reviewed_at",
  // lineage consumed by the supervisor scope filter
  "project_id",
  "root_task_id",
  "parent_task_id",
  // liveness / dispatch lease consumed by the retry planner
  "dispatch_state",
  "dispatch_attempt",
  "dispatch_accepted_at",
  "dispatch_confirm_deadline",
  // bounded display / audit timestamps
  "title",
  "created_at",
  "updated_at",
  "completed_at"
];
function truncateUtf8Bytes(text, maxBytes) {
  if (typeof text !== "string") return text;
  const bytes = new TextEncoder().encode(text);
  if (maxBytes < 0 || bytes.length <= maxBytes) return text;
  let end = maxBytes;
  while (end > 0 && (bytes[end] & 192) === 128) end -= 1;
  return new TextDecoder().decode(bytes.subarray(0, end));
}
function metadataUtf8Bytes(metadata) {
  return utf8ByteLength(JSON.stringify(metadata));
}
function lineageFieldsAltered(original, candidate) {
  for (const key of TASK_METADATA_LINEAGE_FIELDS) {
    if (!(key in original)) continue;
    if (candidate[key] !== original[key]) return true;
  }
  return false;
}
function boundTaskMetadata(metadata, maxBytes) {
  if (metadataUtf8Bytes(metadata) <= maxBytes) return metadata;
  const limits = [128, 64, 32, 16, 8, 0];
  for (const limit of limits) {
    const next = {};
    for (const key of Object.keys(metadata)) {
      const value = metadata[key];
      next[key] = typeof value === "string" ? truncateUtf8Bytes(value, limit) : value;
    }
    next.metadata_bounded = true;
    next[TASK_METADATA_LINEAGE_COMPLETE_FLAG] = !lineageFieldsAltered(metadata, next);
    if (metadataUtf8Bytes(next) <= maxBytes) return next;
  }
  for (const limit of [32, 16, 8, 4, 2, 1, 0]) {
    const minimal = { metadata_bounded: true, [TASK_METADATA_LINEAGE_COMPLETE_FLAG]: false };
    for (const key of TASK_METADATA_CORE_FIELDS) {
      if (!(key in metadata)) continue;
      const value = metadata[key];
      minimal[key] = typeof value === "string" ? truncateUtf8Bytes(value, limit) : value;
    }
    if (metadataUtf8Bytes(minimal) <= maxBytes) return minimal;
  }
  return { metadata_bounded: true, [TASK_METADATA_LINEAGE_COMPLETE_FLAG]: false };
}
function metadataLineageComplete(record) {
  if (!record || typeof record !== "object") return true;
  if (record[TASK_METADATA_LINEAGE_COMPLETE_FLAG] === false) return false;
  if (record.metadata_bounded === true) return false;
  return true;
}
async function readTaskMetadataForLineage(env, task) {
  if (!metadataLineageComplete(task)) {
    try {
      const full = await readTask(env, task.task_id);
      if (full && typeof full === "object") return full;
    } catch {
    }
    return null;
  }
  return task;
}
function buildTaskMetadata(entry) {
  const source = entry && typeof entry === "object" && !Array.isArray(entry) ? entry : {};
  const reviewEvent = source.review_event;
  const eventNote = reviewEvent && typeof reviewEvent === "object" ? reviewEvent.note : void 0;
  const note = source.review_note;
  const metadata = {
    // Bounded, non-leaking presence flags: the full note/event stay in the JSON
    // value only, so the 1024-byte KV metadata bound can never be breached by a
    // long or multi-byte note.
    review_note_present: typeof note === "string" && note.length > 0 || typeof eventNote === "string" && eventNote.length > 0,
    review_event_present: Boolean(reviewEvent && typeof reviewEvent === "object")
  };
  for (const field of TASK_METADATA_FIELDS) {
    if (!(field in source)) continue;
    const value = source[field];
    if (value === null || typeof value === "number" || typeof value === "boolean") {
      metadata[field] = value;
    } else if (typeof value === "string") {
      metadata[field] = TASK_METADATA_LINEAGE_FIELDS.includes(field)
        ? value
        : truncateUtf8Bytes(value, TASK_METADATA_STRING_LIMIT);
    }
    // Objects/arrays (review_event, review_dispatch, dispatch_contract,
    // dispatch_events, unknown blobs) are intentionally excluded; the full
    // record is already persisted in the JSON value and read via readTask.
  }
  return boundTaskMetadata(metadata, TASK_METADATA_MAX_BYTES);
}
async function recordTask(env, contract, options) {
  if (!env.TASK_REGISTRY) return;
  const opts = options && typeof options === "object" ? options : {};
  const nowIso = (/* @__PURE__ */ new Date()).toISOString();
  const meta = {
    status: EXECUTION_STATUS_PENDING,
    normalized_status: null,
    execution_status: EXECUTION_STATUS_PENDING,
    terminal: false,
    workflow_conclusion: null,
    title: String(contract.goal || "").slice(0, 120),
    created_at: nowIso,
    updated_at: nowIso,
    result_available: false,
    reviewed: false,
    review_verdict: null,
    dispatch_state: opts.dispatchState || TASK_DISPATCH_STATE_ACCEPTED,
    dispatch_attempt: Math.max(1, Number(opts.dispatchAttempt) || 1),
    dispatch_accepted_at: nowIso,
    dispatch_confirm_deadline: new Date(Date.now() + TASK_DISPATCH_CONFIRM_GRACE_MS).toISOString()
  };
  if (contract.project_id) meta.project_id = String(contract.project_id);
  if (contract.root_task_id) meta.root_task_id = String(contract.root_task_id);
  if (contract.parent_task_id) meta.parent_task_id = String(contract.parent_task_id);
  await env.TASK_REGISTRY.put(regKey(contract.task_id), JSON.stringify({ task_id: contract.task_id, ...meta, dispatch_contract: contract }), {
    metadata: buildTaskMetadata(meta)
  });
}
async function listTasks(env) {
  if (!env.TASK_REGISTRY) return [];
  const listed = await env.TASK_REGISTRY.list({ prefix: REG_PREFIX });
  return listed.keys.map((k) => ({ task_id: k.name.slice(REG_PREFIX.length), ...k.metadata || {} }));
}
async function saveTask(env, entry) {
  if (!env.TASK_REGISTRY) return;
  const { task_id, ...rest } = entry;
  await env.TASK_REGISTRY.put(regKey(task_id), JSON.stringify(entry), {
    metadata: buildTaskMetadata(rest)
  });
}
async function updateDispatchLease(env, taskId, patch) {
  if (!env.TASK_REGISTRY) return null;
  let current = null;
  try {
    current = await readTask(env, taskId);
  } catch {
    current = null;
  }
  if (!current) return null;
  const lease = patch && typeof patch === "object" ? patch : {};
  const updated = {
    ...current,
    task_id: taskId,
    dispatch_state: lease.dispatchState ?? current.dispatch_state,
    dispatch_attempt: Math.max(1, Number(lease.dispatchAttempt) || Number(current.dispatch_attempt) || 1),
    dispatch_accepted_at: lease.acceptedAt ?? current.dispatch_accepted_at,
    dispatch_confirm_deadline: lease.deadline ?? current.dispatch_confirm_deadline,
    updated_at: (/* @__PURE__ */ new Date()).toISOString()
  };
  await saveTask(env, updated);
  return updated;
}
async function readTask(env, taskId) {
  if (!env.TASK_REGISTRY) return null;
  return env.TASK_REGISTRY.get(regKey(taskId), "json");
}
async function persistTerminalExecution(env, taskId, patch) {
  if (!env.TASK_REGISTRY) return;
  try {
    const current = await readTask(env, taskId) || { task_id: taskId };
    const updated = { ...current, ...patch, task_id: taskId };
    await saveTask(env, updated);
  } catch {
  }
}
async function listPendingResults(env, scope) {
  const tasks = await listTasks(env);
  const index = /* @__PURE__ */ new Map();
  for (const task of tasks) index.set(String(task.task_id), task);
  const lineageUnresolved = /* @__PURE__ */ new Set();
  for (const task of tasks) {
    if (metadataLineageComplete(task)) continue;
    const full = await readTaskMetadataForLineage(env, task);
    if (full) {
      index.set(String(task.task_id), { ...task, ...full, task_id: task.task_id });
    } else {
      lineageUnresolved.add(String(task.task_id));
    }
  }
  const now = Date.now();
  const pending = [];
  const pending_review = [];
  const failed = [];
  const blocked = [];
  const unconfirmed = [];
  const unresolved = [];
  let excluded_by_lineage = 0;
  for (const task of tasks) {
    const taskId = String(task.task_id);
    const record = index.get(taskId) || task;
    const membership = classifyLineageMembership(record, scope, index, lineageUnresolved, taskId);
    if (membership === LINEAGE_MEMBERSHIP_NONMATCH) {
      excluded_by_lineage += 1;
      continue;
    }
    if (membership === LINEAGE_MEMBERSHIP_UNRESOLVED) {
      // The identity (or an ancestor's identity) could not be read back. A
      // scope match can be neither confirmed nor refuted, and a bounded/compressed
      // identity must never be treated as the real id. Surface the task in a
      // dedicated, retryable bucket instead of a confirmed actionable list.
      unresolved.push({
        task_id: task.task_id,
        status: task.normalized_status || task.status || EXECUTION_STATUS_PENDING,
        normalized_status: task.normalized_status || task.status || EXECUTION_STATUS_PENDING,
        execution_status: task.execution_status || task.status || EXECUTION_STATUS_PENDING,
        terminal: task.terminal === true,
        title: task.title || "",
        updated_at: task.updated_at || task.created_at || "",
        result_available: Boolean(task.result_available),
        reviewed: task.reviewed === true,
        review_verdict: task.review_verdict ?? null,
        membership: LINEAGE_MEMBERSHIP_UNRESOLVED,
        identity_resolved: false,
        lineage: null,
        retryable: true,
        recommended_action: TASK_DISPATCH_ACTION_RETRY,
        reason: "LINEAGE_IDENTITY_UNRESOLVED"
      });
      continue;
    }
    let status = task.normalized_status || task.status || EXECUTION_STATUS_PENDING;
    let resultAvailable = Boolean(task.result_available);
    let updatedAt = task.updated_at || task.created_at || "";
    let completedAt = task.completed_at || "";
    let workflowConclusion = task.workflow_conclusion || null;
    const jobEvidence = { hasArtifact: false, runStatus: null, runConclusion: null };
    if (!resultAvailable || !task.workflow_verified) {
      try {
        const artifact = await findArtifact(env, `execution_result-${task.task_id}`);
        if (artifact) {
          const data = await downloadArtifactJson(env, artifact.id);
          const run = await getArtifactWorkflowRun(env, artifact);
          status = verifiedResultStatus(data.status, run);
          workflowConclusion = run.conclusion ?? null;
          resultAvailable = run.status === "completed";
          updatedAt = run.updated_at || updatedAt;
          completedAt = run.completed_at || (resultAvailable ? updatedAt : "");
          jobEvidence.hasArtifact = true;
          jobEvidence.runStatus = run.status ?? null;
          jobEvidence.runConclusion = run.conclusion ?? null;
        } else if (task.result_available) {
          status = EXECUTION_STATUS_PENDING;
          resultAvailable = false;
        }
      } catch {
        if (task.result_available && task.workflow_verified) {
          status = task.normalized_status || task.status || EXECUTION_STATUS_PENDING;
          resultAvailable = true;
        } else {
          status = task.result_available ? EXECUTION_STATUS_PENDING : task.status || EXECUTION_STATUS_PENDING;
          resultAvailable = false;
        }
      }
    }
    const terminal = resultAvailable && TERMINAL_EXECUTION_STATUSES.includes(status);
    const entry = {
      task_id: task.task_id,
      status,
      normalized_status: status,
      execution_status: status,
      workflow_conclusion: workflowConclusion,
      terminal,
      title: task.title || "",
      updated_at: updatedAt,
      completed_at: completedAt,
      result_available: resultAvailable,
      reviewed: task.reviewed === true,
      review_verdict: task.review_verdict ?? null,
      requires_review: resultAvailable && task.reviewed !== true,
      recommended_action: resultAvailable ? "review" : "wait"
    };
    entry.membership = LINEAGE_MEMBERSHIP_MATCH;
    entry.identity_resolved = true;
    if (record.project_id) entry.project_id = String(record.project_id);
    if (record.root_task_id) entry.root_task_id = String(record.root_task_id);
    if (record.parent_task_id) entry.parent_task_id = String(record.parent_task_id);
    entry.lineage = resolveLineage(record, index);
    if (resultAvailable && task.reviewed !== true) {
      pending.push(entry);
      pending_review.push(entry);
      if (status === EXECUTION_STATUS_FAIL) failed.push(entry);
    } else if (!resultAvailable) {
      const liveness = classifyTaskDispatchLiveness(task, {
        now,
        hasArtifact: jobEvidence.hasArtifact,
        runStatus: jobEvidence.runStatus,
        runConclusion: jobEvidence.runConclusion
      });
      entry.dispatch_state = liveness.dispatch_state;
      entry.dispatch_attempt = liveness.attempt;
      entry.dispatch_confirm_deadline = liveness.dispatch_confirm_deadline;
      entry.retryable = liveness.retryable;
      entry.recommended_action = liveness.recommended_action;
      if (liveness.recommended_action === TASK_DISPATCH_ACTION_RETRY) {
        unconfirmed.push(entry);
      } else {
        const created = Date.parse(task.created_at || "") || now;
        if (now - created > BLOCKED_AFTER_MS) {
          entry.recommended_action = "inspect";
          blocked.push(entry);
        }
      }
    }
    if (terminal) {
      await persistTerminalExecution(env, task.task_id, {
        status,
        normalized_status: status,
        execution_status: status,
        terminal: true,
        result_available: true,
        workflow_conclusion: workflowConclusion,
        workflow_verified: true,
        completed_at: completedAt || updatedAt || (/* @__PURE__ */ new Date()).toISOString(),
        synced: true,
        updated_at: updatedAt || (/* @__PURE__ */ new Date()).toISOString()
      });
    }
  }
  const report = {
    pending,
    pending_review,
    failed,
    blocked,
    unconfirmed,
    unresolved,
    counts: {
      pending: pending.length,
      pending_review: pending_review.length,
      failed: failed.length,
      blocked: blocked.length,
      unconfirmed: unconfirmed.length,
      unresolved: unresolved.length,
      total: tasks.length
    }
  };
  if (scope) {
    report.scope = scope;
    report.excluded_by_lineage = excluded_by_lineage;
    report.lineage_unresolved = lineageUnresolved.size;
  }
  return report;
}
var REVIEW_VERDICTS = ["PASS", "FAIL", "BLOCKED"];
async function toolMarkReviewed(env, args) {
  if (!env.TASK_REGISTRY) return { isError: true, text: "TASK_REGISTRY_UNAVAILABLE" };
  const taskId = String(args.task_id ?? "").trim();
  const verdict = String(args.verdict ?? "").trim().toUpperCase();
  const note = args.note == null ? null : String(args.note);
  const approvedNextTask = args.approved_next_task == null ? null : args.approved_next_task;
  if (!taskId) return { isError: true, text: "INVALID_INPUT: task_id required" };
  if (!REVIEW_VERDICTS.includes(verdict)) {
    return { isError: true, text: `INVALID_INPUT: verdict must be one of ${REVIEW_VERDICTS.join(", ")}` };
  }
  const task = await readTask(env, taskId);
  if (!task) return { isError: true, text: `UNKNOWN_TASK: ${taskId}` };
  if (task.reviewed === true) {
    const recorded = task.review_verdict ?? task.verdict;
    if (recorded === verdict) {
      const replayDispatch = await dispatchApprovedChild(
        env,
        taskId,
        verdict,
        approvedNextTask,
        task.reviewed_at ?? null,
        task.review_note ?? null
      );
      if (replayDispatch.child_task_id && !task.review_dispatch) {
        task.review_dispatch = reviewDispatchAudit(taskId, verdict, task.reviewed_at ?? null, replayDispatch);
        task.updated_at = (/* @__PURE__ */ new Date()).toISOString();
        await saveTask(env, task);
      }
      const result2 = {
        task_id: taskId,
        reviewed: true,
        verdict,
        review_verdict: verdict,
        execution_status: task.normalized_status ?? task.execution_status ?? task.status,
        review_event: task.review_event ?? null,
        child_dispatch: replayDispatch,
        idempotent: true
      };
      return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
    }
    return { isError: true, text: `REVIEW_ALREADY_RECORDED: ${recorded || "UNKNOWN"}` };
  }
  const executionStatus = String(
    task.normalized_status ?? task.execution_status ?? task.status ?? ""
  ).trim().toUpperCase();
  const terminal = task.terminal === true || (task.result_available === true && TERMINAL_EXECUTION_STATUSES.includes(executionStatus));
  if (!terminal || !TERMINAL_EXECUTION_STATUSES.includes(executionStatus)) {
    return { isError: true, text: `NOT_REVIEWABLE: NON_TERMINAL (${executionStatus || "UNKNOWN"})` };
  }
  if (task.result_available !== true) {
    return { isError: true, text: "NOT_REVIEWABLE: RESULT_UNAVAILABLE" };
  }
  const timestamp = (/* @__PURE__ */ new Date()).toISOString();
  const reviewEvent = {
    task_id: taskId,
    action: "review",
    verdict,
    timestamp,
    note,
    execution_status: executionStatus
  };
  const updated = {
    ...task,
    reviewed: true,
    verdict,
    review_verdict: verdict,
    reviewed_at: timestamp,
    review_note: note,
    review_event: reviewEvent,
    updated_at: timestamp
  };
  await saveTask(env, updated);
  const childDispatch = await dispatchApprovedChild(
    env,
    taskId,
    verdict,
    approvedNextTask,
    timestamp,
    note
  );
  if (childDispatch.child_task_id) {
    updated.review_dispatch = reviewDispatchAudit(taskId, verdict, timestamp, childDispatch);
    updated.updated_at = (/* @__PURE__ */ new Date()).toISOString();
    await saveTask(env, updated);
  }
  const result = {
    task_id: taskId,
    reviewed: true,
    verdict,
    review_verdict: verdict,
    execution_status: executionStatus,
    reviewed_at: timestamp,
    review_event: reviewEvent,
    child_dispatch: childDispatch,
    idempotent: false
  };
  return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
async function gatherDispatchEvidence(env, taskId) {
  const evidence = { hasArtifact: false, runStatus: null, runConclusion: null };
  try {
    const artifact = await findArtifact(env, `execution_result-${taskId}`);
    if (artifact) {
      evidence.hasArtifact = true;
      const run = await getArtifactWorkflowRun(env, artifact);
      evidence.runStatus = run.status ?? null;
      evidence.runConclusion = run.conclusion ?? null;
    }
  } catch {
  }
  return evidence;
}
async function toolPlanDispatchRetry(env, args) {
  if (!env.TASK_REGISTRY) return { isError: true, text: "TASK_REGISTRY_UNAVAILABLE" };
  const taskId = String(args.task_id ?? "").trim();
  if (!taskId) return { isError: true, text: "INVALID_INPUT: task_id required" };
  const task = await readTask(env, taskId);
  if (!task) return { isError: true, text: `UNKNOWN_TASK: ${taskId}` };
  const evidence = await gatherDispatchEvidence(env, taskId);
  const plan = planTaskDispatchRetry(task, evidence);
  return { isError: false, text: JSON.stringify(plan), structuredContent: plan };
}
async function retryDispatchTask(env, args) {
  const input = args && typeof args === "object" ? args : {};
  const taskId = String(input.task_id ?? "").trim();
  if (!taskId) return { isError: true, text: "INVALID_INPUT: task_id required" };
  if (!env.TASK_REGISTRY) return { isError: true, text: "TASK_REGISTRY_UNAVAILABLE" };
  const task = await readTask(env, taskId);
  if (!task) return { isError: true, text: `UNKNOWN_TASK: ${taskId}` };
  const authoritative = task.reviewed === true || task.terminal === true || task.result_available === true;
  if (authoritative) {
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: false,
      dispatch_state: TASK_DISPATCH_STATE_CONFIRMED,
      reason: DISPATCH_REASON_AUTHORITATIVE,
      execution_status: task.normalized_status ?? task.execution_status ?? task.status ?? null
    };
    return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
  }
  const evidence = await gatherDispatchEvidence(env, taskId);
  const plan = planTaskDispatchRetry(task, evidence);
  if (!plan.should_retry) {
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: false,
      dispatch_state: plan.dispatch_state,
      recommended_action: plan.recommended_action,
      reason: DISPATCH_REASON_NOT_RETRYABLE,
      plan
    };
    return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
  }
  const storedContract = task.dispatch_contract;
  if (storedContract == null || typeof storedContract !== "object" || Array.isArray(storedContract)) {
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: false,
      dispatch_state: plan.dispatch_state,
      recommended_action: plan.recommended_action,
      reason: DISPATCH_REASON_NO_CONTRACT,
      errors: ["stored dispatch contract unavailable; refusing to redispatch"]
    };
    return { isError: true, text: JSON.stringify(result2), structuredContent: result2 };
  }
  const contractErrors = validateContract(storedContract);
  if (contractErrors.length) {
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: false,
      dispatch_state: plan.dispatch_state,
      recommended_action: plan.recommended_action,
      reason: DISPATCH_REASON_NO_CONTRACT,
      errors: contractErrors
    };
    return { isError: true, text: JSON.stringify(result2), structuredContent: result2 };
  }
  const contract = { ...storedContract, task_id: taskId };
  const claimKey = plan.idempotency_key || retryDispatchKey(taskId, plan.next_attempt);
  const claim = await claimDispatchMarker(env, taskId, taskId, RETRY_DISPATCH_VERDICT, null, null, {
    claimKey,
    markerParent: claimKey
  });
  if (claim.status === "unavailable") {
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: false,
      dispatch_state: plan.dispatch_state,
      recommended_action: plan.recommended_action,
      reason: DISPATCH_REASON_RETRY_UNAVAILABLE,
      idempotency_key: plan.idempotency_key
    };
    return { isError: true, text: JSON.stringify(result2), structuredContent: result2 };
  }
  if (!claim.claimed) {
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: true,
      dispatch_state: plan.dispatch_state,
      recommended_action: plan.recommended_action,
      reason: DISPATCH_REASON_RETRY_ALREADY,
      idempotency_key: plan.idempotency_key,
      next_attempt: plan.next_attempt
    };
    return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
  }
  let dispatch;
  try {
    dispatch = await dispatchTask(env, contract);
  } catch (err2) {
    await finalizeDispatchMarker(env, taskId, {
      state: DISPATCH_STATE_FAILED,
      dispatchStatus: "network_error"
    }, { claimKey: plan.idempotency_key });
    await updateDispatchLease(env, taskId, {
      dispatchState: TASK_DISPATCH_STATE_FAILED,
      dispatchAttempt: plan.next_attempt,
      acceptedAt: (/* @__PURE__ */ new Date()).toISOString(),
      deadline: new Date(Date.now() + TASK_DISPATCH_CONFIRM_GRACE_MS).toISOString()
    });
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: false,
      dispatch_state: TASK_DISPATCH_STATE_FAILED,
      reason: DISPATCH_REASON_RETRY_FAILED,
      idempotency_key: plan.idempotency_key,
      next_attempt: plan.next_attempt,
      dispatch_status: "network_error",
      error: safeGithubResponseBody(err2?.message || "request failed")
    };
    return { isError: true, text: JSON.stringify(result2), structuredContent: result2 };
  }
  if (!dispatch.ok) {
    await finalizeDispatchMarker(env, taskId, {
      state: DISPATCH_STATE_FAILED,
      dispatchStatus: "github_rejected",
      httpStatus: dispatch.status,
      requestId: dispatch.requestId
    }, { claimKey: plan.idempotency_key });
    await updateDispatchLease(env, taskId, {
      dispatchState: TASK_DISPATCH_STATE_FAILED,
      dispatchAttempt: plan.next_attempt,
      acceptedAt: (/* @__PURE__ */ new Date()).toISOString(),
      deadline: new Date(Date.now() + TASK_DISPATCH_CONFIRM_GRACE_MS).toISOString()
    });
    const result2 = {
      task_id: taskId,
      retried: false,
      dispatched: false,
      idempotent: false,
      dispatch_state: TASK_DISPATCH_STATE_FAILED,
      reason: DISPATCH_REASON_RETRY_FAILED,
      idempotency_key: plan.idempotency_key,
      next_attempt: plan.next_attempt,
      dispatch_status: "github_rejected",
      github_http_status: dispatch.status,
      github_request_id: dispatch.requestId
    };
    return { isError: true, text: JSON.stringify(result2), structuredContent: result2 };
  }
  const dispatchedAt = (/* @__PURE__ */ new Date()).toISOString();
  await finalizeDispatchMarker(env, taskId, {
    state: DISPATCH_STATE_DISPATCHED,
    dispatchStatus: "accepted",
    httpStatus: dispatch.status,
    requestId: dispatch.requestId,
    dispatchedAt
  }, { claimKey: plan.idempotency_key });
  await updateDispatchLease(env, taskId, {
    dispatchState: TASK_DISPATCH_STATE_RETRY,
    dispatchAttempt: plan.next_attempt,
    acceptedAt: dispatchedAt,
    deadline: new Date(Date.now() + TASK_DISPATCH_CONFIRM_GRACE_MS).toISOString()
  });
  const result2 = {
    task_id: taskId,
    retried: true,
    dispatched: true,
    idempotent: false,
    dispatch_state: TASK_DISPATCH_STATE_RETRY,
    reason: DISPATCH_REASON_REDISPATCHED,
    idempotency_key: plan.idempotency_key,
    next_attempt: plan.next_attempt,
    dispatch_status: "accepted",
    github_http_status: dispatch.status,
    github_request_id: dispatch.requestId,
    dispatched_at: dispatchedAt
  };
  return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
}
async function toolSubmitTask(env, args) {
  const contract = buildContract(args.goal, args.instructions, args.acceptance, args.expected_files, {
    project_id: args.project_id,
    root_task_id: args.root_task_id,
    parent_task_id: args.parent_task_id
  }, args.mode);
  const errors = validateContract(contract);
  if (errors.length) return { isError: true, text: `INVALID_TASK: ${errors.join("; ")}` };
  try {
    await recordTask(env, contract, {
      dispatchState: TASK_DISPATCH_STATE_PENDING,
      dispatchAttempt: 1
    });
  } catch {
  }
  let dispatch;
  try {
    dispatch = await dispatchTask(env, contract);
  } catch (err2) {
    await updateDispatchLease(env, contract.task_id, {
      dispatchState: TASK_DISPATCH_STATE_FAILED,
      dispatchAttempt: 1,
      acceptedAt: (/* @__PURE__ */ new Date()).toISOString(),
      deadline: new Date(Date.now() + TASK_DISPATCH_CONFIRM_GRACE_MS).toISOString()
    });
    return {
      isError: true,
      text: JSON.stringify({
        task_id: contract.task_id,
        status: "dispatch_failed",
        dispatch_state: TASK_DISPATCH_STATE_FAILED,
        dispatch_status: "network_error",
        github_http_status: null,
        github_request_id: null,
        github_response_body_safe: null,
        error: safeGithubResponseBody(err2?.message || "request failed")
      })
    };
  }
  if (!dispatch.ok) {
    await updateDispatchLease(env, contract.task_id, {
      dispatchState: TASK_DISPATCH_STATE_FAILED,
      dispatchAttempt: 1,
      acceptedAt: (/* @__PURE__ */ new Date()).toISOString(),
      deadline: new Date(Date.now() + TASK_DISPATCH_CONFIRM_GRACE_MS).toISOString()
    });
    return {
      isError: true,
      text: JSON.stringify({
        task_id: contract.task_id,
        status: "dispatch_failed",
        dispatch_state: TASK_DISPATCH_STATE_FAILED,
        dispatch_status: "github_rejected",
        github_http_status: dispatch.status,
        github_request_id: dispatch.requestId,
        github_response_body_safe: dispatch.bodySafe || null
      })
    };
  }
  await updateDispatchLease(env, contract.task_id, {
    dispatchState: TASK_DISPATCH_STATE_ACCEPTED,
    dispatchAttempt: 1,
    acceptedAt: (/* @__PURE__ */ new Date()).toISOString(),
    deadline: new Date(Date.now() + TASK_DISPATCH_CONFIRM_GRACE_MS).toISOString()
  });
  return {
    isError: false,
    text: JSON.stringify({
      task_id: contract.task_id,
      status: EXECUTION_STATUS_PENDING,
      submitted: true,
      round: 1,
      dispatch_state: TASK_DISPATCH_STATE_ACCEPTED,
      dispatch_status: "accepted",
      github_http_status: dispatch.status,
      github_request_id: dispatch.requestId,
      github_response_body_safe: dispatch.bodySafe || null
    })
  };
}
function normalizeLineageScope(args) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  const raw = input.scope && typeof input.scope === "object" && !Array.isArray(input.scope) ? input.scope : {};
  const projectId = raw.project_id ?? input.project_id;
  const rootTaskId = raw.root_task_id ?? input.root_task_id;
  const scope = {};
  if (projectId != null && String(projectId)) scope.project_id = String(projectId);
  if (rootTaskId != null && String(rootTaskId)) scope.root_task_id = String(rootTaskId);
  return Object.keys(scope).length ? scope : null;
}
var ACTIVE_PROJECT_ENV = "PERSONAL_AI_ACTIVE_PROJECT_ID";
var DEFAULT_ACTIVE_PROJECT_ID = "cloud-assets-activation";
var SUPERVISOR_ACTIVE_PROJECT_ENV = "PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT";
var FALSEY_CONFIG = ["", "0", "false", "no", "off"];
function supervisorActiveProjectEnabled(env, args) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  if (input.active_project === false || input.active_project === "false") return false;
  if (input.active_project === true || input.active_project === "true") return true;
  const raw = env ? env[SUPERVISOR_ACTIVE_PROJECT_ENV] : null;
  if (raw == null) return false;
  return FALSEY_CONFIG.indexOf(String(raw).trim().toLowerCase()) === -1;
}
function activeProjectScope(env, args) {
  const explicit = normalizeLineageScope(args);
  if (explicit) return explicit;
  if (!supervisorActiveProjectEnabled(env, args)) return null;
  const configured = env && env[ACTIVE_PROJECT_ENV] ? String(env[ACTIVE_PROJECT_ENV]).trim() : "";
  const projectId = configured || DEFAULT_ACTIVE_PROJECT_ID;
  return projectId ? { project_id: projectId } : null;
}
async function toolListPendingResults(env, args) {
  try {
    const scope = activeProjectScope(env, args);
    return { isError: false, text: JSON.stringify(await listPendingResults(env, scope)) };
  } catch (err2) {
    return { isError: true, text: `REGISTRY_READ_FAILED: ${err2.message}` };
  }
}
function buildTaskResult(taskId, data, artifact, run) {
  const raw = data && typeof data === "object" && !Array.isArray(data) ? data : {};
  const executionStatus = data ? verifiedResultStatus(raw.status, run) : EXECUTION_STATUS_PENDING;
  const result = {
    task_id: taskId,
    status: executionStatus,
    normalized_status: executionStatus,
    execution_status: executionStatus,
    terminal: TERMINAL_EXECUTION_STATUSES.includes(executionStatus),
    workflow_conclusion: run ? run.conclusion ?? null : null,
    review_verdict: null,
    round: raw.round ?? 1,
    execution_summary: raw.execution_summary ?? raw.summary ?? "",
    commit: raw.commit ?? "",
    tests: raw.tests ?? "",
    artifacts: raw.artifacts ?? raw.changed_files ?? [],
    execution_result_json: data ?? null,
    evidence: {
      ...raw.evidence ?? {
        artifact: {
          name: `execution_result-${taskId}`,
          id: artifact?.id ?? null,
          file: RESULT_FILENAME
        },
        validation: {
          artifact_found: Boolean(artifact),
          result_loaded: Boolean(data),
          task_id_matches: Boolean(data && raw.task_id === taskId)
        }
      },
      workflow_run: run ?? null
    }
  };
  if (raw.summary !== void 0) result.summary = raw.summary;
  return result;
}
async function finalizeTaskResult(env, taskId, result) {
  let registry = null;
  if (env.TASK_REGISTRY) {
    try {
      registry = await readTask(env, taskId);
    } catch {
      registry = null;
    }
  }
  if (registry) {
    result.review_verdict = registry.review_verdict ?? registry.verdict ?? null;
    result.review_state = registry.review_state ?? (registry.reviewed === true ? "reviewed" : null);
  }
  if (result.terminal && TERMINAL_EXECUTION_STATUSES.includes(result.status)) {
    await persistTerminalExecution(env, taskId, {
      status: result.status,
      normalized_status: result.status,
      execution_status: result.status,
      terminal: true,
      result_available: true,
      workflow_conclusion: result.workflow_conclusion ?? null,
      workflow_verified: true,
      synced: true,
      updated_at: (/* @__PURE__ */ new Date()).toISOString()
    });
    try {
      await emitTaskCompleted(env, {
        task_id: taskId,
        status: result.status,
        project_id: registry && registry.project_id ? registry.project_id : void 0
      });
    } catch {
    }
  }
  return result;
}
// Strict observation path: KV get + GitHub GET only. Never finalize results.
var EXECUTION_OBSERVATION_TTL_SECONDS = 60;
function sourceTimestamp(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)) ? value : null;
}
function positiveSourceInteger(value) {
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}
// Reuse GitHub's existing workflow-run registry; no callback or mapping writes.
var TASK_RUN_TITLE_PREFIX = "personal-ai-task:";
var TASK_WORKFLOW_PATH = ".github/workflows/agent-dispatch.yml";
// Diagnostic draft: structured allowlist only; never exception messages or bodies.
class TaskObservationReadError extends Error {
  constructor(diagnostics) {
    super("task observation read failed");
    this.diagnostics = diagnostics;
  }
}
function rejectObservationRedirect(response, stage) {
  // Never read Location, consume the redirect body, or forward credentials.
  if (response.status >= 300 && response.status < 400) {
    throw new TaskObservationReadError({ stage, failure_class: "redirect_rejected",
      http_status: response.status, github_request_id: null, rate_limit_remaining: null });
  }
}
async function observationWorkflowJson(url, options) {
  const d = { stage: "workflow_runs", failure_class: null,
    http_status: null, github_request_id: null, rate_limit_remaining: null };
  let response;
  try { response = await fetch(url, options); }
  catch {
    d.failure_class = options.signal?.aborted ? "timeout" : "network_or_redirect";
    throw new TaskObservationReadError(d);
  }
  rejectObservationRedirect(response, "workflow_runs");
  d.http_status = Number.isInteger(response.status) ? response.status : null;
  const requestId = response.headers.get("x-github-request-id");
  d.github_request_id = typeof requestId === "string" && /^[A-Fa-f0-9:]{1,128}$/.test(requestId) ? requestId : null;
  const remaining = response.headers.get("x-ratelimit-remaining");
  d.rate_limit_remaining = typeof remaining === "string" && /^\d{1,10}$/.test(remaining) && Number.isSafeInteger(Number(remaining)) ? Number(remaining) : null;
  if (!response.ok) {
    d.failure_class = "http";
    throw new TaskObservationReadError(d);
  }
  let payload;
  try { payload = await response.json(); }
  catch {
    d.failure_class = options.signal?.aborted ? "timeout" : "response_json";
    throw new TaskObservationReadError(d);
  }
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    d.failure_class = "response_shape";
    throw new TaskObservationReadError(d);
  }
  return { response, payload };
}
async function findEarlyTaskRun(env, task, readOptions) {
  const createdAt = sourceTimestamp(task.created_at);
  if (!createdAt) return { run: null, reason: null, coverage: "registration_time_missing" };
  // Approved-child registration happens AFTER dispatch. Reuse the existing
  // 15-minute dispatch grace as a bounded lookback, not an identity assertion.
  // Exact task/repo/workflow matching remains mandatory; older unseen runs stay unknown.
  const boundary = new Date(Math.floor((Date.parse(createdAt) - TASK_DISPATCH_CONFIRM_GRACE_MS) / 1000) * 1000).toISOString();
  const query = new URLSearchParams({ event: "repository_dispatch", per_page: "100", created: `>=${boundary}` });
  const { response, payload } = await observationWorkflowJson(`${API}/repos/${env.GITHUB_REPO}/actions/workflows/agent-dispatch.yml/runs?${query}`, {
    ...readOptions, headers: ghHeaders(env)
  });
  // A bounded incomplete page is not evidence that a newer dispatch is absent.
  if (!Array.isArray(payload.workflow_runs) || !Number.isSafeInteger(payload.total_count) ||
      payload.total_count < 0 || payload.total_count !== payload.workflow_runs.length ||
      response.headers.get("link")?.includes('rel="next"')) {
    return { run: null, reason: "run_lookup_incomplete" };
  }
  const title = `${TASK_RUN_TITLE_PREFIX}${task.task_id}`;
  const matches = payload.workflow_runs.filter((run) => run?.display_title === title);
  if (!matches.length) return { run: null, reason: null, coverage: "no_named_run_visible" };
  for (const run of matches) {
    if (!positiveSourceInteger(run.id) || !positiveSourceInteger(run.run_number) ||
        !positiveSourceInteger(run.run_attempt) || run.event !== "repository_dispatch" ||
        run.path !== TASK_WORKFLOW_PATH ||
        typeof run.repository?.full_name !== "string" ||
        run.repository.full_name.toLowerCase() !== env.GITHUB_REPO.toLowerCase() ||
        !sourceTimestamp(run.created_at) || Date.parse(run.created_at) < Date.parse(boundary)) {
      return { run: null, reason: "invalid_early_run_identity" };
    }
  }
  // run_number orders dispatches within this one workflow; run_attempt orders reruns.
  // A late rerun of an older dispatch must not replace a newer dispatch.
  matches.sort((a, b) => b.run_number - a.run_number || b.run_attempt - a.run_attempt);
  const selected = matches[0];
  if (matches.some((run) => run.run_number === selected.run_number && run.id !== selected.id)) {
    return { run: null, reason: "ambiguous_early_run_identity" };
  }
  return { run: selected, reason: null, coverage: "named_workflow_run" };
}
function hasTaskObservationScope(auth) {
  if (!hasWriteScope(auth)) return false;
  if (auth.kind === "static") return true;
  const payload = auth.payload;
  // normalizeScopes has legacy defaults: inspect the signed claims directly.
  return auth.kind === "oauth" && payload?.aud === "mcp" &&
    Number.isFinite(payload.exp) && payload.exp > nowSec() &&
    typeof payload.scope === "string" && payload.scope.split(/\s+/).includes(SCOPE);
}
async function toolGetTaskExecutionStatus(env, args) {
  const taskId = args.task_id;
  if (typeof taskId !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(taskId)) {
    return { isError: true, text: "INVALID_INPUT: task_id required (1-128 letters, digits, _ or -)" };
  }
  const result = {
    contract: "task_execution_observation.v1", task_id: taskId,
    source: "github_actions", scope: "single_task_mapped_run",
    full_task_coverage: false, agent_state: "unknown",
    mapping: { kind: "unknown", artifact_id: null, run_id: null, run_number: null, coverage: null },
    executor: { state: "unknown", run_id: null, run_attempt: null, status: null, conclusion: null,
      created_at: null, updated_at: null, run_started_at: null, completed_at: null },
    // Registry execution_status historically combines workflow and business status.
    // Neither that value nor a review verdict establishes independent acceptance.
    business: { state: "unknown", reason: "business_result_not_read" },
    acceptance: { state: "unknown", reason: "independent_acceptance_not_read" },
    registry: { available: false, dispatch_attempt: null },
    observed_at: null, ttl_seconds: EXECUTION_OBSERVATION_TTL_SECONDS,
    expires_at: null, reason: null
  };
  const finish = () => {
    result.observed_at = new Date().toISOString();
    result.expires_at = new Date(Date.parse(result.observed_at) + result.ttl_seconds * 1000).toISOString();
    return { isError: false, text: JSON.stringify(result), structuredContent: result };
  };
  let task;
  try { task = await readTask(env, taskId); }
  catch { result.reason = "registry_read_failed"; return finish(); }
  if (!task || task.task_id !== taskId) {
    result.reason = "task_registration_unavailable";
    return finish();
  }
  result.registry = { available: true, dispatch_attempt: positiveSourceInteger(task.dispatch_attempt) };
  if (typeof env.GITHUB_REPO !== "string" || !/^[A-Za-z0-9_-]+\/[A-Za-z0-9_.-]+$/.test(env.GITHUB_REPO) || !env.GITHUB_TOKEN) {
    result.reason = "github_configuration_unavailable";
    return finish();
  }
  // Bound all GETs together; reject redirects so authorization stays on GitHub.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  const readOptions = { method: "GET", redirect: "manual", signal: controller.signal };
  try {
    const early = await findEarlyTaskRun(env, task, readOptions);
    result.mapping.coverage = early.coverage ?? null;
    if (early.reason) { result.reason = early.reason; return finish(); }
    let artifact;
    if (early.run) {
      result.mapping.kind = "workflow_run_name";
      result.mapping.run_number = early.run.run_number;
      artifact = { workflow_run: { id: early.run.id } };
    } else {
      // Compatibility only: old workflows used display_title=gpt_task.
      result.mapping.kind = "execution_result_artifact";
      artifact = await findArtifact(env, `execution_result-${taskId}`, readOptions);
      if (!artifact) { result.reason = "task_run_mapping_unavailable"; return finish(); }
      if (artifact.name !== `execution_result-${taskId}` || !positiveSourceInteger(artifact.workflow_run?.id)) {
        result.reason = "invalid_task_run_mapping"; return finish();
      }
      result.mapping.artifact_id = positiveSourceInteger(artifact.id);
    }
    const runId = artifact.workflow_run.id;
    result.mapping.run_id = runId;
    result.executor.run_id = runId;
    const run = await getArtifactWorkflowRun(env, artifact, readOptions);
    if (run.id !== runId) { result.reason = "run_identity_mismatch"; return finish(); }
    if (typeof run.repository_full_name !== "string" ||
        run.repository_full_name.toLowerCase() !== env.GITHUB_REPO.toLowerCase()) {
      result.reason = "run_repository_mismatch"; return finish();
    }
    if (early.run && (run.display_title !== `${TASK_RUN_TITLE_PREFIX}${taskId}` ||
        run.event !== "repository_dispatch" || run.path !== TASK_WORKFLOW_PATH ||
        run.run_number !== early.run.run_number || !positiveSourceInteger(run.run_attempt) ||
        run.run_attempt < early.run.run_attempt)) {
      result.reason = "early_run_changed_or_regressed"; return finish();
    }
    if (result.registry.dispatch_attempt > 1) {
      const accepted = sourceTimestamp(task.dispatch_accepted_at);
      const sourceCreated = sourceTimestamp(run.created_at);
      if (!accepted || !sourceCreated || Date.parse(sourceCreated) < Math.floor(Date.parse(accepted) / 1000) * 1000) {
        result.reason = "latest_dispatch_not_visible"; return finish();
      }
    }
    const ex = result.executor;
    ex.run_attempt = positiveSourceInteger(run.run_attempt);
    const statuses = ["queued", "in_progress", "completed", "requested", "waiting", "pending"];
    const conclusions = ["success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "stale", "startup_failure"];
    ex.status = typeof run.status === "string" ? run.status : null;
    ex.conclusion = typeof run.conclusion === "string" ? run.conclusion : null;
    for (const field of ["created_at", "updated_at", "run_started_at", "completed_at"]) {
      ex[field] = sourceTimestamp(run[field]);
    }
    if (!statuses.includes(ex.status) || !ex.run_attempt || (ex.status === "completed" && !conclusions.includes(ex.conclusion))) {
      result.reason = "incomplete_source_fields";
    } else if (ex.status !== "completed" && run.conclusion != null) {
      result.reason = "inconsistent_source_fields";
    } else {
      ex.state = ex.status === "in_progress" ? "running" : ex.status === "completed" ? "completed" : "queued";
    }
  } catch (error) {
    // Only our locally constructed diagnostic type can supply allowlisted fields.
    if (error instanceof TaskObservationReadError) result.github_diagnostics = error.diagnostics;
    result.reason = controller.signal.aborted ? "github_read_timeout" : "github_read_failed";
  } finally { clearTimeout(timer); }
  return finish();
}

async function toolGetTaskResult(env, args) {
  const taskId = String(args.task_id ?? "");
  if (!taskId) return { isError: true, text: "INVALID_INPUT: task_id required" };
  let artifact;
  try {
    artifact = await findArtifact(env, `execution_result-${taskId}`);
  } catch (err2) {
    return { isError: true, text: `GITHUB_READ_FAILED: ${err2.message}` };
  }
  if (!artifact) {
    const result2 = await finalizeTaskResult(env, taskId, buildTaskResult(taskId, null, null));
    return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
  }
  let data;
  try {
    data = await downloadArtifactJson(env, artifact.id);
  } catch (err2) {
    return { isError: true, text: `GITHUB_READ_FAILED: ${err2.message}` };
  }
  if (data.task_id !== taskId) return { isError: true, text: "TASK_ID_MISMATCH" };
  let run;
  try {
    run = await getArtifactWorkflowRun(env, artifact);
  } catch (err2) {
    return { isError: true, text: `GITHUB_READ_FAILED: ${err2.message}` };
  }
  const result = await finalizeTaskResult(env, taskId, buildTaskResult(taskId, data, artifact, run));
  return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
function assetSubtype(row, content) {
  if (content && typeof content.subtype === "string" && content.subtype.trim()) return content.subtype.trim();
  return ASSET_SUBTYPE_SCHEMA[String(row.schema_version || "")] || null;
}
var BLOCKED_READ_KEY = /(?:^|_)(?:path|source_db|decrypted_dir|media_root|key|token|secret|credential|password|authorization|database|db_path|raw_metadata)(?:$|_)/i;
function safeAssetRead(value, key = "", depth = 0) {
  if (depth > 12) return null;
  if (key && BLOCKED_READ_KEY.test(key)) return void 0;
  if (typeof value === "string") {
    if (/(?:^[A-Za-z]:[\\/]|^\\\\|^file:\/\/)/i.test(value)) return "[REDACTED]";
    return value;
  }
  if (Array.isArray(value)) return value.map((entry) => safeAssetRead(entry, "", depth + 1)).filter((entry) => entry !== void 0);
  if (value && typeof value === "object") {
    const out = {};
    for (const [childKey, childValue] of Object.entries(value)) {
      const cleaned = safeAssetRead(childValue, childKey, depth + 1);
      if (cleaned !== void 0) out[childKey] = cleaned;
    }
    return out;
  }
  return value;
}
function parseAssetJson(value) {
  try {
    return JSON.parse(String(value));
  } catch {
    return String(value);
  }
}
var ASSET_PROVENANCE_CONTRACT = "PERSONAL_AI_ASSET_PROVENANCE_V0.2";
var PROVENANCE_STATUS_VERIFIED = "VERIFIED";
var PROVENANCE_STATUS_INCOMPLETE = "INCOMPLETE";
var PROVENANCE_STATUS_HASH_MISMATCH = "HASH_MISMATCH";
var PROVENANCE_FIELDS = [
  "source_identity",
  "source_location",
  "source_version",
  "content_version",
  "canonical_version",
  "content_hash",
  "source_content_hash",
  "verification_evidence",
  "promotion_decision",
  "promotion_event",
  "captured_at",
  "promoted_at",
  "supersedes",
  "superseded_by"
];
var REQUIRED_PROVENANCE_FIELDS = [
  "source_identity",
  "source_location",
  "source_version",
  "content_version",
  "canonical_version",
  "content_hash",
  "verification_evidence",
  "promotion_decision",
  "promotion_event",
  "captured_at",
  "promoted_at"
];
var PROVENANCE_FIELD_ALIASES = {
  source_identity: ["source.identity", "source_identity", "source_id", "source.id"],
  source_location: ["source.location", "source_location", "source_uri", "source.url"],
  source_version: ["source_version", "source.version", "source_revision"],
  content_version: ["content_version", "source.content_version", "content_revision"],
  canonical_version: ["canonical_version", "target_version", "version"],
  content_hash: ["content_hash", "canonical_content_hash", "hash"],
  source_content_hash: ["source_content_hash", "source.hash", "source_hash"],
  verification_evidence: ["verification.evidence", "verification_evidence", "evidence"],
  promotion_decision: ["promotion.decision", "promotion_decision", "decision"],
  promotion_event: ["promotion.event_id", "promotion_event", "promotion_event_id", "promotion.id"],
  captured_at: ["captured_at", "source.captured_at", "source_timestamp"],
  promoted_at: ["promoted_at", "promotion.decided_at", "promotion.timestamp"],
  supersedes: ["supersedes", "supersession", "lineage.supersedes"],
  superseded_by: ["superseded_by", "lineage.superseded_by"]
};
var PROVENANCE_VERIFICATION_HASH_KEYS = [
  "content_hash_matches",
  "expected_content_hash",
  "content_hash"
];
var PROVENANCE_HASH_PREFIXES = ["sha256:", "sha-256:", "sha256-", "sha-512:", "0x"];
function provLookup(mapping, path) {
  let current = mapping;
  for (const part of path.split(".")) {
    if (!current || typeof current !== "object" || Array.isArray(current) || !(part in current)) return null;
    current = current[part];
  }
  return current;
}
function provMeaningful(value) {
  if (value === null || value === void 0) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}
function provResolve(provenance, field) {
  const aliases = PROVENANCE_FIELD_ALIASES[field] || [];
  for (const alias of aliases) {
    const value = provLookup(provenance, alias);
    if (provMeaningful(value)) return value;
  }
  return null;
}
function normalizeProvenanceHash(value) {
  let text = String(value).trim().toLowerCase();
  for (const prefix of PROVENANCE_HASH_PREFIXES) {
    if (text.startsWith(prefix)) {
      text = text.slice(prefix.length);
      break;
    }
  }
  return text.replace(/\s+/g, "");
}
function provenanceExpectedHashes(provenance, verification) {
  const expected = [];
  for (const source of [provLookup(provenance, "verification"), verification]) {
    if (!source || typeof source !== "object" || Array.isArray(source)) continue;
    for (const key of ["expected_content_hash", "content_hash"]) {
      if (provMeaningful(source[key])) expected.push(source[key]);
    }
  }
  return expected;
}
function provenanceExplicitMatch(provenance, verification) {
  for (const source of [provLookup(provenance, "verification"), verification]) {
    if (source && typeof source === "object" && !Array.isArray(source) && "content_hash_matches" in source) {
      return Boolean(source.content_hash_matches);
    }
  }
  return null;
}
function evaluateAssetProvenance(provenance, options) {
  const opts = options || {};
  const source = provenance && typeof provenance === "object" && !Array.isArray(provenance) ? provenance : {};
  const verification = opts.verification;
  const fields = {};
  for (const field of PROVENANCE_FIELDS) {
    fields[field] = provResolve(source, field);
  }
  if (fields.canonical_version === null && provMeaningful(opts.canonical_version)) {
    fields.canonical_version = opts.canonical_version;
  }
  if (fields.verification_evidence === null && verification && typeof verification === "object" && !Array.isArray(verification)) {
    let candidate = verification.evidence;
    if (!provMeaningful(candidate)) candidate = verification.method;
    if (provMeaningful(candidate)) {
      fields.verification_evidence = candidate;
    } else {
      const extra = {};
      for (const [key, value] of Object.entries(verification)) {
        if (!PROVENANCE_VERIFICATION_HASH_KEYS.includes(key) && provMeaningful(value)) extra[key] = value;
      }
      if (Object.keys(extra).length) fields.verification_evidence = extra;
    }
  }
  const missing = REQUIRED_PROVENANCE_FIELDS.filter((field) => fields[field] === null);
  const declared = fields.content_hash;
  const expected = provenanceExpectedHashes(source, verification);
  const stored = provMeaningful(opts.content_hash) ? opts.content_hash : null;
  const pairs = [];
  if (declared !== null && stored !== null) pairs.push([declared, stored]);
  if (declared !== null && expected.length) pairs.push([declared, expected[0]]);
  if (stored !== null && expected.length) pairs.push([stored, expected[0]]);
  let hashChecked = false;
  let hashMatch = null;
  for (const [left, right] of pairs) {
    hashChecked = true;
    if (normalizeProvenanceHash(left) !== normalizeProvenanceHash(right)) {
      hashMatch = false;
      break;
    }
    if (hashMatch === null) hashMatch = true;
  }
  const explicit = provenanceExplicitMatch(source, verification);
  if (explicit !== null) {
    hashChecked = true;
    if (explicit === false) hashMatch = false;
    else if (hashMatch === null) hashMatch = explicit;
  }
  const complete = missing.length === 0;
  const verified = complete && hashMatch !== false;
  let supersedes = fields.supersedes;
  if (Array.isArray(supersedes)) supersedes = supersedes.slice();
  else if (supersedes === null) supersedes = [];
  else supersedes = [supersedes];
  let status;
  let reason;
  if (hashMatch === false) {
    status = PROVENANCE_STATUS_HASH_MISMATCH;
    reason = "provenance hash mismatch: content_hash does not agree with the recorded verification evidence";
  } else if (verified) {
    status = PROVENANCE_STATUS_VERIFIED;
    reason = "provenance complete: source/version/hash/verification/promotion evidence linked";
  } else {
    status = PROVENANCE_STATUS_INCOMPLETE;
    reason = "provenance incomplete: missing " + missing.join(", ");
  }
  return {
    contract: ASSET_PROVENANCE_CONTRACT,
    status,
    complete,
    verified,
    missing,
    fields,
    hash_checked: hashChecked,
    hash_match: hashMatch,
    lineage: { supersedes, superseded_by: fields.superseded_by ?? null },
    reason
  };
}
function readAssetMetadata(row) {
  const parsed = parseAssetJson(row.content);
  const provenance = safeAssetRead(parseAssetJson(row.provenance));
  const verification = safeAssetRead(parseAssetJson(row.verification));
  const completeness = evaluateAssetProvenance(provenance, {
    content_hash: row.content_hash,
    canonical_version: row.current_version,
    verification
  });
  return {
    asset_id: row.asset_id,
    asset_type: row.asset_type,
    subtype: assetSubtype(row, parsed),
    title: row.title,
    current_version: row.current_version,
    content_hash: row.content_hash,
    updated_at: row.updated_at,
    provenance_status: completeness.status,
    provenance_complete: completeness.complete,
    provenance_verified: completeness.verified,
    provenance_missing: completeness.missing,
    provenance: completeness.fields,
    provenance_lineage: completeness.lineage
  };
}
async function toolSearchAssets(env, args) {
  if (!env.ASSET_DB) return { isError: true, text: "ASSET_READ_UNAVAILABLE" };
  const typeInput = String(args.asset_type ?? "").trim().toUpperCase();
  if (typeInput && !ASSET_TYPES.has(typeInput)) return { isError: true, text: "INVALID_ASSET_TYPE" };
  const subtype = String(args.subtype ?? "").trim().slice(0, 120);
  const query = String(args.query ?? "").trim().slice(0, 200);
  const limit = Math.min(Math.max(Number(args.limit) || 20, 1), 100);
  const like = query ? `%${query.replace(/[\\%_]/g, "\\$&")}%` : "%";
  const result = await env.ASSET_DB.prepare(
    "SELECT asset_id,asset_type,schema_version,title,status,current_version,content_hash,updated_at, (SELECT content FROM asset_versions av WHERE av.asset_id=assets.asset_id AND av.version=assets.current_version) AS content, (SELECT provenance FROM asset_versions av WHERE av.asset_id=assets.asset_id AND av.version=assets.current_version) AS provenance, (SELECT verification FROM asset_versions av WHERE av.asset_id=assets.asset_id AND av.version=assets.current_version) AS verification FROM assets WHERE (? = '' OR asset_type = ?) AND (? = '%' OR title LIKE ? ESCAPE '\\' OR asset_id LIKE ? ESCAPE '\\') ORDER BY updated_at DESC LIMIT ?"
  ).bind(typeInput, typeInput, query ? query : "%", like, like, limit).all();
  const assets = (result.results || []).map(readAssetMetadata).filter((asset) => !subtype || asset.subtype === subtype).slice(0, limit);
  return { isError: false, text: JSON.stringify({ assets }), structuredContent: { assets } };
}
async function toolGetAsset(env, args) {
  if (!env.ASSET_DB) return { isError: true, text: "ASSET_READ_UNAVAILABLE" };
  const assetId = String(args.asset_id ?? "").trim();
  if (!ASSET_ID_RE.test(assetId)) return { isError: true, text: "INVALID_ASSET_ID" };
  const row = await env.ASSET_DB.prepare(
    "SELECT a.asset_id,a.asset_type,a.schema_version,a.title,a.status,a.current_version,a.content_hash,a.updated_at, v.content,v.provenance,v.verification FROM assets a JOIN asset_versions v ON v.asset_id=a.asset_id AND v.version=a.current_version WHERE a.asset_id=?"
  ).bind(assetId).first();
  if (!row) return { isError: true, text: "ASSET_NOT_FOUND" };
  const rawContent = parseAssetJson(row.content);
  const content = safeAssetRead(rawContent);
  const provenance = safeAssetRead(parseAssetJson(row.provenance));
  const verification = safeAssetRead(parseAssetJson(row.verification));
  const completeness = evaluateAssetProvenance(provenance, {
    content_hash: row.content_hash,
    canonical_version: row.current_version,
    verification
  });
  const result = {
    asset_id: row.asset_id,
    asset_type: row.asset_type,
    subtype: assetSubtype(row, rawContent),
    version: row.current_version,
    content_hash: row.content_hash,
    provenance,
    verification,
    provenance_status: completeness.status,
    provenance_verified: completeness.verified,
    historical_provenance_incomplete: completeness.status === PROVENANCE_STATUS_INCOMPLETE,
    provenance_completeness: completeness,
    content
  };
  return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
var KNOWLEDGE_WRITE_CONTRACT = "PERSONAL_AI_KNOWLEDGE_CANDIDATE_WRITER_V0.1";
var KNOWLEDGE_ASSET_TYPE = "KNOWLEDGE";
var KNOWLEDGE_WRITE_LIMITS = { title: 300 };
var KNOWLEDGE_WRITE_STATUS = "accepted";
var KNOWLEDGE_HASH_RE = /^[0-9a-f]{64}$/;
var KNOWLEDGE_VERSION_INSERT = "INSERT INTO asset_versions (asset_id, version, content, content_hash, provenance, verification, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)";
var KNOWLEDGE_VERSION_VERIFY = "SELECT a.current_version AS asset_version, a.content_hash AS asset_content_hash, a.status AS asset_status, v.version AS version_version, v.content AS version_content, v.content_hash AS version_content_hash, v.created_by AS version_created_by, v.provenance AS version_provenance, v.verification AS version_verification FROM assets a JOIN asset_versions v ON v.asset_id = a.asset_id AND v.version = a.current_version WHERE a.asset_id = ?";
function canonicalKnowledgeContent(content) {
  if (typeof content === "string") return content;
  return JSON.stringify(content);
}
async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  let hex = "";
  for (const byte of new Uint8Array(digest)) hex += byte.toString(16).padStart(2, "0");
  return hex;
}
function buildKnowledgeProvenance(input) {
  const nowIso = (/* @__PURE__ */ new Date()).toISOString();
  const capturedAt = String(input.captured_at ?? nowIso);
  const promotedAt = String(input.promoted_at ?? nowIso);
  const sourceVersion = String(input.source_version ?? "v1");
  return {
    source: {
      identity: String(input.source_identity ?? `knowledge-candidate:${input.asset_id}`),
      location: String(input.source_location ?? "cloud://knowledge-inbox")
    },
    source_version: sourceVersion,
    content_version: String(input.content_version ?? sourceVersion),
    source_content_hash: input.source_content_hash == null ? null : String(input.source_content_hash),
    canonical_version: input.canonical_version,
    content_hash: input.content_hash,
    verification: {
      method: "recompute_content_hash",
      evidence: {
        checked_by: "knowledge_candidate_writer",
        recomputed: input.content_hash
      },
      verified_at: promotedAt,
      expected_content_hash: input.content_hash,
      content_hash_matches: true
    },
    promotion: {
      decision: String(input.promotion_decision ?? "PROMOTE"),
      event_id: String(input.promotion_event ?? `promote:${input.asset_id}:${input.canonical_version}`),
      decided_at: promotedAt,
      actor: String(input.actor ?? "cloud-agent")
    },
    captured_at: capturedAt,
    promoted_at: promotedAt,
    supersedes: Array.isArray(input.supersedes) ? input.supersedes.slice() : [],
    superseded_by: input.superseded_by ?? null
  };
}
async function verifyKnowledgeVersion(db, assetId, expectedVersion, expectedHash, expectedContent) {
  let row;
  try {
    row = await db.prepare(KNOWLEDGE_VERSION_VERIFY).bind(assetId).first();
  } catch {
    return false;
  }
  if (!row) return false;
  if (Number(row.asset_version) !== Number(expectedVersion)) return false;
  if (Number(row.version_version) !== Number(expectedVersion)) return false;
  if (String(row.asset_content_hash) !== String(expectedHash)) return false;
  if (String(row.version_content_hash) !== String(expectedHash)) return false;
  if (expectedContent !== void 0 && String(row.version_content) !== String(expectedContent)) return false;
  if (String(row.asset_status) !== KNOWLEDGE_WRITE_STATUS) return false;
  const createdBy = row.version_created_by == null ? "" : String(row.version_created_by).trim();
  if (!createdBy) return false;
  const persistedProvenance = parseAssetJson(row.version_provenance);
  const persistedVerification = parseAssetJson(row.version_verification);
  const evaluation = evaluateAssetProvenance(persistedProvenance, {
    content_hash: expectedHash,
    canonical_version: expectedVersion,
    verification: persistedVerification
  });
  if (evaluation.status !== PROVENANCE_STATUS_VERIFIED || evaluation.verified !== true) return false;
  return true;
}
async function writeKnowledgeCandidate(env, args, allowed = KNOWLEDGE_ASSET_TYPE) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  if (!env || !env.ASSET_DB) return { isError: true, text: "ASSET_WRITE_UNAVAILABLE" };
  const assetType = String(input.asset_type ?? allowed).trim().toUpperCase();
  if (assetType !== allowed) return { isError: true, text: "INVALID_ASSET_TYPE" };
  const contract = assetType === KNOWLEDGE_ASSET_TYPE ? KNOWLEDGE_WRITE_CONTRACT : "PERSONAL_AI_SKILL_CANDIDATE_WRITER_V0.1";
  const assetId = String(input.asset_id ?? input.candidate_id ?? "").trim();
  if (!ASSET_ID_RE.test(assetId)) return { isError: true, text: "INVALID_ASSET_ID" };
  const title = String(input.title ?? "").trim().slice(0, KNOWLEDGE_WRITE_LIMITS.title);
  if (!title) return { isError: true, text: "INVALID_TITLE" };
  if (input.content == null) return { isError: true, text: "INVALID_CONTENT" };
  const canonicalContent = canonicalKnowledgeContent(input.content);
  if (!canonicalContent.trim()) return { isError: true, text: "INVALID_CONTENT" };
  const contentHash = await sha256Hex(canonicalContent);
  if (!KNOWLEDGE_HASH_RE.test(contentHash)) return { isError: true, text: "ASSET_WRITE_FAILED" };
  const nowIso = (/* @__PURE__ */ new Date()).toISOString();
  const db = env.ASSET_DB;
  let existing;
  try {
    existing = await db.prepare(
      "SELECT asset_id, asset_type, current_version, content_hash, updated_at FROM assets WHERE asset_id = ?"
    ).bind(assetId).first();
  } catch {
    return { isError: true, text: "ASSET_WRITE_FAILED" };
  }
  if (existing && existing.asset_type !== assetType) return { isError: true, text: "ASSET_TYPE_OWNERSHIP_MISMATCH" };
  const approvalBound = assetType === "KNOWLEDGE" && input.__knowledge_gate === "KNOWLEDGE_PROD_V02_COUNTER_V1";
  if (approvalBound && (existing?.current_version ?? null) !== input.expected_current_version) return { isError: true, text: "TARGET_VERSION_CHANGED" };
  if (existing && normalizeProvenanceHash(existing.content_hash) === contentHash) {
    const currentVersion = Number(existing.current_version) || 1;
    const present = await verifyKnowledgeVersion(db, assetId, currentVersion, contentHash, canonicalContent);
    if (!present) return { isError: true, text: "ASSET_WRITE_FAILED" };
    const replay = {
      contract,
      asset_id: assetId,
      asset_type: assetType,
      status: "IDEMPOTENT",
      created: false,
      idempotent: true,
      version: currentVersion,
      content_hash: contentHash,
      provenance_status: PROVENANCE_STATUS_VERIFIED,
      provenance_verified: true,
      updated_at: existing.updated_at ?? nowIso
    };
    return { isError: false, text: JSON.stringify(replay), structuredContent: replay };
  }
  const previousVersion = existing ? Number(existing.current_version) || 0 : 0;
  const version = previousVersion + 1;
  const provenance = buildKnowledgeProvenance({
    ...input,
    asset_id: assetId,
    canonical_version: version,
    content_hash: contentHash,
    supersedes: previousVersion > 0 ? [...Array.isArray(input.supersedes) ? input.supersedes : [], String(previousVersion)] : input.supersedes
  });
  const verification = provenance.verification;
  const schemaVersion = String(input.schema_version ?? "v0.1");
  const createdBy = String(input.created_by ?? input.actor ?? "cloud-agent").trim() || "cloud-agent";
  const assetWrite = existing ? db.prepare(
    "UPDATE assets SET schema_version = ?, title = ?, status = ?, current_version = ?, content_hash = ?, updated_at = ? WHERE asset_id = ?"
  ).bind(schemaVersion, title, KNOWLEDGE_WRITE_STATUS, version, contentHash, nowIso, assetId) : db.prepare(
    "INSERT INTO assets (asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
  ).bind(assetId, assetType, schemaVersion, title, KNOWLEDGE_WRITE_STATUS, version, contentHash, nowIso, nowIso);
  const boundAssetWrite = approvalBound && existing ? db.prepare("UPDATE assets SET schema_version=?,title=?,status=?,current_version=?,content_hash=?,updated_at=? WHERE asset_id=? AND asset_type='KNOWLEDGE' AND current_version=?").bind(schemaVersion, title, KNOWLEDGE_WRITE_STATUS, version, contentHash, nowIso, assetId, input.expected_current_version) : assetWrite;
  const versionWrite = db.prepare(KNOWLEDGE_VERSION_INSERT).bind(
    assetId,
    version,
    canonicalContent,
    contentHash,
    JSON.stringify(provenance),
    JSON.stringify(verification),
    createdBy,
    nowIso
  );
  if (typeof db.batch !== "function") return { isError: true, text: "ASSET_WRITE_FAILED" };
  try {
    await db.batch(approvalBound ? [boundAssetWrite, db.prepare("SELECT CASE WHEN changes()=1 THEN 1 ELSE json('TARGET_VERSION_CAS_LOST') END AS ok"), versionWrite] : [assetWrite, versionWrite]);
  } catch {
    return { isError: true, text: "ASSET_WRITE_FAILED" };
  }
  const persisted = await verifyKnowledgeVersion(db, assetId, version, contentHash, canonicalContent);
  if (!persisted) return { isError: true, text: "ASSET_WRITE_FAILED" };
  const result = {
    contract,
    asset_id: assetId,
    asset_type: assetType,
    schema_version: schemaVersion,
    title,
    status: "WRITTEN",
    created: !existing,
    idempotent: false,
    version,
    previous_version: previousVersion > 0 ? previousVersion : null,
    content_hash: contentHash,
    provenance_status: PROVENANCE_STATUS_VERIFIED,
    provenance_verified: true,
    promotion_event: provenance.promotion.event_id,
    supersedes: provenance.supersedes,
    updated_at: nowIso
  };
  return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
async function writeSkillCandidate(env, args) {
  return writeKnowledgeCandidate(env, args, "SKILL");
}
async function toolWriteKnowledgeCandidate(env, args) {
  try {
    const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
    // The public Knowledge route never writes a non-KNOWLEDGE asset type.
    const assetType = String(input.asset_type ?? KNOWLEDGE_ASSET_TYPE).trim().toUpperCase();
    if (assetType !== KNOWLEDGE_ASSET_TYPE) return { isError: true, text: "INVALID_ASSET_TYPE" };
    // The single public Knowledge MCP tool dispatches the candidate lifecycle
    // sub-operations so an authorised agent has real, callable entry points
    // without expanding the frozen `tools/list` surface:
    //   create  -> persist an independent DRAFT candidate
    //   read    -> independent read by candidate_id (cross-agent / cross-session)
    //   submit  -> DRAFT -> PENDING_REVIEW
    //   review  -> record PASS / FAIL
    //   promote -> the sole Canonical write gate (default, fail-closed)
    // Any other/missing sub-operation falls through to the promotion gate.
    const op = String(input.candidate_operation ?? input.operation ?? "").trim().toLowerCase();
    if (op === "create" || op === "create_candidate") return await createKnowledgeCandidate(env, input);
    if (op === "read" || op === "get" || op === "get_candidate") return await readKnowledgeCandidate(env, input);
    if (op === "submit" || op === "submit_review" || op === "submit_for_review") return await submitKnowledgeCandidateForReview(env, input);
    if (op === "review" || op === "record_review") return await recordKnowledgeCandidateReview(env, input);
    // Promotion (fail-closed). A Canonical write is ONLY authorised through the
    // independent staged-candidate promotion gate (validateCandidateGate via
    // promoteKnowledgeCandidate). A legacy asset_id-only call carries no
    // candidate, no review state, and no bound approval, so it is rejected
    // before any DB read, Canonical writer call, or mutation. A caller-supplied
    // promotion_decision/approved_by/approval_receipt never authorises the write.
    return await promoteKnowledgeCandidate(env, args);
  } catch (err2) {
    return { isError: true, text: `KNOWLEDGE_WRITE_FAILED: ${err2?.message || "unknown"}` };
  }
}
function knowledgeCandidateReadOperation(args) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  const op = String(input.candidate_operation ?? input.operation ?? "").trim().toLowerCase();
  return op === "read" || op === "get" || op === "get_candidate";
}
var KNOWLEDGE_CANDIDATE_CONTRACT = "PERSONAL_AI_KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_V1";
var KNOWLEDGE_PROMOTION_OPERATION = "KNOWLEDGE_PROMOTION";
var KNOWLEDGE_CANDIDATE_DRAFT = "DRAFT";
var KNOWLEDGE_CANDIDATE_PENDING_REVIEW = "PENDING_REVIEW";
var KNOWLEDGE_CANDIDATE_APPROVED_FOR_PROMOTION = "APPROVED_FOR_PROMOTION";
// Transient promotion claim. A promotion atomically moves the candidate from
// APPROVED_FOR_PROMOTION to PROMOTION_RESERVED before it consumes the approval
// or calls the Canonical writer. This is the linearization point that competes
// with a review FAIL: once reserved, a FAIL's guarded UPDATE (which only matches
// pre-promotion states) makes zero changes, so an accepted FAIL can never race
// ahead of an in-flight promotion, and a promotion can never overwrite a
// recorded FAIL. Only `recordKnowledgeCandidateReview` (and promotion itself)
// transitions out of a pre-promotion state, so no extra column is required.
var KNOWLEDGE_CANDIDATE_PROMOTION_RESERVED = "PROMOTION_RESERVED";
var KNOWLEDGE_CANDIDATE_PROMOTED = "PROMOTED";
var KNOWLEDGE_CANDIDATE_CANONICAL_READBACK_VERIFIED = "CANONICAL_READBACK_VERIFIED";
var KNOWLEDGE_CANDIDATE_STATES = [
  KNOWLEDGE_CANDIDATE_DRAFT,
  KNOWLEDGE_CANDIDATE_PENDING_REVIEW,
  KNOWLEDGE_CANDIDATE_APPROVED_FOR_PROMOTION,
  KNOWLEDGE_CANDIDATE_PROMOTION_RESERVED,
  KNOWLEDGE_CANDIDATE_PROMOTED,
  KNOWLEDGE_CANDIDATE_CANONICAL_READBACK_VERIFIED
];
var KNOWLEDGE_CANDIDATE_NOT_REVIEWED = "NOT_REVIEWED";
var KNOWLEDGE_CANDIDATE_REVIEW_PASS = "PASS";
var KNOWLEDGE_CANDIDATE_REVIEW_FAIL = "FAIL";
var KNOWLEDGE_PROMOTION_REJECTED = "REJECTED";
var KNOWLEDGE_PROMOTION_WRITTEN = "WRITTEN";
var KNOWLEDGE_PROMOTION_IDEMPOTENT = "IDEMPOTENT";
var KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_MISSING = "candidate_missing";
var KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_STATE = "candidate_state";
var KNOWLEDGE_PROMOTION_REJECT_STORED_REVIEW = "stored_review_not_pass";
var KNOWLEDGE_PROMOTION_REJECT_REVIEW = "review_not_pass";
var KNOWLEDGE_PROMOTION_REJECT_STORED_HASH = "stored_content_hash_mismatch";
var KNOWLEDGE_PROMOTION_REJECT_HASH = "content_hash_mismatch";
var KNOWLEDGE_PROMOTION_REJECT_VERSION = "candidate_version_mismatch";
var KNOWLEDGE_PROMOTION_REJECT_APPROVAL = "missing_or_expired_approval";
var KNOWLEDGE_PROMOTION_REJECT_RESERVED = "promotion_reserved";
// Candidate staging lives in its own D1 table, intentionally distinct from the
// Golden `assets` / `asset_versions` tables. Approvals are NOT a second
// authority: KNOWLEDGE_PROMOTION reuses the trusted, single-use
// `personal_ai_approval_ledger` together with the `approval_ledger_operations`
// registry (both added additively by migration 0003). There is deliberately NO
// worker code path that registers/mints an approval -- a caller-supplied
// `approved_by` / `approval_receipt` / `promotion_decision` can never authorise
// a write. Approvals enter the ledger only through the trusted Human Gate
// process, which writes to D1 out of band.
var KNOWLEDGE_CANDIDATE_SELECT = "SELECT * FROM knowledge_candidates WHERE candidate_id = ?";
var KNOWLEDGE_CANDIDATE_INSERT = "INSERT INTO knowledge_candidates (candidate_id, asset_id, title, status, content, content_hash, version, provenance, created_at, review_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
var KNOWLEDGE_CANDIDATE_REVIEW_UPDATE = "UPDATE knowledge_candidates SET status = ?, review_state = ? WHERE candidate_id = ? AND status='DRAFT'";
// Recording a review may only act on a pre-promotion candidate. The guarded
// UPDATE makes the legal lifecycle transition atomic: a PROMOTED /
// CANONICAL_READBACK_VERIFIED candidate can never be regressed back to
// APPROVED_FOR_PROMOTION through the review tool (changes === 0 -> rejected).
var KNOWLEDGE_CANDIDATE_REVIEW_RECORD = "UPDATE knowledge_candidates SET status = ?, review_state = ?, review_result = ?, reviewed_at = ? WHERE candidate_id = ? AND status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED_FOR_PROMOTION')";
// The single atomic promotion claim. Only a candidate that is still in the
// reviewed-PASS pre-promotion state can be claimed; a concurrent review FAIL
// (which moves the candidate to PENDING_REVIEW) or a competing promotion makes
// this compare-and-swap return changes === 0, so the loser fails closed BEFORE
// consuming an approval or calling the Canonical writer.
var KNOWLEDGE_CANDIDATE_RESERVE = "UPDATE knowledge_candidates SET status = ? WHERE candidate_id = ? AND status = ? AND review_state = ?";
// Guarded lifecycle transitions. The promotion only ever advances a candidate it
// still owns (PROMOTION_RESERVED -> PROMOTED -> CANONICAL_READBACK_VERIFIED) and
// can release a failed claim (PROMOTION_RESERVED -> APPROVED_FOR_PROMOTION).
// Because each guarded UPDATE pins the expected current status, a promotion can
// never overwrite a concurrently recorded state (e.g. a FAIL) and a terminal
// candidate can never be regressed.
var KNOWLEDGE_CANDIDATE_GUARDED_UPDATE = "UPDATE knowledge_candidates SET status = ? WHERE candidate_id = ? AND status = ?";
var KNOWLEDGE_CANDIDATE_STATUS_UPDATE = "UPDATE knowledge_candidates SET status = ? WHERE candidate_id = ?";
// The trusted approval ledger (single authority, reused for
// decision_write / knowledge_write / KNOWLEDGE_PROMOTION).
// The select returns only LIVE approvals (unconsumed AND not invalidated), so a
// FAIL-revoked approval can never be replayed even if a later PASS restores the
// candidate's APPROVED_FOR_PROMOTION status.
// The single-use authority is the LEGACY `consumed_at` column (INTEGER epoch),
// shared with the Site WebAuthn CAS. The Worker-only `consumed`/`state` columns
// are a mirror updated in the same statement; the gate reads/writes the legacy
// field so a Site-minted approval and a Worker consume can never diverge.
var APPROVAL_LEDGER_SELECT = "SELECT approval_id, operation, asset_type, candidate_id, candidate_version, content_hash, review_result, approved_by, expires_at, state, consumed, consume_count, invalidated, consumed_at FROM personal_ai_approval_ledger WHERE operation = ? AND candidate_id = ? AND candidate_version = ? AND content_hash = ? AND consumed_at IS NULL AND invalidated = 0 ORDER BY expires_at DESC";
var APPROVAL_LEDGER_CONSUME = "UPDATE personal_ai_approval_ledger SET consumed = 1, state = 'CONSUMED', consume_count = consume_count + 1, consumed_at = ? WHERE approval_id = ? AND operation = ? AND consumed_at IS NULL AND invalidated = 0";
// Atomic stale-approval revocation. Only UNCONSUMED, not-yet-invalidated
// approvals bound to the operation+candidate are transitioned; a consumed
// approval (evidence of a completed/pending write) is never rewritten.
var APPROVAL_LEDGER_INVALIDATE = "UPDATE personal_ai_approval_ledger SET invalidated = 1, state = 'INVALIDATED', invalidated_at = ? WHERE operation = ? AND candidate_id = ? AND consumed_at IS NULL AND invalidated = 0";
var KNOWLEDGE_PROMOTION_APPROVAL_INVALIDATED = "INVALIDATED";
function knowledgePromotionOutcome(resultStatus, extra) {
  const body = { contract: KNOWLEDGE_CANDIDATE_CONTRACT, status: resultStatus, ...(extra || {}) };
  return { isError: false, text: JSON.stringify(body), structuredContent: body };
}
// Historical contract validator retained for compatibility diagnostics only.
// Canonical promotion exclusively uses guardedKnowledgePromote and production atomic approval.
function validateCandidateGate(candidate, supplied, approval, nowMs) {
  const reject = (reason) => ({ ok: false, reason });
  if (!candidate || typeof candidate !== "object") return reject(KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_MISSING);
  if (String(candidate.status) !== KNOWLEDGE_CANDIDATE_APPROVED_FOR_PROMOTION) return reject(KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_STATE);
  if (String(candidate.review_state) !== KNOWLEDGE_CANDIDATE_REVIEW_PASS) return reject(KNOWLEDGE_PROMOTION_REJECT_STORED_REVIEW);
  const src = supplied && typeof supplied === "object" ? supplied : {};
  if (String(src.recomputed_content_hash) !== String(candidate.content_hash)) return reject(KNOWLEDGE_PROMOTION_REJECT_STORED_HASH);
  if (String(src.content_hash) !== String(candidate.content_hash)) return reject(KNOWLEDGE_PROMOTION_REJECT_HASH);
  if (Number(src.candidate_version) !== Number(candidate.version)) return reject(KNOWLEDGE_PROMOTION_REJECT_VERSION);
  if (String(src.review_result) !== KNOWLEDGE_CANDIDATE_REVIEW_PASS) return reject(KNOWLEDGE_PROMOTION_REJECT_REVIEW);
  if (!approval || typeof approval !== "object") return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  // The approval must come from the shared trusted ledger, bound to the
  // KNOWLEDGE_PROMOTION operation. A wrong operation / a receipt that is not in
  // the ledger can never authorise the write.
  if (String(approval.operation) !== KNOWLEDGE_PROMOTION_OPERATION) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (String(approval.candidate_id) !== String(candidate.candidate_id)) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (Number(approval.candidate_version) !== Number(candidate.version)) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (String(approval.content_hash) !== String(candidate.content_hash)) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (String(approval.review_result) !== KNOWLEDGE_CANDIDATE_REVIEW_PASS) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (!String(approval.approval_id || "").trim()) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (!String(approval.approved_by || "").trim()) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  // A FAIL-revoked (stale) approval is permanently dead: even if the candidate
  // is later re-PASSed with the same version/hash it can never authorise a write.
  if (approval.invalidated === true || Number(approval.invalidated) === 1) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (String(approval.state || "") === KNOWLEDGE_PROMOTION_APPROVAL_INVALIDATED) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  if (approval.consumed === true || Number(approval.consumed) === 1) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  // The legacy `consumed_at` (INTEGER epoch, shared with the Site WebAuthn CAS)
  // is the single-use authority. A non-null value means another consumer has
  // already spent this approval, so it is rejected even if the mirror lags.
  if (approval.consumed_at !== null && approval.consumed_at !== void 0 && String(approval.consumed_at).trim() !== "") return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  const now = Number.isFinite(nowMs) ? Number(nowMs) : Date.now();
  // `expires_at` is INTEGER epoch seconds in the production/union ledger and an
  // ISO string in the repo-only schema; accept both, fail closed on neither.
  const expiresRaw = approval.expires_at;
  const expiresNumeric = Number(expiresRaw);
  const expires = String(expiresRaw ?? "").trim() !== "" && Number.isFinite(expiresNumeric)
    ? expiresNumeric * 1000
    : Date.parse(String(expiresRaw));
  if (!Number.isFinite(expires) || expires <= now) return reject(KNOWLEDGE_PROMOTION_REJECT_APPROVAL);
  return { ok: true, reason: null };
}
async function stageKnowledgeCandidate(env, args) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  if (!env || !env.ASSET_DB) return { isError: true, text: "ASSET_WRITE_UNAVAILABLE" };
  const candidateId = String(input.candidate_id ?? "").trim();
  if (!ASSET_ID_RE.test(candidateId)) return { isError: true, text: "INVALID_ASSET_ID" };
  const assetId = String(input.asset_id ?? candidateId).trim();
  if (!ASSET_ID_RE.test(assetId)) return { isError: true, text: "INVALID_ASSET_ID" };
  if (input.content == null) return { isError: true, text: "INVALID_CONTENT" };
  const canonicalContent = canonicalKnowledgeContent(input.content);
  if (!canonicalContent.trim()) return { isError: true, text: "INVALID_CONTENT" };
  const contentHash = await sha256Hex(canonicalContent);
  const nowIso = (/* @__PURE__ */ new Date()).toISOString();
  const version = Number.isFinite(Number(input.version)) ? Number(input.version) : 1;
  const provenance = input.provenance && typeof input.provenance === "object" ? input.provenance : {};
  try {
    if (!/^knowledge[:-][a-zA-Z0-9:_-]+$/.test(assetId) || !Number.isSafeInteger(version) || version < 1) return {isError:true,text:'INVALID_CANDIDATE_IDENTITY'};
    checkedProvenance(provenance);
    await checkedSchema(env.ASSET_DB, SNAPSHOT);
    await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_INSERT).bind(
      candidateId,
      assetId,
      String(input.title ?? "").trim(),
      KNOWLEDGE_CANDIDATE_DRAFT,
      canonicalContent,
      contentHash,
      version,
      JSON.stringify(provenance),
      nowIso,
      KNOWLEDGE_CANDIDATE_NOT_REVIEWED
    ).run();
  } catch {
    return { isError: true, text: "ASSET_WRITE_FAILED" };
  }
  const candidate = {
    candidate_id: candidateId,
    asset_id: assetId,
    title: String(input.title ?? "").trim(),
    status: KNOWLEDGE_CANDIDATE_DRAFT,
    content: canonicalContent,
    content_hash: contentHash,
    version,
    provenance,
    created_at: nowIso,
    review_state: KNOWLEDGE_CANDIDATE_NOT_REVIEWED
  };
  return { isError: false, text: JSON.stringify({ contract: KNOWLEDGE_CANDIDATE_CONTRACT, staged: true, candidate }), structuredContent: { contract: KNOWLEDGE_CANDIDATE_CONTRACT, staged: true, candidate } };
}
async function recordKnowledgeCandidateReview(env, args) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  if (!env || !env.ASSET_DB) return { isError: true, text: "ASSET_WRITE_UNAVAILABLE" };
  const db = env.ASSET_DB;
  const candidateId = String(input.candidate_id ?? "").trim();
  const reviewResult = String(input.review_result ?? "").trim().toUpperCase();
  if (![KNOWLEDGE_CANDIDATE_REVIEW_PASS, KNOWLEDGE_CANDIDATE_REVIEW_FAIL].includes(reviewResult)) {
    return { isError: true, text: "INVALID_REVIEW_RESULT" };
  }
  // NOTE: approval/approver/receipt fields supplied by the caller are ignored.
  // Recording a review never mints an approval; it can only REVOKE stale ones.
  let candidate;
  try {
    candidate = await db.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind(candidateId).first();
  } catch {
    return { isError: true, text: "ASSET_WRITE_FAILED" };
  }
  if (!candidate) return { isError: true, text: "CANDIDATE_NOT_FOUND" };
  const currentStatus = String(candidate.status);
  // Only pre-promotion states are reviewable. PROMOTED / CANONICAL_READBACK_VERIFIED
  // are terminal: review must never regress them back to APPROVED_FOR_PROMOTION.
  if (![KNOWLEDGE_CANDIDATE_DRAFT, KNOWLEDGE_CANDIDATE_PENDING_REVIEW, KNOWLEDGE_CANDIDATE_APPROVED_FOR_PROMOTION].includes(currentStatus)) {
    return knowledgePromotionOutcome(KNOWLEDGE_PROMOTION_REJECTED, {
      reason: KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_STATE,
      candidate_id: candidateId,
      review_recorded: false
    });
  }
  const nextStatus = reviewResult === KNOWLEDGE_CANDIDATE_REVIEW_PASS
    ? KNOWLEDGE_CANDIDATE_APPROVED_FOR_PROMOTION
    : KNOWLEDGE_CANDIDATE_PENDING_REVIEW;
  const nowIso = (new Date()).toISOString();
  if (typeof input.reviewed_by !== 'string' || !input.reviewed_by.trim() ||
      typeof input.review_evidence_ref !== 'string' || !input.review_evidence_ref.trim() ||
      !/^[a-f0-9]{64}$/.test(input.review_evidence_sha256 ?? '')) {
    return {isError:true,text:'REVIEW_EVIDENCE_REQUIRED'};
  }
  let target;
  try {
    await checkedSchema(db, SNAPSHOT);
    target = await db.prepare('SELECT asset_type,current_version FROM assets WHERE asset_id=?').bind(candidate.asset_id).first();
    if (target && target.asset_type !== 'KNOWLEDGE') return {isError:true,text:'ASSET_TYPE_OWNERSHIP_MISMATCH'};
  } catch { return {isError:true,text:'PRODUCTION_SCHEMA_OR_TARGET_UNAVAILABLE'}; }
  const reviewWrite = db.prepare(`UPDATE knowledge_candidates SET status=?,review_state=?,review_result=?,reviewed_at=?,reviewed_by=?,review_evidence_ref=?,review_evidence_sha256=?,expected_asset_version=? WHERE candidate_id=? AND version=? AND content_hash=? AND reviewed_at IS ? AND status IN ('DRAFT','PENDING_REVIEW','APPROVED_FOR_PROMOTION')`)
    .bind(nextStatus,reviewResult,reviewResult,nowIso,input.reviewed_by,input.review_evidence_ref,input.review_evidence_sha256,target?.current_version??null,candidateId,candidate.version,candidate.content_hash,candidate.reviewed_at??null);
  // A review FAIL must atomically revoke every still-live KNOWLEDGE_PROMOTION
  // approval bound to this candidate. A later PASS therefore requires a NEW
  // trusted Human Gate approval; the revoked one can never be replayed.
  const invalidateWrite = reviewResult === KNOWLEDGE_CANDIDATE_REVIEW_FAIL
    ? db.prepare(APPROVAL_LEDGER_INVALIDATE).bind(nowIso, KNOWLEDGE_PROMOTION_OPERATION, candidateId)
    : null;
  let reviewChanges = 0;
  let invalidatedCount = 0;
  if (typeof db.batch === "function") {
    try {
      const results = await db.batch(invalidateWrite ? [reviewWrite, db.prepare("SELECT CASE WHEN changes()=1 THEN 1 ELSE json('REVIEW_CAS_LOST') END AS ok"), invalidateWrite] : [reviewWrite]);
      reviewChanges = results && results[0] && results[0].meta ? Number(results[0].meta.changes) || 0 : 0;
      if (invalidateWrite) invalidatedCount = results && results[2] && results[2].meta ? Number(results[2].meta.changes) || 0 : 0;
    } catch {
      return { isError: true, text: "ASSET_WRITE_FAILED" };
    }
  } else {
    // No atomic batch available. A FAIL cannot guarantee both the status change
    // and the stale-approval revocation, so it fails closed rather than leave a
    // live approval that a later PASS could resurrect.
    if (invalidateWrite) return { isError: true, text: "ASSET_WRITE_FAILED" };
    try {
      const res = await reviewWrite.run();
      reviewChanges = res && res.meta ? Number(res.meta.changes) || 0 : 1;
    } catch {
      return { isError: true, text: "ASSET_WRITE_FAILED" };
    }
  }
  if (reviewChanges < 1) {
    // The guarded UPDATE found no reviewable candidate (e.g. it was promoted
    // concurrently). No status regress; report the illegal transition.
    return knowledgePromotionOutcome(KNOWLEDGE_PROMOTION_REJECTED, {
      reason: KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_STATE,
      candidate_id: candidateId,
      review_recorded: false
    });
  }
  const body = {
    contract: KNOWLEDGE_CANDIDATE_CONTRACT,
    candidate_id: candidateId,
    status: nextStatus,
    review_state: reviewResult,
    approvals_invalidated: invalidatedCount
  };
  return { isError: false, text: JSON.stringify(body), structuredContent: body };
}
async function createKnowledgeCandidate(env, args) {
  // Callable candidate-intake entry point. Persists an independent DRAFT
  // candidate record (never a Golden asset). Creating a candidate does NOT
  // approve or promote anything.
  const staged = await stageKnowledgeCandidate(env, args);
  return staged;
}
async function readKnowledgeCandidate(env, args) {
  // Independent read by candidate_id. Any authorised agent/session can read a
  // candidate another agent persisted; the record is never conflated with a
  // Canonical asset.
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  if (!env || !env.ASSET_DB) return { isError: true, text: "ASSET_WRITE_UNAVAILABLE" };
  const candidateId = String(input.candidate_id ?? "").trim();
  if (!ASSET_ID_RE.test(candidateId)) return { isError: true, text: "INVALID_ASSET_ID" };
  let row;
  try {
    row = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind(candidateId).first();
  } catch {
    return { isError: true, text: "ASSET_WRITE_FAILED" };
  }
  if (!row) return { isError: true, text: "CANDIDATE_NOT_FOUND" };
  let parsedContent = row.content;
  try {
    parsedContent = JSON.parse(row.content);
  } catch {
    parsedContent = row.content;
  }
  let provenance = row.provenance;
  try {
    provenance = JSON.parse(row.provenance);
  } catch {
    provenance = {};
  }
  const candidate = {
    candidate_id: row.candidate_id,
    asset_id: row.asset_id,
    title: row.title,
    status: row.status,
    content: parsedContent,
    content_hash: row.content_hash,
    version: Number(row.version),
    provenance,
    created_at: row.created_at,
    review_state: row.review_state,
    review_result: row.review_result ?? null
  };
  const body = { contract: KNOWLEDGE_CANDIDATE_CONTRACT, found: true, candidate };
  return { isError: false, text: JSON.stringify(body), structuredContent: body };
}
async function submitKnowledgeCandidateForReview(env, args) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  if (!env || !env.ASSET_DB) return { isError: true, text: "ASSET_WRITE_UNAVAILABLE" };
  const candidateId = String(input.candidate_id ?? "").trim();
  if (!ASSET_ID_RE.test(candidateId)) return { isError: true, text: "INVALID_ASSET_ID" };
  let row;
  try {
    row = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind(candidateId).first();
  } catch {
    return { isError: true, text: "ASSET_WRITE_FAILED" };
  }
  if (!row) return { isError: true, text: "CANDIDATE_NOT_FOUND" };
  if (String(row.status) !== KNOWLEDGE_CANDIDATE_DRAFT) {
    return knowledgePromotionOutcome(KNOWLEDGE_PROMOTION_REJECTED, {
      reason: KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_STATE,
      candidate_id: candidateId
    });
  }
  try {
    const changed = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_REVIEW_UPDATE).bind(KNOWLEDGE_CANDIDATE_PENDING_REVIEW, KNOWLEDGE_CANDIDATE_NOT_REVIEWED, candidateId).run();
    if (changed.meta?.changes !== 1) return {isError:true,text:"CANDIDATE_STATE_CHANGED"};
  } catch {
    return { isError: true, text: "ASSET_WRITE_FAILED" };
  }
  const body = { contract: KNOWLEDGE_CANDIDATE_CONTRACT, candidate_id: candidateId, status: KNOWLEDGE_CANDIDATE_PENDING_REVIEW, review_state: KNOWLEDGE_CANDIDATE_NOT_REVIEWED };
  return { isError: false, text: JSON.stringify(body), structuredContent: body };
}
// NOTE: there is deliberately no worker function that registers/mints a
// promotion approval. The worker can only READ and atomically CONSUME approvals
// from the trusted `personal_ai_approval_ledger`; it can never mint one. This is
// what makes a caller-supplied approved_by/approval_receipt/promotion_decision
// incapable of authorising a write.
// Gated promotion: candidate -> validateCandidateGate -> atomic promotion
// reservation -> single-use approval consume -> Golden Writer
// (writeKnowledgeCandidate) -> guarded status transitions -> authoritative
// read-back.
//
// The reservation is the linearization point against a review FAIL. A promotion
// that cannot atomically claim a reviewed-PASS candidate fails closed with
// write_calls === 0 (no approval consume, no Canonical write), and a review FAIL
// that arrives after the claim is rejected because its guarded UPDATE only
// matches pre-promotion states.
async function releaseKnowledgeCandidateReservation(db, candidateId) {
  try {
    const result = await db.prepare(KNOWLEDGE_CANDIDATE_GUARDED_UPDATE).bind(KNOWLEDGE_CANDIDATE_APPROVED_FOR_PROMOTION, candidateId, KNOWLEDGE_CANDIDATE_PROMOTION_RESERVED).run();
    return result && result.meta ? Number(result.meta.changes) || 0 : 0;
  } catch {
    return 0;
  }
}
async function promoteKnowledgeCandidate(env, args) {
  return guardedKnowledgePromote(env, args, { writer: writeKnowledgeCandidate, verifyVersion: verifyKnowledgeVersion });
}
async function toolPromoteKnowledgeCandidate(env, args) {
  try {
    return await promoteKnowledgeCandidate(env, args);
  } catch (err2) {
    return { isError: true, text: `KNOWLEDGE_PROMOTION_FAILED: ${err2?.message || "unknown"}` };
  }
}
var DECISION_WRITE_CONTRACT = "PERSONAL_AI_DECISION_WRITER_V0.1";
var DECISION_INGESTION_CONTRACT = "PERSONAL_AI_DECISION_INGESTION_V0.1";
var DECISION_ASSET_TYPE = "DECISION";
var DECISION_WRITE_STATUS = "accepted";
var DECISION_HASH_RE = /^[0-9a-f]{64}$/;
var DECISION_DISPATCH_OUTCOMES = ["PENDING", "DISPATCHED", "FAILED"];
var DECISION_REQUIRED_FIELDS = ["review_verdict", "dispatch_outcome", "promotion_decision", "user_choice", "user_outcome"];
var DECISION_INSERT_SQL = "INSERT INTO asset_versions (asset_id, version, content, content_hash, provenance, verification, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)";
var DECISION_VERIFY_SQL = "SELECT a.asset_id AS asset_id, a.asset_type AS asset_type, a.current_version AS asset_version, a.content_hash AS asset_content_hash, a.status AS asset_status, v.version AS version_version, v.content AS version_content, v.content_hash AS version_content_hash, v.created_by AS version_created_by, v.provenance AS version_provenance, v.verification AS version_verification FROM assets a JOIN asset_versions v ON v.asset_id = a.asset_id AND v.version = a.current_version WHERE a.asset_id = ?";
function normalizeDecision(input) {
const src = input && typeof input === "object" && !Array.isArray(input) ? input : {};
const missing = DECISION_REQUIRED_FIELDS.filter((key) => src[key] === null || src[key] === void 0 || typeof src[key] === "string" && !src[key].trim());
const invalid = [];
const verdict = src.review_verdict == null ? null : String(src.review_verdict).trim().toUpperCase();
if (verdict !== null && !REVIEW_VERDICTS.includes(verdict)) invalid.push("review_verdict");
const dispatch = src.dispatch_outcome == null ? null : String(src.dispatch_outcome).trim().toUpperCase();
if (dispatch !== null && !DECISION_DISPATCH_OUTCOMES.includes(dispatch)) invalid.push("dispatch_outcome");
const complete = missing.length === 0 && invalid.length === 0;
return { contract: DECISION_INGESTION_CONTRACT, status: complete ? "VERIFIED" : "INCOMPLETE", complete, verified: complete, missing, invalid, record: { review_verdict: verdict, dispatch_outcome: dispatch } };
}
function canonicalDecisionContent(content) {
const sorted = (value) => {
if (value === null || typeof value !== "object") return JSON.stringify(value);
if (Array.isArray(value)) return "[" + value.map(sorted).join(",") + "]";
return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + sorted(value[key])).join(",") + "}";
};
return typeof content === "string" ? content : sorted(content);
}
function buildDecisionProvenance(input) {
const now = (/* @__PURE__ */ new Date()).toISOString();
const capturedAt = String(input.captured_at ?? now);
const promotedAt = String(input.promoted_at ?? now);
const sourceVersion = String(input.source_version ?? "v1");
return {
source: { identity: String(input.evidence_ref), location: String(input.source_location ?? "cloud://decision-registry") },
source_version: sourceVersion,
content_version: String(input.content_version ?? sourceVersion),
canonical_version: input.canonical_version,
content_hash: input.content_hash,
verification: {
method: "recompute_content_hash",
evidence: { checked_by: "decision_ingestion_writer", recomputed: input.content_hash, verified_at: promotedAt },
verified_at: promotedAt,
expected_content_hash: input.content_hash,
content_hash_matches: true
},
promotion: { decision: String(input.promotion_decision), event_id: String(input.promotion_event), decided_at: String(input.decided_at), actor: String(input.actor ?? "cloud-agent") },
captured_at: capturedAt,
promoted_at: promotedAt,
supersedes: Array.isArray(input.supersedes) ? input.supersedes.slice() : [],
superseded_by: null
};
}
async function verifyDecisionVersion(db, assetId, expectedVersion, expectedHash, expectedContent) {
let row;
try {
row = await db.prepare(DECISION_VERIFY_SQL).bind(assetId).first();
} catch {
return false;
}
if (!row) return false;
if (String(row.asset_type) !== DECISION_ASSET_TYPE) return false;
if (Number(row.asset_version) !== Number(expectedVersion)) return false;
if (Number(row.version_version) !== Number(expectedVersion)) return false;
if (String(row.asset_content_hash) !== String(expectedHash)) return false;
if (String(row.version_content_hash) !== String(expectedHash)) return false;
if (expectedContent !== void 0 && String(row.version_content) !== String(expectedContent)) return false;
if (String(row.asset_status) !== DECISION_WRITE_STATUS) return false;
const createdBy = row.version_created_by == null ? "" : String(row.version_created_by).trim();
if (!createdBy) return false;
const evaluation = evaluateAssetProvenance(parseAssetJson(row.version_provenance), { content_hash: expectedHash, canonical_version: expectedVersion, verification: parseAssetJson(row.version_verification) });
if (evaluation.status !== PROVENANCE_STATUS_VERIFIED || evaluation.verified !== true) return false;
return true;
}
async function writeDecisionRecord(env, args) {
if (!env || !env.ASSET_DB) return { isError: true, text: "ASSET_WRITE_UNAVAILABLE" };
if (args === null || typeof args !== "object" || Array.isArray(args)) return { isError: true, text: "INVALID_INPUT" };
const input = args;
if (input.asset_type != null && String(input.asset_type).trim().toUpperCase() !== DECISION_ASSET_TYPE) return { isError: true, text: "INVALID_ASSET_TYPE" };
const suppliedAssetId = input.asset_id == null ? "" : String(input.asset_id).trim();
let decisionId = String(input.decision_id ?? "").trim();
if (suppliedAssetId) {
if (!suppliedAssetId.startsWith("decision:")) return { isError: true, text: "INVALID_ASSET_ID" };
const fromAsset = suppliedAssetId.slice("decision:".length);
if (decisionId && decisionId !== fromAsset) return { isError: true, text: "INVALID_ASSET_ID" };
if (!decisionId) decisionId = fromAsset;
}
if (!decisionId) decisionId = String(input.task_id ?? "").trim();
const assetId = "decision:" + decisionId;
if (!decisionId || !ASSET_ID_RE.test(decisionId) || !ASSET_ID_RE.test(assetId)) return { isError: true, text: "INVALID_ASSET_ID" };
const taskId = String(input.task_id ?? "").trim();
if (!taskId) return { isError: true, text: "INVALID_TASK_ID" };
if (input.review_verdict != null && !REVIEW_VERDICTS.includes(String(input.review_verdict).trim().toUpperCase())) return { isError: true, text: "INVALID_REVIEW_VERDICT" };
if (input.dispatch_outcome != null && !DECISION_DISPATCH_OUTCOMES.includes(String(input.dispatch_outcome).trim().toUpperCase())) return { isError: true, text: "INVALID_DISPATCH_OUTCOME" };
if (!input.promotion_decision || !input.promotion_event) return { isError: true, text: "INVALID_PROMOTION" };
const agentRecommendation = String(input.agent_recommendation ?? "").trim();
if (!agentRecommendation) return { isError: true, text: "INVALID_AGENT_RECOMMENDATION" };
const userChoice = input.user_choice == null ? "" : String(input.user_choice);
if (!userChoice.trim()) return { isError: true, text: "INVALID_USER_CHOICE" };
const userOutcome = input.user_outcome == null ? "" : String(input.user_outcome);
if (!userOutcome.trim()) return { isError: true, text: "INVALID_USER_OUTCOME" };
const derivedOverride = userChoice.trim() !== agentRecommendation;
const overrideReason = input.override_reason == null ? "" : String(input.override_reason).trim();
if (derivedOverride && !overrideReason) return { isError: true, text: "INVALID_OVERRIDE_REASON" };
if (input.user_override !== void 0 && input.user_override !== null && Boolean(input.user_override) !== derivedOverride) return { isError: true, text: "INVALID_OVERRIDE" };
const decidedAt = String(input.decided_at ?? "").trim();
if (!decidedAt || Number.isNaN(Date.parse(decidedAt))) return { isError: true, text: "INVALID_DECIDED_AT" };
const evidenceRef = String(input.evidence_ref ?? "").trim();
if (!evidenceRef) return { isError: true, text: "INVALID_EVIDENCE_REF" };
const normalized = normalizeDecision(input);
if (normalized.status !== "VERIFIED" || normalized.verified !== true) return { isError: true, text: "INCOMPLETE_DECISION" };
const content = {
decision_id: decisionId,
task_id: taskId,
review_verdict: normalized.record.review_verdict,
dispatch_outcome: normalized.record.dispatch_outcome,
promotion_decision: String(input.promotion_decision),
promotion_event: String(input.promotion_event),
agent_recommendation: agentRecommendation,
user_choice: userChoice,
user_outcome: userOutcome,
user_override: derivedOverride,
override_reason: derivedOverride ? overrideReason : null,
outcome_feedback: input.outcome_feedback == null ? null : input.outcome_feedback,
evidence_ref: evidenceRef,
decided_at: decidedAt
};
const canonicalContent = canonicalDecisionContent(content);
const contentHash = await sha256Hex(canonicalContent);
if (!DECISION_HASH_RE.test(contentHash)) return { isError: true, text: "ASSET_WRITE_FAILED" };
const nowIso = (/* @__PURE__ */ new Date()).toISOString();
const db = env.ASSET_DB;
let existing;
try {
existing = await db.prepare("SELECT asset_id, current_version, content_hash, updated_at FROM assets WHERE asset_id = ?").bind(assetId).first();
} catch {
return { isError: true, text: "ASSET_WRITE_FAILED" };
}
const schemaVersion = String(input.schema_version ?? "v0.1");
const title = String(input.title ?? "").trim() || `Decision ${decisionId}`;
if (existing && normalizeProvenanceHash(existing.content_hash) === contentHash) {
const currentVersion = Number(existing.current_version) || 1;
const present = await verifyDecisionVersion(db, assetId, currentVersion, contentHash, canonicalContent);
if (!present) return { isError: true, text: "ASSET_WRITE_FAILED" };
const replay = {
contract: DECISION_WRITE_CONTRACT, asset_id: assetId, asset_type: DECISION_ASSET_TYPE, schema_version: schemaVersion, title,
status: "IDEMPOTENT", created: false, idempotent: true, version: currentVersion, previous_version: currentVersion > 1 ? currentVersion - 1 : null,
content_hash: contentHash, provenance_status: PROVENANCE_STATUS_VERIFIED, provenance_verified: true, promotion_event: String(input.promotion_event),
supersedes: [], user_override: derivedOverride, user_choice: userChoice, agent_recommendation: agentRecommendation, updated_at: existing.updated_at ?? nowIso
};
return { isError: false, text: JSON.stringify(replay), structuredContent: replay };
}
const previousVersion = existing ? Number(existing.current_version) || 0 : 0;
const version = previousVersion + 1;
const callerSupersedes = Array.isArray(input.supersedes) ? input.supersedes.slice() : [];
const supersedes = previousVersion > 0 ? [...callerSupersedes, String(previousVersion)] : callerSupersedes;
const createdBy = String(input.created_by ?? input.actor ?? "cloud-agent").trim() || "cloud-agent";
const provenance = buildDecisionProvenance({ ...input, actor: createdBy, canonical_version: version, content_hash: contentHash, supersedes });
const verification = provenance.verification;
const assetWrite = existing ? db.prepare("UPDATE assets SET schema_version = ?, title = ?, status = ?, current_version = ?, content_hash = ?, updated_at = ? WHERE asset_id = ?").bind(schemaVersion, title, DECISION_WRITE_STATUS, version, contentHash, nowIso, assetId) : db.prepare("INSERT INTO assets (asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)").bind(assetId, DECISION_ASSET_TYPE, schemaVersion, title, DECISION_WRITE_STATUS, version, contentHash, nowIso, nowIso);
const versionWrite = db.prepare(DECISION_INSERT_SQL).bind(assetId, version, canonicalContent, contentHash, JSON.stringify(provenance), JSON.stringify(verification), createdBy, nowIso);
if (typeof db.batch !== "function") return { isError: true, text: "ASSET_WRITE_FAILED" };
try {
await db.batch([assetWrite, versionWrite]);
} catch {
return { isError: true, text: "ASSET_WRITE_FAILED" };
}
const persisted = await verifyDecisionVersion(db, assetId, version, contentHash, canonicalContent);
if (!persisted) return { isError: true, text: "ASSET_WRITE_FAILED" };
const result = {
contract: DECISION_WRITE_CONTRACT, asset_id: assetId, asset_type: DECISION_ASSET_TYPE, schema_version: schemaVersion, title,
status: "WRITTEN", created: !existing, idempotent: false, version, previous_version: previousVersion > 0 ? previousVersion : null,
content_hash: contentHash, provenance_status: PROVENANCE_STATUS_VERIFIED, provenance_verified: true, promotion_event: provenance.promotion.event_id,
supersedes: provenance.supersedes, user_override: derivedOverride, user_choice: userChoice, agent_recommendation: agentRecommendation, updated_at: nowIso
};
return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
async function toolWriteDecisionRecord(env, args) {
try {
return await writeDecisionRecord(env, args);
} catch {
return { isError: true, text: "ASSET_WRITE_FAILED" };
}
}

var TOOLS = [
  {
    name: "submit_task",
    description: "Submit a structured task to the Cloud Agent via GitHub repository_dispatch.",
    inputSchema: {
      type: "object",
      properties: {
        goal: { type: "string" },
        instructions: { type: "array", items: { type: "string" } },
        acceptance: { type: "array", items: { type: "string" } },
        expected_files: { type: "array", items: { type: "string" } },
        mode: { type: ["string", "null"], description: "Optional execution mode passed through to the Gate mode resolver. Supported values: readonly / write (missing or empty defaults to write; any other value fails closed)." },
        project_id: { type: ["string", "null"], description: "Optional active-project lineage id." },
        root_task_id: { type: ["string", "null"], description: "Optional lineage root task id." },
        parent_task_id: { type: ["string", "null"], description: "Optional immediate parent task id." }
      },
      required: ["goal", "instructions", "acceptance"]
    }
  },
  {
    name: "get_task_execution_status",
    description: "Strict read-only observation of a registered task's named GitHub workflow run, with historical artifact fallback. No registry writes or events. Preserves run attempt and source times; missing mapping is unknown. One selected task run, never Agent availability, business success or independent acceptance. Observations expire after ttl_seconds.",
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
    inputSchema: { type: "object", properties: { task_id: { type: "string" } }, required: ["task_id"], additionalProperties: false },
    outputSchema: { type: "object", additionalProperties: true }
  },
  {
    name: "get_task_result",
    description: "Read the execution_result.json produced by the Cloud Agent for a task_id.",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string" } },
      required: ["task_id"]
    },
    outputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        status: { type: "string" },
        round: { type: "number" },
        execution_summary: { type: "string" },
        commit: { type: "string" },
        tests: { type: ["string", "object", "array", "null"] },
        artifacts: { type: ["array", "object"] },
        execution_result_json: { type: ["object", "array", "null"] },
        evidence: { type: ["object", "array", "null"] }
      },
      additionalProperties: true
    }
  },
  {
    name: "list_pending_results",
    description: "List tasks that have finished and await review, plus failed and blocked tasks. Returns buckets pending_review / failed / blocked. Optional project_id / root_task_id lineage scope deterministically restricts the result to one active lineage and reports excluded_by_lineage; unscoped behavior is unchanged. Set active_project=true, or configure the live Supervisor/advancement caller with PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT, to scope to the configured active project lineage (PERSONAL_AI_ACTIVE_PROJECT_ID, default cloud-assets-activation).",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: ["string", "null"], description: "Optional active-project lineage id to scope the listing." },
        root_task_id: { type: ["string", "null"], description: "Optional lineage root task id to scope the listing." },
        active_project: { type: ["boolean", "null"], description: "When true and no explicit scope is supplied, scope to the configured active project lineage." },
        scope: {
          type: ["object", "null"],
          properties: {
            project_id: { type: ["string", "null"] },
            root_task_id: { type: ["string", "null"] }
          },
          additionalProperties: false
        }
      },
      required: []
    }
  },
  {
    name: "plan_task_redispatch",
    description: "Return an idempotent, deduplicated re-dispatch plan for an accepted Cloud Agent task whose queued run never started a job. Reuses the same task_id and a deterministic retry:<task_id>:<attempt> idempotency key. Read-only: it plans but never dispatches, so single-writer safety is preserved.",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string" } },
      required: ["task_id"]
    },
    outputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        should_retry: { type: "boolean" },
        same_task_id: { type: "boolean" },
        next_attempt: { type: "number" },
        idempotency_key: { type: ["string", "null"] },
        retry_claim_scope: { type: ["string", "null"] },
        dispatch_state: { type: "string" },
        recommended_action: { type: "string" },
        retryable: { type: "boolean" },
        reason: { type: "string" }
      },
      additionalProperties: true
    }
  },
  {
    name: "retry_task_dispatch",
    description: "Bounded, idempotent retry executor for an eligible unconfirmed Cloud Agent task. It consumes the read-only plan_task_redispatch decision, claims the deterministic retry:<task_id>:<attempt> idempotency key through the existing D1 task_dispatch_markers INSERT OR IGNORE before any redispatch, and re-issues the SAME task_id. It never retries an authoritative completed/reviewed task, never fabricates a terminal verdict, never mutates review state, and stops (inspect) once the bounded attempt policy is exhausted.",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string" } },
      required: ["task_id"]
    },
    outputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        retried: { type: "boolean" },
        dispatched: { type: "boolean" },
        idempotent: { type: "boolean" },
        dispatch_state: { type: "string" },
        reason: { type: "string" },
        idempotency_key: { type: ["string", "null"] },
        next_attempt: { type: ["number", "null"] }
      },
      additionalProperties: true
    }
  },
  {
    name: "mark_reviewed",
    description: "Record a review verdict for a completed task and close its pending review state. On an authoritative terminal PASS, an explicit pre-authorized approved_next_task may be dispatched exactly once as a child gpt_task; the worker never invents next work.",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        verdict: { type: "string", enum: REVIEW_VERDICTS },
        note: { type: ["string", "null"] },
        approved_next_task: {
          type: ["object", "null"],
          properties: {
            goal: { type: "string" },
            instructions: { type: "array", items: { type: "string" } },
            acceptance: { type: "array", items: { type: "string" } },
            expected_files: { type: "array", items: { type: "string" } },
            project_id: { type: ["string", "null"] },
            root_task_id: { type: ["string", "null"] }
          },
          required: ["goal", "instructions", "acceptance"]
        }
      },
      required: ["task_id", "verdict"]
    },
    outputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        reviewed: { type: "boolean" },
        verdict: { type: "string", enum: REVIEW_VERDICTS },
        reviewed_at: { type: "string" },
        review_event: { type: ["object", "null"] },
        child_dispatch: { type: ["object", "null"] },
        idempotent: { type: "boolean" }
      },
      additionalProperties: true
    }
  },
  {
    name: "search_assets",
    description: "Search the Personal AI Cloud Asset canonical by type, subtype, and query. Read only; returns metadata without asset content.",
    inputSchema: {
      type: "object",
      properties: {
        asset_type: { type: "string", description: "Canonical asset type: reality, decision, knowledge, or skill." },
        subtype: { type: "string" },
        query: { type: "string" },
        limit: { type: "integer", minimum: 1, maximum: 100 }
      },
      required: []
    },
    outputSchema: {
      type: "object",
      properties: { assets: { type: "array" } },
      additionalProperties: false
    }
  },
  {
    name: "get_asset",
    description: "Read one canonical Personal AI Cloud Asset by asset_id. Read only; returns the current version, provenance, and canonical content.",
    inputSchema: {
      type: "object",
      properties: { asset_id: { type: "string" } },
      required: ["asset_id"]
    }
  },
  {
    name: "write_knowledge_candidate",
    description: "Controlled KNOWLEDGE candidate lifecycle + canonical writer. `candidate_operation` selects create (persist an independent DRAFT candidate), read (independent read by candidate_id), submit_review (DRAFT -> PENDING_REVIEW), review (record PASS/FAIL), or promote (the sole fail-closed Canonical write gate; default). Promotion requires a real single-use Human Gate approval in the shared personal_ai_approval_ledger bound to candidate_id/version/content_hash/review_result/approved_by/expires_at/KNOWLEDGE_PROMOTION. Write operations require write scope; read requires asset.read scope. Never used for non-KNOWLEDGE assets.",
    inputSchema: {
      type: "object",
      properties: {
        review_evidence_sha256: { type: "string" },
        review_evidence_ref: { type: "string" },
        reviewed_by: { type: "string" },
        approval_id: { type: "string" },
        candidate_version: { type: "integer" },
        candidate_operation: { type: "string", enum: ["create", "read", "submit_review", "review", "promote"] },
        asset_id: { type: "string" },
        candidate_id: { type: "string" },
        asset_type: { type: "string", enum: ["KNOWLEDGE"] },
        title: { type: "string" },
        content: { type: ["string", "object", "array"] },
        review_result: { type: "string", enum: ["PASS", "FAIL"] },
        schema_version: { type: "string" },
        status: { type: "string" },
        source_identity: { type: "string" },
        source_location: { type: "string" },
        source_version: { type: "string" },
        content_version: { type: "string" },
        source_content_hash: { type: "string" },
        promotion_decision: { type: "string" },
        promotion_event: { type: "string" },
        captured_at: { type: "string" },
        promoted_at: { type: "string" }
      },
      required: []
    },
    outputSchema: {
      type: "object",
      properties: {
        asset_id: { type: "string" },
        asset_type: { type: "string" },
        version: { type: "number" },
        content_hash: { type: "string" },
        idempotent: { type: "boolean" },
        created: { type: "boolean" },
        provenance_status: { type: "string" }
      },
      additionalProperties: true
    }
  },
  {
    name: "write_skill_candidate",
    description: "Controlled canonical writer for a SKILL candidate. Write only; never used for non-SKILL assets.",
    inputSchema: {
      type: "object",
      properties: {
        asset_id: { type: "string" },
        candidate_id: { type: "string" },
        asset_type: { type: "string", enum: ["SKILL"] },
        title: { type: "string" },
        content: { type: ["string", "object", "array"] },
        schema_version: { type: "string" },
        source_identity: { type: "string" },
        source_location: { type: "string" },
        source_version: { type: "string" },
        content_version: { type: "string" },
        source_content_hash: { type: "string" },
        promotion_decision: { type: "string" },
        promotion_event: { type: "string" },
        captured_at: { type: "string" },
        promoted_at: { type: "string" }
      },
      required: ["title", "content"]
    }
  },
  {
    name: "write_decision_record",
    description: "Controlled canonical writer for a normalized VERIFIED DECISION record. Write only; never used for non-DECISION assets.",
    inputSchema: {
      type: "object",
      properties: {
        asset_type: { type: "string", enum: ["DECISION"] },
        review_verdict: { type: "string", enum: REVIEW_VERDICTS }
      },
      additionalProperties: true,
      required: []
    },
    outputSchema: { type: "object", additionalProperties: true }
  }
];
function jsonRpcError(cors, id, err) {
  const info = err && err.mcpError ? err.mcpError : { code: -32603, message: "Internal error", data: null };
  const error = { code: info.code, message: info.message };
  if (info.data) error.data = info.data;
  return json({ jsonrpc: "2.0", id, error }, 200, cors);
}
// task.read: fixed-project, pure-read branch. No registry synchronization.
const TASK_READ_SCOPE = 'task.read';
const TASK_READ_PROJECT = 'cloud-assets-activation';
function isTaskRead(auth) {
  return auth?.scopes?.length === 1 && auth.scopes[0] === TASK_READ_SCOPE &&
    auth.payload?.task_project === TASK_READ_PROJECT;
}
function taskReadError(code) { return {isError:true,text:code}; }
function taskReadTools() {
  return [{name:'get_task_result',description:'Pure read of one registry-verified task in cloud-assets-activation; no registry sync.',
    inputSchema:{type:'object',additionalProperties:false,properties:{task_id:{type:'string',pattern:'^cf-[a-f0-9]{12}$'}},required:['task_id']}},
    {name:'list_pending_results',description:'Pure read of pending-review/failed/blocked/unconfirmed buckets in fixed project cloud-assets-activation; not all running tasks.',
    inputSchema:{type:'object',additionalProperties:false,properties:{project_id:{type:'string',enum:[TASK_READ_PROJECT]}},required:[]}}]
    .map(t=>({...t,annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:true}}));
}
function taskReadArgs(args, detail=false) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return false;
  const allowed = detail ? ['task_id'] : ['project_id'];
  if (Object.keys(args).some(k=>!allowed.includes(k))) return false;
  return detail ? typeof args.task_id === 'string' && /^cf-[a-f0-9]{12}$/.test(args.task_id) :
    !Object.hasOwn(args,'project_id') || args.project_id === TASK_READ_PROJECT;
}
async function taskReadIndex(env) {
  if (!env.TASK_REGISTRY) throw Error('REGISTRY_UNAVAILABLE');
  const index = new Map(), seen = new Set();
  let cursor;
  for (let page=0; page<100; page++) {
    const listed = await env.TASK_REGISTRY.list({prefix:REG_PREFIX,...(cursor?{cursor}:{})});
    if (!listed || !Array.isArray(listed.keys) || typeof listed.list_complete !== 'boolean') throw Error('REGISTRY_PAGE_INVALID');
    for (const key of listed.keys) {
      if (typeof key.name !== 'string' || !key.name.startsWith(REG_PREFIX)) throw Error('REGISTRY_KEY_INVALID');
      const id=key.name.slice(REG_PREFIX.length);
      if (index.has(id)) throw Error('REGISTRY_KEY_REPEATED');
      if(!key.metadata||typeof key.metadata!=='object'||Array.isArray(key.metadata)||
        Object.hasOwn(key.metadata,'task_id')&&key.metadata.task_id!==id)throw Error('REGISTRY_METADATA_INVALID');
      let row = {...(key.metadata ?? {}), task_id: id};
      if (!metadataLineageComplete(row)) {
        row = await readTask(env, id);
        if (!row || row.task_id !== id) throw Error('REGISTRY_IDENTITY_UNAVAILABLE');
        taskReadIdentity(row);
      }
      index.set(id, row);
    }
    if (listed.list_complete) return index;
    if (!listed.cursor || seen.has(listed.cursor)) throw Error('REGISTRY_CURSOR_INVALID');
    cursor=listed.cursor;seen.add(cursor);
  }
  throw Error('REGISTRY_INCOMPLETE');
}
// All declared parent/root references must resolve consistently. Unknown fails closed.
function taskReadProject(row,index,seen=new Set()) {
  if (!row || typeof row.task_id !== 'string' || seen.has(row.task_id) || seen.size>=MAX_LINEAGE_WALK) return null;
  const trail=new Set(seen);trail.add(row.task_id);
  let own=null;
  if (Object.hasOwn(row,'project_id')) {
    if (typeof row.project_id!=='string'||!row.project_id) return null;
    own=row.project_id;
  }
  const links=[];
  for (const field of ['root_task_id','parent_task_id']) {
    if (!Object.hasOwn(row,field)||row[field]===null||row[field]==='') continue;
    if (typeof row[field]!=='string') return null;
    if (field==='root_task_id'&&row[field]===row.task_id) continue;
    links.push(row[field]);
  }
  for (const id of new Set(links)) {
    const project=taskReadProject(index.get(id),index,trail);
    if (!project || own && project!==own) return null;
    own=project;
  }
  return own;
}
async function taskReadResult(env,taskId,registry) {
  const artifact=await findArtifact(env,`execution_result-${taskId}`);
  let data=null,run=null;
  if (artifact) {
    data=await downloadArtifactJson(env,artifact.id);
    if (!data || typeof data!=='object'||Array.isArray(data)||data.task_id!==taskId) throw Error('RESULT_TASK_ID_MISMATCH');
    for(const field of ['project_id','root_task_id','parent_task_id']){
      if(Object.hasOwn(data,field)&&data[field]!== (field==='project_id'?TASK_READ_PROJECT:registry[field]??null))throw Error('RESULT_LINEAGE_CONFLICT');
    }
    if(Object.hasOwn(data,'lineage')&&(!data.lineage||data.lineage.kind!=='project'||data.lineage.key!==TASK_READ_PROJECT))throw Error('RESULT_LINEAGE_CONFLICT');
    run=await getArtifactWorkflowRun(env,artifact);
  }
  const safeRun=taskReadRun(run,artifact,env.GITHUB_REPO);
  const status=data?verifiedResultStatus(data.status,safeRun):EXECUTION_STATUS_PENDING;
  // Deliberate task.read allowlist: no raw result, free text, tests, commit,
  // arbitrary artifact metadata or user-supplied nested evidence is forwarded.
  return {task_id:taskId,project_id:TASK_READ_PROJECT,status,normalized_status:status,execution_status:status,
    terminal:TERMINAL_EXECUTION_STATUSES.includes(status),workflow_conclusion:safeRun?.conclusion??null,
    review_verdict:['PASS','FAIL','BLOCKED'].includes(registry.review_verdict??registry.verdict)?registry.review_verdict??registry.verdict:null,
    review_state:['reviewed','unreviewed','pending_review'].includes(registry.review_state)?registry.review_state:registry.reviewed===true?'reviewed':null,
    artifacts:Array.isArray(data?.artifacts)&&data.artifacts.length===0?[]:null,
    artifact_metadata_policy:'UNTRUSTED_DELIVERABLE_METADATA_NOT_PROJECTED',
    evidence:{artifact:{name:`execution_result-${taskId}`,id:artifact?.id??null,file:RESULT_FILENAME},
      validation:{artifact_found:!!artifact,result_loaded:!!data,task_id_matches:!!data&&data.task_id===taskId},workflow_run:safeRun},
    completed_at:safeRun?.completed_at??null,source_updated_at:safeRun?.updated_at??null,
    registry_updated_at:taskReadTime(registry.updated_at),observed_at:new Date().toISOString(),
    read_only:true,registry_sync_performed:false};
}
function taskReadTime(value){
  return typeof value==='string'&&value.length<=40&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)&&Number.isFinite(Date.parse(value))?value:null;
}
function taskReadRun(run,artifact,repo){
  if(!run)return null;
  if(!Number.isSafeInteger(run.id)||run.id<=0||run.id!==artifact?.workflow_run?.id||
    !Number.isSafeInteger(artifact.id)||artifact.id<=0||
    typeof repo!=='string'||!/^[-\w.]+\/[-\w.]+$/.test(repo)||
    run.html_url!==`https://github.com/${repo}/actions/runs/${run.id}`)throw Error('WORKFLOW_IDENTITY_CONFLICT');
  const statuses=['queued','in_progress','completed','requested','waiting','pending'];
  const conclusions=['success','failure','cancelled','timed_out','neutral','skipped','action_required','stale','startup_failure'];
  if(!statuses.includes(run.status)||run.conclusion!==null&&run.conclusion!==undefined&&!conclusions.includes(run.conclusion))throw Error('WORKFLOW_STATUS_INVALID');
  return {id:run.id,status:run.status,conclusion:run.conclusion??null,html_url:run.html_url,
    created_at:taskReadTime(run.created_at),updated_at:taskReadTime(run.updated_at),completed_at:taskReadTime(run.completed_at)};
}
function taskReadIdentity(row){
  if(!row||typeof row!=='object'||Array.isArray(row)||typeof row.task_id!=='string'||!/^cf-[a-f0-9]{12}$/.test(row.task_id))throw Error('REGISTRY_IDENTITY_INVALID');
  const identity={task_id:row.task_id};
  for(const field of ['project_id','root_task_id','parent_task_id']){
    const v=row[field]??null;
    if(v!==null&&(typeof v!=='string'||!v||field!=='project_id'&&!/^cf-[a-f0-9]{12}$/.test(v)))throw Error('REGISTRY_IDENTITY_INVALID');
    identity[field]=v;
  }
  return identity;
}
function taskReadContext(env,index){
  const bodies=new Map();
  async function node(id){
    if(!index.has(id))throw Error('REGISTRY_NODE_MISSING');
    if(!bodies.has(id))bodies.set(id,(async()=>{
      const metadata=taskReadIdentity(index.get(id)),body=await readTask(env,id),actual=taskReadIdentity(body);
      if(actual.task_id!==id||JSON.stringify(metadata)!==JSON.stringify(actual))throw Error('REGISTRY_METADATA_BODY_CONFLICT');
      if(body.dispatch_contract!==undefined){
        const contract=body.dispatch_contract;
        if(!contract||typeof contract!=='object'||Array.isArray(contract))throw Error('REGISTRY_CONTRACT_INVALID');
        for(const key of ['task_id','project_id','root_task_id','parent_task_id'])
          if(Object.hasOwn(contract,key)&&(contract[key]??null)!==actual[key])throw Error('REGISTRY_CONTRACT_CONFLICT');
      }
      return body;
    })());
    return bodies.get(id);
  }
  async function project(id,seen=new Set()){
    if(seen.has(id)||seen.size>=MAX_LINEAGE_WALK)throw Error('REGISTRY_LINEAGE_UNKNOWN');
    const trail=new Set(seen);trail.add(id);
    const row=await node(id);let own=row.project_id??null;
    const links=new Set([row.parent_task_id,row.root_task_id===id?null:row.root_task_id].filter(Boolean));
    for(const parent of links){
      const inherited=await project(parent,trail);
      if(!inherited||own&&own!==inherited)throw Error('REGISTRY_LINEAGE_CONFLICT');
      own=inherited;
    }
    if(!own)throw Error('REGISTRY_PROJECT_UNKNOWN');
    return own;
  }
  return {node,project};
}
async function taskReadGet(env,args) {
  if (!taskReadArgs(args,true)) return taskReadError('TASK_READ_ARGUMENTS_REJECTED');
  try {
    const index=await taskReadIndex(env);
    if (!index.has(args.task_id)) return taskReadError('TASK_PROJECT_NOT_VERIFIED');
    const context=taskReadContext(env,index);
    if (await context.project(args.task_id)!==TASK_READ_PROJECT) return taskReadError('TASK_PROJECT_NOT_VERIFIED');
    const row=await context.node(args.task_id);
    const result=await taskReadResult(env,args.task_id,row);
    return {isError:false,text:JSON.stringify(result),structuredContent:result};
  } catch { return taskReadError('TASK_READ_SOURCE_FAILED'); }
}
async function taskReadList(env,args) {
  if (!taskReadArgs(args)) return taskReadError('TASK_READ_ARGUMENTS_REJECTED');
  try {
    const index=await taskReadIndex(env),pending_review=[],failed=[],blocked=[],unconfirmed=[];
    const now=Date.now(),context=taskReadContext(env,index),verified=[];
    for (const metadata of index.values()) {
      const claimed=taskReadProject(metadata,index);
      if(claimed===null)throw Error('REGISTRY_PROJECT_UNKNOWN');
      if(claimed!==TASK_READ_PROJECT)continue;
      if(await context.project(metadata.task_id)!==TASK_READ_PROJECT)throw Error('REGISTRY_PROJECT_CONFLICT');
      verified.push(await context.node(metadata.task_id));
    }
    // All selected task and ancestor bodies verified before any GitHub fetch.
    for (const row of verified) {
      const r=await taskReadResult(env,row.task_id,row);
      const available=r.terminal&&r.evidence?.validation?.result_loaded===true;
      const item={task_id:row.task_id,project_id:TASK_READ_PROJECT,
        execution_status:r.execution_status,status:r.status,terminal:r.terminal,
        workflow_conclusion:r.workflow_conclusion,review_verdict:r.review_verdict,review_state:r.review_state,
        result_available:available,reviewed:row.reviewed===true,
        completed_at:r.completed_at,source_updated_at:r.source_updated_at,registry_updated_at:r.registry_updated_at};
      if (available&&row.reviewed!==true) {
        pending_review.push(item);if(r.execution_status===EXECUTION_STATUS_FAIL)failed.push(item);
      } else if (!available) {
        const liveness=classifyTaskDispatchLiveness(row,{now,hasArtifact:!!r.evidence?.validation?.artifact_found,
          runStatus:r.evidence?.workflow_run?.status,runConclusion:r.workflow_conclusion});
        item.dispatch_state=liveness.dispatch_state;
        item.recommended_action=liveness.recommended_action;
        // This is a report only. No retry/lease/dispatch function is invoked.
        if(liveness.recommended_action===TASK_DISPATCH_ACTION_RETRY)unconfirmed.push(item);
        else { const created=Date.parse(row.created_at);if(Number.isFinite(created)&&now-created>BLOCKED_AFTER_MS)blocked.push(item); }
      }
    }
    const report={pending:pending_review,pending_review,failed,blocked,unconfirmed,
      counts:{pending:pending_review.length,pending_review:pending_review.length,failed:failed.length,
        blocked:blocked.length,unconfirmed:unconfirmed.length,total:verified.length},
      scope:{project_id:TASK_READ_PROJECT},read_only:true,registry_sync_performed:false,
      coverage:'PENDING_REVIEW_FAILED_BLOCKED_UNCONFIRMED_NOT_ALL_RUNNING_TASKS',observed_at:new Date().toISOString()};
    return {isError:false,text:JSON.stringify(report),structuredContent:report};
  } catch { return taskReadError('TASK_READ_SOURCE_FAILED'); }
}

async function handleMcp(request, env, cors, auth) {
  let message;
  try {
    message = await request.json();
  } catch {
    return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400, cors);
  }
  const { id = null, method, params = {} } = message || {};
  if (method && method.startsWith("notifications/")) return new Response(null, { status: 202, headers: cors });
  const ok = (result) => json({ jsonrpc: "2.0", id, result }, 200, cors);
  const fail = (code, message2) => json({ jsonrpc: "2.0", id, error: { code, message: message2 } }, 200, cors);
  switch (method) {
    case "initialize":
      return ok({
        protocolVersion: params.protocolVersion || PROTOCOL_VERSION,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: "personal-ai-execution", version: "0.1" }
      });
    case "ping":
      return ok({});
    case "server/discover":
      return ok({
        resultType: "complete",
        supportedVersions: [EVENTS_PROTOCOL_VERSION],
        capabilities: { tools: {}, events: {} }
      });
    case "events/list":
      return ok(listEvents());
    case "events/subscribe": {
      if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
      try {
        return ok(await handleEventsSubscribe(env, auth, params));
      } catch (err) {
        return jsonRpcError(cors, id, err);
      }
    }
    case "events/unsubscribe": {
      if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
      try {
        return ok(await handleEventsUnsubscribe(env, auth, params));
      } catch (err) {
        return jsonRpcError(cors, id, err);
      }
    }
    case "tools/list":
      return ok({ tools: isTaskRead(auth) ? taskReadTools() : TOOLS });
    case "tools/call": {
      const name = params.name;
      const args = params.arguments || {};
      let outcome;
      if (isTaskRead(auth)) {
        if (name === 'get_task_result') outcome = await taskReadGet(env, args);
        else if (name === 'list_pending_results') outcome = await taskReadList(env, args);
        else return fail(-32002, 'task.read allows only two fixed-project read tools');
      } else if (name === "submit_task") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolSubmitTask(env, args);
      } else if (name === "get_task_execution_status") {
        // Keep existing task authorization without legacy scope defaults.
        if (!hasTaskObservationScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolGetTaskExecutionStatus(env, args);
      } else if (name === "get_task_result") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolGetTaskResult(env, args);
      } else if (name === "list_pending_results") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolListPendingResults(env, args);
      } else if (name === "mark_reviewed") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolMarkReviewed(env, args);
      } else if (name === "plan_task_redispatch") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolPlanDispatchRetry(env, args);
      } else if (name === "retry_task_dispatch") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await retryDispatchTask(env, args);
      } else if (name === "search_assets") {
        if (!hasReadScope(auth)) return fail(-32001, "asset.read scope required");
        outcome = await toolSearchAssets(env, args);
      } else if (name === "get_asset") {
        if (!hasReadScope(auth)) return fail(-32001, "asset.read scope required");
        outcome = await toolGetAsset(env, args);
      } else if (name === "write_knowledge_candidate") {
        // Candidate reads keep read-scope isolation; every write/mutation
        // sub-operation (create / submit / review / promote) requires write scope.
        if (knowledgeCandidateReadOperation(args)) {
          if (!hasReadScope(auth)) return fail(-32001, "asset.read scope required");
        } else if (!hasWriteScope(auth)) {
          return fail(-32002, "mcp scope required");
        }
        outcome = await toolWriteKnowledgeCandidate(env, args);
      } else if (name === "write_skill_candidate") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await writeSkillCandidate(env, args);
      } else if (name === "write_decision_record") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolWriteDecisionRecord(env, args);
      } else return fail(-32602, `unknown tool: ${name}`);
      const toolResult = { content: [{ type: "text", text: outcome.text }], isError: outcome.isError };
      if (outcome.structuredContent !== void 0) toolResult.structuredContent = outcome.structuredContent;
      return ok(toolResult);
    }
    default:
      return fail(-32601, `method not found: ${method}`);
  }
}
var index_default = {
  async fetch(request, env) {
    const cors = corsHeaders();
    const url = new URL(request.url);
    const origin = originOf(request);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname === "/.well-known/oauth-protected-resource" || url.pathname === "/.well-known/oauth-protected-resource/mcp") {
      return json(protectedResourceMetadata(origin), 200, cors);
    }
    if (url.pathname === "/.well-known/oauth-authorization-server") {
      return json(authorizationServerMetadata(origin), 200, cors);
    }
    if (url.pathname === "/register" && request.method === "POST") return registerClient(request, env, origin);
    if (url.pathname === "/authorize" && request.method === "GET") return authorizeGet(request, env);
    if (url.pathname === "/authorize" && request.method === "POST") return authorizePost(request, env);
    if (url.pathname === "/token" && request.method === "POST") return tokenEndpoint(request, env);
    if (url.pathname === "/healthz") {
      return json({ status: "ok", name: "personal-ai-execution-mcp", version: "0.2" }, 200, cors);
    }
    if (url.pathname === "/mcp") {
      if (request.method !== "POST") {
        return new Response("Method Not Allowed", { status: 405, headers: { ...cors, Allow: "POST" } });
      }
      const auth = await mcpAuthorized(request, env);
      if (!auth) return unauthorized(origin);
      return handleMcp(request, env, cors, auth);
    }
    return json({ error: "NOT_FOUND" }, 404, cors);
  }
};
export {
  index_default as default
};
//# sourceMappingURL=index.js.map
