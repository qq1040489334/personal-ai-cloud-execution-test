// Maintenance-only runner over the existing D1 binding and Wrangler history.
// No HTTP route, new approval authority or production invocation is added.
export const COMPAT_NAME = "0002z_knowledge_approval_ledger_compat.sql";
export const GOLDEN_NAME = "0003_knowledge_candidate_golden_pipeline.sql";
const GOLDEN_HASH = "9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a";
const sqlLiterals = sql => [...new Set(sql.match(/'(?:[^']|'')*'/g) ?? [])];
const normalize = (sql, definition = sql) => {
  for (const [i, value] of sqlLiterals(definition).entries()) sql = sql.replaceAll(value, `@${i}@`);
  return sql.replace(/\bIF NOT EXISTS\s*/g, "").replace(/[\s";]/g, "");
};
const hash = async s => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",
  new TextEncoder().encode(s))), b => b.toString(16).padStart(2, "0")).join("");
const LEGACY = `CREATE TABLE personal_ai_approval_ledger (
  approval_id TEXT PRIMARY KEY, requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation TEXT CHECK (operation IN ('deploy_worker_version','write_decision_record')),
  exact_target TEXT, payload_sha256 TEXT, created_at INTEGER, expires_at INTEGER, consumed_at INTEGER) STRICT`;
const OPERATIONS = [
  ['KNOWLEDGE_PROMOTION','KNOWLEDGE','writeKnowledgeCandidate',1,1],
  ['decision_write','DECISION','writeDecisionRecord',1,1],
  ['deploy_worker_version','DEPLOY','deployWorkerVersion',1,1],
  ['knowledge_write','KNOWLEDGE','writeKnowledgeCandidate',1,1],
  ['write_decision_record','DECISION','writeDecisionRecord',1,1]
];
const literal = s => "'" + String(s).replaceAll("'", "''") + "'";
// Keep string literal case significant (e.g. NOT_REVIEWED defaults). Only the
// reviewed whitespace/quotes/IF NOT EXISTS spelling is normalized.
const sqlNormal = (expr, definition) => {
  for (const [i, value] of sqlLiterals(definition).entries()) expr = `replace(${expr}, ${literal(value)}, '@${i}@')`;
  return `replace(replace(replace(replace(replace(replace(replace(${expr}, ' ', ''), char(10), ''), char(13), ''), char(9), ''), '"', ''), ';', ''), 'IFNOTEXISTS', '')`;
};
const schemaQuery = "SELECT json_group_array(json_array(type,name,tbl_name,sql)) AS value FROM (SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name)";
const registryQuery = "SELECT json_group_array(json_array(operation,asset_type,canonical_writer,single_use,replay_guard)) AS value FROM (SELECT * FROM approval_ledger_operations ORDER BY operation)";
const historyQuery = "SELECT json_group_array(json_array(id,name,applied_at)) AS value FROM (SELECT * FROM d1_migrations ORDER BY id)";
const assertion = predicate => `SELECT CASE WHEN (${predicate}) THEN 1 ELSE json('HALT_TRANSACTION_INVARIANT') END`;
const ddl = (sql, name) => migrationStatements(sql).find(s => s.startsWith('CREATE TABLE') && new RegExp(`\\b${name}\\s*\\(`).test(s));

