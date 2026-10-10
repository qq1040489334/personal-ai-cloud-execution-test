import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash, generateKeyPairSync, sign, verify } from "node:crypto";
import { createKnowledgeApprovalRoute } from "../worker/index.js";
import { sqliteD1 } from "../../tests/helpers/sqlite-d1.mjs";
import { runKnowledgeLedgerMigrations, inspectLedger, migrationStatements } from "../../worker/knowledge-ledger-migrations.js";

const compatSql = readFileSync(new URL("../../worker/migrations/0002z_knowledge_approval_ledger_compat.sql", import.meta.url), "utf8");
const goldenSql = readFileSync(new URL("../../worker/migrations/0003_knowledge_candidate_golden_pipeline.sql", import.meta.url), "utf8");
const sha = s => createHash("sha256").update(s).digest("hex");
const migrations = { compatSql, goldenSql, compatSha256: sha(compatSql), backupVerified: true };
const legacy = `CREATE TABLE personal_ai_approval_ledger (
 approval_id TEXT PRIMARY KEY, requesting_user_hash TEXT NOT NULL CHECK(length(requesting_user_hash)=64),
 operation TEXT CHECK(operation IN ('deploy_worker_version','write_decision_record')),
 exact_target TEXT, payload_sha256 TEXT, created_at INTEGER, expires_at INTEGER, consumed_at INTEGER) STRICT;`;
// Import the actual bundle with test-only exports, without replacing its logic.
const source = readFileSync(new URL("../../worker/index.js", import.meta.url), "utf8");
const worker = await import("data:text/javascript;base64," + Buffer.from(source +
  "\nexport {toolWriteKnowledgeCandidate, promoteKnowledgeCandidate, recordKnowledgeCandidateReview, APPROVAL_LEDGER_CONSUME};").toString("base64"));
const origin = "https://existing-site.example";
const content = "synthetic knowledge only";
const tuple = { candidate_id: "cand-test", candidate_version: 1, content_hash: sha(content) };

