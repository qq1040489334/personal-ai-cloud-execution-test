// Maintenance runner over an existing D1 binding. Never mounted as an HTTP/MCP
// route; calling it requires the separately authorized maintenance context.
// Uses the same d1_migrations history as Wrangler, never deletes failed history.
export const COMPAT_NAME = "0002z_knowledge_approval_ledger_compat.sql";
export const GOLDEN_NAME = "0003_knowledge_candidate_golden_pipeline.sql";
const GOLDEN_HASH = "9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a";
const normalize = sql => {
  const literals = [];
  const structure = sql.replace(/'(?:[^']|'')*'/g, s => `@${literals.push(s)-1}@`)
    .toLowerCase().replace(/[\s";]/g, "");
  return structure.replace(/@(\d+)@/g, (_m, i) => literals[Number(i)]);
};
const hash = async s => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",
  new TextEncoder().encode(s))), b => b.toString(16).padStart(2, "0")).join("");
const LEGACY = normalize(`CREATE TABLE personal_ai_approval_ledger (
  approval_id TEXT PRIMARY KEY, requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation TEXT CHECK (operation IN ('deploy_worker_version','write_decision_record')),
  exact_target TEXT, payload_sha256 TEXT, created_at INTEGER, expires_at INTEGER, consumed_at INTEGER) STRICT`);

// Only these reviewed migration files contain plain statements without triggers
// or semicolons in string values. Reject future unsupported syntax, don't guess.
export function migrationStatements(sql) {
  const clean = sql.replace(/--[^\n]*/g, "");
  if (/\b(BEGIN|COMMIT|ROLLBACK|TRIGGER)\b/i.test(clean.replace(/'(?:[^']|'')*'/g, ""))) throw new Error("HALT_UNSUPPORTED_SQL");
  return clean.split(";").map(s => s.trim()).filter(Boolean);
}

export async function inspectLedger(db, compatSql) {
  const row = await db.prepare("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'personal_ai_approval_ledger'").first();
  if (!row) return "ABSENT";
  const unionDDL = compatSql.match(/CREATE TABLE personal_ai_approval_ledger__v2\s*\([\s\S]*?\) STRICT;/)?.[0];
  if (!unionDDL) throw new Error("HALT_MIGRATION_SOURCE_INVALID");
  const shape = normalize(row.sql) === LEGACY ? "LEGACY" :
    normalize(row.sql) === normalize(unionDDL.replace("personal_ai_approval_ledger__v2", "personal_ai_approval_ledger")) ? "UNION" : "DRIFT";
  const triggers = await db.prepare("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'personal_ai_approval_ledger'").all();
  if (triggers.results.length) return "DRIFT";
  if (shape === "UNION") {
    const fk = await db.prepare("PRAGMA foreign_key_list(personal_ai_approval_ledger)").all();
    if (fk.results.length !== 1 || fk.results[0].table !== "approval_ledger_operations" ||
        fk.results[0].from !== "operation" || fk.results[0].to !== "operation") return "DRIFT";
    for (const [name, columns] of [["idx_approval_ledger_binding", "operation,candidate_id,candidate_version,content_hash"],
                                 ["idx_approval_ledger_state", "operation,consumed,invalidated"]]) {
      const indexes = await db.prepare(`PRAGMA index_info(${name})`).all();
      if (indexes.results.map(r => r.name).join(",") !== columns) return "DRIFT";
    }
    const operations = await db.prepare("SELECT * FROM approval_ledger_operations ORDER BY operation").all();
    const expected = { deploy_worker_version: ["DEPLOY", "deployWorkerVersion"], write_decision_record: ["DECISION", "writeDecisionRecord"],
      decision_write: ["DECISION", "writeDecisionRecord"], knowledge_write: ["KNOWLEDGE", "writeKnowledgeCandidate"],
      KNOWLEDGE_PROMOTION: ["KNOWLEDGE", "writeKnowledgeCandidate"] };
    if (operations.results.length !== 5 || operations.results.some(r => !expected[r.operation] ||
      r.asset_type !== expected[r.operation][0] || r.canonical_writer !== expected[r.operation][1] ||
      r.single_use !== 1 || r.replay_guard !== 1)) return "DRIFT";
  }
  return shape;
}

export async function runKnowledgeLedgerMigrations(db, { compatSql, goldenSql, compatSha256, backupVerified } = {}) {
  if (!db?.batch || backupVerified !== true) throw new Error("HALT_VERIFIED_BACKUP_REQUIRED");
  if (await hash(goldenSql) !== GOLDEN_HASH || await hash(compatSql) !== compatSha256)
    throw new Error("HALT_MIGRATION_HASH_MISMATCH");
  const shape = await inspectLedger(db, compatSql);
  if (!["LEGACY", "UNION"].includes(shape)) throw new Error(`HALT_LEDGER_${shape}`);
  const hasHistory = await db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'd1_migrations'").first();
  const history = hasHistory ? (await db.prepare("SELECT name FROM d1_migrations ORDER BY id").all()).results.map(r => r.name) : [];
  if (new Set(history).size !== history.length || (history.includes(COMPAT_NAME) && shape !== "UNION") ||
      (history.includes(GOLDEN_NAME) && !history.includes(COMPAT_NAME))) throw new Error("HALT_HISTORY_SCHEMA_MISMATCH");
  if (history.includes(GOLDEN_NAME)) {
    const candidate = await db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'knowledge_candidates'").first();
    if (!candidate) throw new Error("HALT_HISTORY_SCHEMA_MISMATCH");
    return { status: "ALREADY_APPLIED", shape };
  }
  const statements = [db.prepare("CREATE TABLE IF NOT EXISTS d1_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)")];
  // Recheck the exact pre-read schema INSIDE the transaction to close drift races.
  const current = await db.prepare("SELECT sql FROM sqlite_master WHERE name = 'personal_ai_approval_ledger'").first();
  statements.push(db.prepare("SELECT CASE WHEN (SELECT sql FROM sqlite_master WHERE name = 'personal_ai_approval_ledger') = ? THEN 1 ELSE json('HALT_CONCURRENT_SCHEMA_DRIFT') END").bind(current.sql));
  if (!history.includes(COMPAT_NAME)) {
    if (shape === "LEGACY") statements.push(...migrationStatements(compatSql).map(sql => db.prepare(sql)));
    // UNION adoption is allowed only after exact schema/FK/index/registry proof;
    // it records the completed repair under its real name, never rewrites history.
    statements.push(db.prepare("INSERT INTO d1_migrations (name) VALUES (?)").bind(COMPAT_NAME));
  }
  statements.push(...migrationStatements(goldenSql).map(sql => db.prepare(sql)));
  statements.push(db.prepare("INSERT INTO d1_migrations (name) VALUES (?)").bind(GOLDEN_NAME));
  // D1 batch rolls back DDL, data AND history if any statement fails.
  await db.batch(statements);
  if (await inspectLedger(db, compatSql) !== "UNION") throw new Error("HALT_POST_MIGRATION_DRIFT");
  return { status: "APPLIED", shape: "UNION", order: [COMPAT_NAME, GOLDEN_NAME] };
}