export function migrationStatements(sql) {
  const clean = sql.replace(/--[^\n]*/g, "");
  if (/\b(BEGIN|COMMIT|ROLLBACK|TRIGGER)\b/i.test(clean.replace(/'(?:[^']|'')*'/g, ""))) throw new Error("HALT_UNSUPPORTED_SQL");
  return clean.split(";").map(s => s.trim()).filter(Boolean);
}
function tableInvariant(table, definition, indexes = []) {
  if (!definition) throw new Error('HALT_MIGRATION_SOURCE_INVALID');
  const name = literal(table);
  const conditions = [
    `(SELECT ${sqlNormal('sql',definition)} FROM sqlite_master WHERE type='table' AND name=${name}) = ${literal(normalize(definition))}`,
    `NOT EXISTS (SELECT 1 FROM sqlite_master WHERE type='trigger' AND tbl_name=${name})`,
    // The reviewed TEXT PRIMARY KEY has one implicit pk index. Reject all
    // additional enforcing indexes, including UNIQUE constraints/autoindexes.
    `(SELECT count(*) FROM pragma_index_list(${name})) = ${indexes.length + 1}`,
    `(SELECT count(*) FROM pragma_index_list(${name}) WHERE origin='pk' AND "unique"=1 AND partial=0) = 1`
  ];
  for (const [index, columns, definition] of indexes) {
    const ix = literal(index);
    conditions.push(`EXISTS (SELECT 1 FROM sqlite_master WHERE type='index' AND name=${ix} AND tbl_name=${name} AND ${sqlNormal('sql',definition)}=${literal(normalize(definition))})`,
      `EXISTS (SELECT 1 FROM pragma_index_list(${name}) WHERE name=${ix} AND "unique"=0 AND origin='c' AND partial=0)`,
      `(SELECT json_group_array(json_array(name,desc,coll,"key")) FROM (SELECT * FROM pragma_index_xinfo(${ix}) WHERE "key"=1 ORDER BY seqno))=${literal(JSON.stringify(columns.map(c => [c,0,'BINARY',1])))}`);
  }
  return conditions.join(' AND ');
}
function reviewedInvariants(compatSql, goldenSql) {
  const union = ddl(compatSql, 'personal_ai_approval_ledger__v2')?.replace('personal_ai_approval_ledger__v2','personal_ai_approval_ledger');
  const indexes = (sql, names) => names.map(([name,columns]) => [name,columns,migrationStatements(sql).find(s => s.startsWith('CREATE INDEX') && s.includes(name))]);
  return {
    ledger: tableInvariant('personal_ai_approval_ledger', union, indexes(compatSql,[
      ['idx_approval_ledger_binding',['operation','candidate_id','candidate_version','content_hash']],
      ['idx_approval_ledger_state',['operation','consumed','invalidated']]])),
    registry: tableInvariant('approval_ledger_operations',ddl(compatSql,'approval_ledger_operations')) + ` AND (${registryQuery})=${literal(JSON.stringify(OPERATIONS))}`,
    candidate: goldenSql ? tableInvariant('knowledge_candidates',ddl(goldenSql,'knowledge_candidates'),indexes(goldenSql,[
      ['idx_knowledge_candidates_status',['status']],['idx_knowledge_candidates_asset',['asset_id']]])) : null
  };
}
async function holds(db, predicate) {
  return Number((await db.prepare(`SELECT CASE WHEN (${predicate}) THEN 1 ELSE 0 END AS ok`).first()).ok) === 1;
}
export async function inspectLedger(db, compatSql) {
  const row = await db.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name='personal_ai_approval_ledger'").first();
  if (!row) return 'ABSENT';
  if (normalize(row.sql,LEGACY) === normalize(LEGACY)) {
    return await holds(db,tableInvariant('personal_ai_approval_ledger',LEGACY)) ? 'LEGACY' : 'DRIFT';
  }
  try {
    const inv=reviewedInvariants(compatSql);
    return await holds(db, inv.ledger + ' AND ' + inv.registry) ? 'UNION' : 'DRIFT';
  } catch { return 'DRIFT'; }
}
export async function runKnowledgeLedgerMigrations(db, { compatSql, goldenSql, compatSha256, backupVerified } = {}) {
  if (!db?.batch || backupVerified !== true) throw new Error('HALT_VERIFIED_BACKUP_REQUIRED');
  if (await hash(goldenSql) !== GOLDEN_HASH || await hash(compatSql) !== compatSha256) throw new Error('HALT_MIGRATION_HASH_MISMATCH');
  // Retain the ORIGINAL inspected schema and authority/history snapshot. Never
  // re-read a later ledger SQL string as the expected precondition.
  const schema = (await db.prepare(schemaQuery).first()).value;
  const objects = JSON.parse(schema);
  const exists = name => objects.some(r => r[0]==='table' && r[1]===name);
  let registry=null, history=null, names=[];
  try {
    if (exists('approval_ledger_operations')) registry=(await db.prepare(registryQuery).first()).value;
    if (exists('d1_migrations')) {
      history=(await db.prepare(historyQuery).first()).value;
      names=JSON.parse(history).map(r=>r[1]);
    }
  } catch { throw new Error('HALT_HISTORY_OR_REGISTRY_SCHEMA_DRIFT'); }
  const shape=await inspectLedger(db,compatSql);
  if (!['LEGACY','UNION'].includes(shape)) throw new Error(`HALT_LEDGER_${shape}`);
  const inv=reviewedInvariants(compatSql,goldenSql);
  if (exists('knowledge_candidates') && !await holds(db,inv.candidate)) throw new Error('HALT_CANDIDATE_SCHEMA_DRIFT');
  if (new Set(names).size!==names.length || (names.includes(COMPAT_NAME)&&shape!=='UNION') ||
      (names.includes(GOLDEN_NAME)&&(!names.includes(COMPAT_NAME)||!exists('knowledge_candidates')||names.indexOf(GOLDEN_NAME)<names.indexOf(COMPAT_NAME)))) throw new Error('HALT_HISTORY_SCHEMA_MISMATCH');
  if(objects.some(r=>r[0]==='trigger'&&r[2]==='d1_migrations')) throw new Error('HALT_HISTORY_TRIGGER_DRIFT');
  const guards = [db.prepare(assertion(`(${schemaQuery}) = ?`)).bind(schema)];
  if(registry!==null) guards.push(db.prepare(assertion(`(${registryQuery}) = ?`)).bind(registry));
  if(history!==null) guards.push(db.prepare(assertion(`(${historyQuery}) = ?`)).bind(history));
  const already=names.includes(GOLDEN_NAME);
  if (!already) {
    guards.push(db.prepare('CREATE TABLE IF NOT EXISTS d1_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)'));
    if (!names.includes(COMPAT_NAME)&&shape==='LEGACY') guards.push(...migrationStatements(compatSql).map(s=>db.prepare(s)));
    guards.push(...migrationStatements(goldenSql).map(s=>db.prepare(s)));
  }
  // All postconditions execute INSIDE the batch, BEFORE success history. D1
  // rolls back preceding DDL/data on a failing statement, not on a JS post-read.
  guards.push(db.prepare(assertion(inv.ledger+' AND '+inv.registry+' AND '+inv.candidate)));
  guards.push(db.prepare(assertion(`(${historyQuery}) = ?`)).bind(history??'[]'));
  if (!already) {
    if (!names.includes(COMPAT_NAME)) guards.push(db.prepare('INSERT INTO d1_migrations (name) VALUES (?)').bind(COMPAT_NAME));
    guards.push(db.prepare('INSERT INTO d1_migrations (name) VALUES (?)').bind(GOLDEN_NAME));
  }
  try { await db.batch(guards); }
  catch(error) { throw new Error('HALT_TRANSACTION_INVARIANT: '+error.message,{cause:error}); }
  return already ? {status:'ALREADY_APPLIED',shape} : {status:'APPLIED',shape:'UNION',order:[COMPAT_NAME,GOLDEN_NAME]};
}