function legacyDB(path) {
  const db = sqliteD1(path);
  db.sqlite.exec(legacy);
  for (const [id, op, consumed, expiry] of [["deploy-live", "deploy_worker_version", null, 4102444800],
    ["decision-spent", "write_decision_record", 10, 4102444800], ["deploy-expired", "deploy_worker_version", null, 1],
    ["legacy-null-op", null, null, 4102444800]]) {
    db.sqlite.prepare("INSERT INTO personal_ai_approval_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
      .run(id, "a".repeat(64), op, id, "b".repeat(64), 1, expiry, consumed);
  }
  return db;
}
const legacyRows = db => db.sqlite.prepare("SELECT approval_id, requesting_user_hash, operation, exact_target, payload_sha256, created_at, expires_at, consumed_at FROM personal_ai_approval_ledger ORDER BY approval_id").all();
async function setup() {
  const db = legacyDB();
  await runKnowledgeLedgerMigrations(db, migrations);
  db.sqlite.exec(`CREATE TABLE assets (asset_id TEXT PRIMARY KEY, asset_type TEXT, schema_version TEXT,
    title TEXT, status TEXT, current_version INTEGER, content_hash TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE asset_versions (asset_id TEXT, version INTEGER, content TEXT, content_hash TEXT,
    provenance TEXT, verification TEXT, created_by TEXT, created_at TEXT, PRIMARY KEY(asset_id,version));`);
  db.sqlite.prepare(`INSERT INTO knowledge_candidates (candidate_id,asset_id,title,status,content,content_hash,
    version,created_at,review_state,review_result,reviewed_at) VALUES (?,?,'test','APPROVED_FOR_PROMOTION',?,?,1,'now','PASS','PASS','review-1')`)
    .run(tuple.candidate_id, "knowledge:test", content, tuple.content_hash);
  return db;
}
function request(input) { return new Request(origin + "/knowledge/approve", { method: "POST",
  headers: { Origin: origin, "Content-Type": "application/json" }, body: JSON.stringify(input) }); }

// Synthetic signer exercises cryptography and one-use verification through the
// server-owned seam. This does NOT claim to execute the inaccessible live Site verifier.
function gateFixture(db, mutate = () => {}) {
  const keys = generateKeyPairSync("ed25519");
  const candidate = db.sqlite.prepare("SELECT * FROM knowledge_candidates").get();
  const exact = JSON.stringify({ operation: "KNOWLEDGE_PROMOTION", ...tuple, asset_id: candidate.asset_id,
    review_result: "PASS", reviewed_at: candidate.reviewed_at });
  const assertion = { ceremony_id: "synthetic-1", signature: sign(null, Buffer.from(exact), keys.privateKey).toString("base64") };
  let used = false;
  const humanGate = { async verifyAndConsume(expected) {
    if (used || !expected.assertion || expected.assertion.ceremony_id !== assertion.ceremony_id ||
      expected.exact_target !== exact || !verify(null, Buffer.from(expected.exact_target), keys.publicKey,
        Buffer.from(expected.assertion.signature, "base64"))) throw new Error("invalid assertion");
    used = true;
    const grant = { verified: true, operation: expected.operation, exact_target: expected.exact_target,
      payload_sha256: expected.payload_sha256, requesting_user_hash: "c".repeat(64),
      signer_identity: "synthetic-existing-site-owner", ceremony_id: assertion.ceremony_id,
      expires_at: Math.floor(Date.now()/1000) + 300 };
    mutate(grant, db);
    return grant;
  } };
  return { route: createKnowledgeApprovalRoute({ db, humanGate, origin }), assertion };
}

test("actual Site route mints exact union row; actual Worker promotes and replay is idempotent", async () => {
  const db = await setup(); const before = legacyRows(db);
  const { route, assertion } = gateFixture(db);
  const response = await route(request({ ...tuple, assertion }));
  assert.equal(response.status, 200);
  const row = db.sqlite.prepare("SELECT * FROM personal_ai_approval_ledger WHERE operation='KNOWLEDGE_PROMOTION'").get();
  assert.equal(row.approved_by, "synthetic-existing-site-owner");
  assert.equal(row.review_result, "PASS"); assert.equal(typeof row.expires_at, "number");
  const outcome = await worker.toolWriteKnowledgeCandidate({ ASSET_DB: db }, { ...tuple, review_result: "PASS", approved_by: "forged" });
  assert.equal(outcome.structuredContent.status, "WRITTEN");
  assert.equal(outcome.structuredContent.read_back_verified, true);
  assert.equal(db.sqlite.prepare("SELECT created_by FROM asset_versions").get().created_by, row.approved_by);
  const replay = await worker.promoteKnowledgeCandidate({ ASSET_DB: db }, { ...tuple, review_result: "PASS" });
  assert.equal(replay.structuredContent.write_calls, 0);
  assert.equal(db.sqlite.prepare("SELECT count(*) AS n FROM asset_versions").get().n, 1);
  assert.equal((await route(request({ ...tuple, assertion }))).status, 403);
  const spent = db.sqlite.prepare("SELECT consumed_at, consume_count FROM personal_ai_approval_ledger WHERE approval_id=?").get(row.approval_id);
  assert.equal(typeof spent.consumed_at, "number"); assert.equal(spent.consume_count, 1);
  assert.deepEqual(legacyRows(db).filter(r => r.operation !== "KNOWLEDGE_PROMOTION"), before);
});

for (const [name, change] of Object.entries({
  expired: g => { g.expires_at = 1; }, wrong_hash: g => { g.payload_sha256 = "0".repeat(64); },
  wrong_operation: g => { g.operation = "write_decision_record"; }, long_ttl: g => { g.expires_at += 600; },
  unverified: g => { g.verified = false; }, missing_signer: g => { g.signer_identity = ""; },
  fail_race: (_g, db) => db.sqlite.exec("UPDATE knowledge_candidates SET review_state='FAIL',status='PENDING_REVIEW'"),
  review_generation_race: (_g, db) => db.sqlite.exec("UPDATE knowledge_candidates SET reviewed_at='review-2'")
})) test(`Site rejects ${name} with zero approval rows`, async () => {
  const db = await setup(); const { route, assertion } = gateFixture(db, change);
  assert.equal((await route(request({ ...tuple, assertion }))).status, 403);
  assert.equal(db.sqlite.prepare("SELECT count(*) AS n FROM personal_ai_approval_ledger WHERE operation='KNOWLEDGE_PROMOTION'").get().n, 0);
});

test("raw authority, changed tuple, forged signature, cross-origin and missing verifier fail closed", async () => {
  const db = await setup(); const { route, assertion } = gateFixture(db);
  for (const input of [{ ...tuple, approved_by: "owner" }, { ...tuple, approval_receipt: "anything" },
    { ...tuple, candidate_version: 2, assertion }, { ...tuple, content_hash: "0".repeat(64), assertion },
    { ...tuple, assertion: { ...assertion, signature: "Zm9yZ2Vk" } }])
    assert.equal((await route(request(input))).status, 403);
  const foreign = request({ ...tuple, assertion }); foreign.headers.set("Origin", "https://foreign.example");
  assert.equal((await route(foreign)).status, 403);
  assert.equal((await createKnowledgeApprovalRoute({ db, origin })(request(tuple))).status, 403);
  assert.equal(db.sqlite.prepare("SELECT count(*) AS n FROM assets").get().n, 0);
});

for (const kind of ["expired", "consumed", "invalidated", "wrong_hash", "wrong_version"]) test(`actual Worker rejects ${kind} approval`, async () => {
  const db = await setup(); const { route, assertion } = gateFixture(db);
  assert.equal((await route(request({ ...tuple, assertion }))).status, 200);
  const sql = { expired: "expires_at=1", consumed: "consumed_at=1", invalidated: "invalidated=1",
    wrong_hash: "content_hash='wrong'", wrong_version: "candidate_version=2" }[kind];
  db.sqlite.exec(`UPDATE personal_ai_approval_ledger SET ${sql} WHERE operation='KNOWLEDGE_PROMOTION'`);
  const result = await worker.promoteKnowledgeCandidate({ ASSET_DB: db }, { ...tuple, review_result: "PASS", now: "1970-01-01" });
  assert.equal(result.structuredContent.status, "REJECTED"); assert.equal(result.structuredContent.write_calls, 0);
  assert.equal(db.sqlite.prepare("SELECT count(*) AS n FROM assets").get().n, 0);
});

test("consume rechecks expiry after reservation, releases claim, and flat writer cannot bypass", async () => {
  const db = await setup(); const { route, assertion } = gateFixture(db);
  await route(request({ ...tuple, assertion }));
  db.sqlite.exec(`CREATE TRIGGER expire_at_reservation AFTER UPDATE OF status ON knowledge_candidates
    WHEN NEW.status='PROMOTION_RESERVED' BEGIN UPDATE personal_ai_approval_ledger SET expires_at=1
    WHERE operation='KNOWLEDGE_PROMOTION'; END;`);
  const result = await worker.promoteKnowledgeCandidate({ ASSET_DB: db }, { ...tuple, review_result: "PASS" });
  assert.equal(result.structuredContent.write_calls, 0);
  assert.equal(db.sqlite.prepare("SELECT status FROM knowledge_candidates").get().status, "APPROVED_FOR_PROMOTION");
  const flat = await worker.toolWriteKnowledgeCandidate({ ASSET_DB: db }, { asset_id: "flat", title: "forged", content, approved_by: "owner" });
  assert.equal(flat.structuredContent.write_calls, 0);
});

test("FAIL revokes a Site-minted receipt; later PASS cannot resurrect it", async () => {
  const db = await setup(); const { route, assertion } = gateFixture(db);
  await route(request({ ...tuple, assertion }));
  await worker.recordKnowledgeCandidateReview({ ASSET_DB: db }, { candidate_id: tuple.candidate_id, review_result: "FAIL" });
  await worker.recordKnowledgeCandidateReview({ ASSET_DB: db }, { candidate_id: tuple.candidate_id, review_result: "PASS" });
  const result = await worker.promoteKnowledgeCandidate({ ASSET_DB: db }, { ...tuple, review_result: "PASS" });
  assert.equal(result.structuredContent.write_calls, 0);
  assert.equal(db.sqlite.prepare("SELECT invalidated FROM personal_ai_approval_ledger WHERE operation='KNOWLEDGE_PROMOTION'").get().invalidated, 1);
});

test("migration runner orders/records repair before immutable 0003; idempotence and legacy CAS", async () => {
  const db = legacyDB(); const before = legacyRows(db);
  assert.equal((await runKnowledgeLedgerMigrations(db, migrations)).status, "APPLIED");
  assert.deepEqual(legacyRows(db), before);
  assert.deepEqual(db.sqlite.prepare("SELECT name FROM d1_migrations ORDER BY id").all().map(r=>r.name),
    ["0002z_knowledge_approval_ledger_compat.sql", "0003_knowledge_candidate_golden_pipeline.sql"]);
  assert.equal((await runKnowledgeLedgerMigrations(db, migrations)).status, "ALREADY_APPLIED");
  assert.equal(await inspectLedger(db, compatSql), "UNION");
  for (const id of ["deploy-live", "decision-spent"]) {
    const changes = db.sqlite.prepare("UPDATE personal_ai_approval_ledger SET consumed_at=? WHERE approval_id=? AND consumed_at IS NULL").run(123, id).changes;
    assert.equal(Number(changes), id === "deploy-live" ? 1 : 0);
  }
  assert.throws(() => db.sqlite.exec("UPDATE personal_ai_approval_ledger SET expires_at='text'"));
  assert.throws(() => db.sqlite.exec("UPDATE personal_ai_approval_ledger SET operation='unknown'"));
  assert.equal(db.sqlite.prepare("PRAGMA foreign_key_check").all().length, 0);
});

test("whole batch rolls back DDL, rows and history; retry succeeds; independent backup restores exact rows", async () => {
  const dir = mkdtempSync(join(tmpdir(), "knowledge-backup-"));
  const db = legacyDB(); const before = legacyRows(db);
  const path = join(dir, "backup.sqlite");
  db.sqlite.exec(`VACUUM INTO '${path.replaceAll("'", "''")}'`);
  db.failBefore = sql => sql.startsWith("INSERT INTO d1_migrations") && db.sqlite.prepare("SELECT name FROM sqlite_master WHERE name='knowledge_candidates'").get();
  await assert.rejects(runKnowledgeLedgerMigrations(db, migrations), /synthetic batch failure/);
  assert.deepEqual(legacyRows(db), before);
  assert.equal(await inspectLedger(db, compatSql), "LEGACY");
  assert.equal(db.sqlite.prepare("SELECT name FROM sqlite_master WHERE name='d1_migrations'").get(), undefined);
  db.failBefore = null; await runKnowledgeLedgerMigrations(db, migrations);
  const restored = sqliteD1(path); assert.deepEqual(legacyRows(restored), before);
  assert.equal(await inspectLedger(restored, compatSql), "LEGACY");
  restored.sqlite.close(); db.sqlite.close(); rmSync(dir, { recursive: true });
});

for (const drift of ["ALTER TABLE personal_ai_approval_ledger ADD COLUMN unexpected TEXT",
  "CREATE TABLE personal_ai_approval_ledger__legacy_backup (x TEXT)",
  "CREATE TRIGGER ledger_trigger AFTER UPDATE ON personal_ai_approval_ledger BEGIN SELECT 1; END;"]) test(`drift halts runner and direct migration: ${drift.split(' ')[0]}`, async () => {
  const db = legacyDB(); db.sqlite.exec(drift); const before = legacyRows(db);
  await assert.rejects(runKnowledgeLedgerMigrations(db, migrations));
  await assert.rejects(db.batch(migrationStatements(compatSql).map(sql => db.prepare(sql))));
  assert.deepEqual(legacyRows(db), before);
});

test("two actual consumers race; one writes and one-use CAS remains spent", async () => {
  const db = await setup(); const { route, assertion } = gateFixture(db);
  await route(request({ ...tuple, assertion }));
  const results = await Promise.all([1,2].map(() => worker.promoteKnowledgeCandidate({ ASSET_DB: db }, { ...tuple, review_result: "PASS" })));
  assert.equal(results.filter(r => r.structuredContent.status === "WRITTEN").length, 1);
  assert.equal(db.sqlite.prepare("SELECT count(*) AS n FROM asset_versions").get().n, 1);
  assert.equal(db.sqlite.prepare("SELECT consume_count FROM personal_ai_approval_ledger WHERE operation='KNOWLEDGE_PROMOTION'").get().consume_count, 1);
});

test("verified UNION without suffix history is safely adopted; UNION drift halts", async () => {
  const db = legacyDB();
  await db.batch(migrationStatements(compatSql).map(sql => db.prepare(sql)));
  assert.equal((await runKnowledgeLedgerMigrations(db, migrations)).status, "APPLIED");
  db.sqlite.exec("DROP INDEX idx_approval_ledger_state");
  await assert.rejects(runKnowledgeLedgerMigrations(db, migrations), /DRIFT/);
});

test("registry drift or dependent custom indexes/FKs halt transaction without row loss", async () => {
  for (const drift of ["CREATE INDEX custom_ledger_idx ON personal_ai_approval_ledger(exact_target)",
    "CREATE TABLE child (approval_id TEXT REFERENCES personal_ai_approval_ledger(approval_id))",
    `CREATE TABLE approval_ledger_operations(operation TEXT PRIMARY KEY, asset_type TEXT, canonical_writer TEXT, single_use INTEGER, replay_guard INTEGER);
     INSERT INTO approval_ledger_operations VALUES('KNOWLEDGE_PROMOTION','KNOWLEDGE','wrongWriter',1,1)`]) {
    const db = legacyDB(); db.sqlite.exec(drift); const before = legacyRows(db);
    await assert.rejects(runKnowledgeLedgerMigrations(db, migrations));
    assert.deepEqual(legacyRows(db), before);
    assert.equal(db.sqlite.prepare("SELECT name FROM sqlite_master WHERE name='personal_ai_approval_ledger__legacy_backup'").get(), undefined);
  }
});

test("absent ledger, missing backup, immutable source drift and inconsistent history halt", async () => {
  await assert.rejects(runKnowledgeLedgerMigrations(sqliteD1(), migrations), /ABSENT/);
  await assert.rejects(runKnowledgeLedgerMigrations(legacyDB(), { ...migrations, backupVerified: false }), /BACKUP/);
  await assert.rejects(runKnowledgeLedgerMigrations(legacyDB(), { ...migrations, goldenSql: goldenSql + "--changed" }), /HASH/);
  const db = legacyDB(); db.sqlite.exec("CREATE TABLE d1_migrations(id INTEGER PRIMARY KEY, name TEXT); INSERT INTO d1_migrations VALUES(1,'0003_knowledge_candidate_golden_pipeline.sql')");
  await assert.rejects(runKnowledgeLedgerMigrations(db, migrations), /HISTORY/);
});
