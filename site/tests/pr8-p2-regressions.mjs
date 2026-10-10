import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash, generateKeyPairSync, sign, verify } from 'node:crypto';
import { createKnowledgeApprovalRoute } from '../worker/index.js';
import { sqliteD1 } from '../../tests/helpers/sqlite-d1.mjs';
import { runKnowledgeLedgerMigrations, inspectLedger, migrationStatements } from '../../worker/knowledge-ledger-migrations.js';
const compatSql = readFileSync(new URL('../../worker/migrations/0002z_knowledge_approval_ledger_compat.sql', import.meta.url), 'utf8');
const goldenSql = readFileSync(new URL('../../worker/migrations/0003_knowledge_candidate_golden_pipeline.sql', import.meta.url), 'utf8');
const sha = s => createHash('sha256').update(s).digest('hex');
const migrations = { compatSql, goldenSql, compatSha256: sha(compatSql), backupVerified: true };
const source = readFileSync(new URL('../../worker/index.js', import.meta.url), 'utf8');
const worker = await import('data:text/javascript;base64,' + Buffer.from(source + '\nexport {promoteKnowledgeCandidate, recordKnowledgeCandidateReview, KNOWLEDGE_CANDIDATE_RESERVE, APPROVAL_LEDGER_CONSUME};').toString('base64'));
function legacyDB() {
  const db = sqliteD1();
  db.sqlite.exec(`CREATE TABLE personal_ai_approval_ledger (
    approval_id TEXT PRIMARY KEY, requesting_user_hash TEXT NOT NULL CHECK(length(requesting_user_hash)=64),
    operation TEXT CHECK(operation IN ('deploy_worker_version','write_decision_record')),
    exact_target TEXT, payload_sha256 TEXT, created_at INTEGER, expires_at INTEGER, consumed_at INTEGER) STRICT;
    INSERT INTO personal_ai_approval_ledger VALUES('legacy', '${'a'.repeat(64)}', 'deploy_worker_version', 'target', '${'b'.repeat(64)}', 1, 4102444800, NULL);`);
  return db;
}
const snapshot = db => {
  const schema=db.sqlite.prepare("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").all();
  const data=schema.filter(r=>r.type==='table').map(r=>[r.name,db.sqlite.prepare('SELECT * FROM "'+r.name.replaceAll('"','""')+'" ORDER BY rowid').all()]);
  return JSON.stringify({schema,data});
};
async function unionDB(history = false) {
  const db = legacyDB();
  if (history) await runKnowledgeLedgerMigrations(db, migrations);
  else await db.batch(migrationStatements(compatSql).map(s => db.prepare(s)));
  return db;
}
async function approvedDB() {
  const db = await unionDB(true), content = 'synthetic knowledge only';
  const tuple = { candidate_id:'cand-test', candidate_version:1, content_hash:sha(content) };
  db.sqlite.exec(`CREATE TABLE assets(asset_id TEXT PRIMARY KEY,asset_type TEXT,schema_version TEXT,title TEXT,status TEXT,current_version INTEGER,content_hash TEXT,created_at TEXT,updated_at TEXT);
    CREATE TABLE asset_versions(asset_id TEXT,version INTEGER,content TEXT,content_hash TEXT,provenance TEXT,verification TEXT,created_by TEXT,created_at TEXT,PRIMARY KEY(asset_id,version));`);
  db.sqlite.prepare("INSERT INTO knowledge_candidates(candidate_id,asset_id,title,status,content,content_hash,version,created_at,review_state,review_result,reviewed_at) VALUES(?,'knowledge:test','test','APPROVED_FOR_PROMOTION',?,?,1,'now','PASS','PASS','review-1')").run(tuple.candidate_id,content,tuple.content_hash);
  await mint(db,tuple,'synthetic-1');
  return {db,tuple};
}
async function mint(db,tuple,ceremony) {
  const keys=generateKeyPairSync('ed25519'), origin='https://existing-site.example';
  const candidate=db.sqlite.prepare('SELECT * FROM knowledge_candidates').get();
  const exact=JSON.stringify({operation:'KNOWLEDGE_PROMOTION',...tuple,asset_id:candidate.asset_id,review_result:'PASS',reviewed_at:candidate.reviewed_at});
  const signature=sign(null,Buffer.from(exact),keys.privateKey);
  let used=false;
  const route=createKnowledgeApprovalRoute({db,origin,humanGate:{async verifyAndConsume(expected){
    assert.equal(used,false); used=true;
    assert.equal(expected.exact_target,exact);assert.equal(expected.payload_sha256,sha(exact));
    assert.equal(verify(null,Buffer.from(expected.exact_target),keys.publicKey,signature),true);
    return {verified:true,operation:expected.operation,exact_target:expected.exact_target,payload_sha256:expected.payload_sha256,
      requesting_user_hash:'c'.repeat(64),signer_identity:'synthetic-owner',ceremony_id:ceremony,expires_at:Math.floor(Date.now()/1000)+300};
  }}});
  assert.equal((await route(new Request(origin+'/knowledge/approve',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({...tuple,assertion:{}})}))).status,200);
}
async function rejectedPromotion(db,tuple) {
  const result=await worker.promoteKnowledgeCandidate({ASSET_DB:db},{...tuple,review_result:'PASS'});
  assert.equal(result.structuredContent.status,'REJECTED'); assert.equal(result.structuredContent.write_calls,0);
  assert.equal(db.sqlite.prepare('SELECT count(*) n FROM assets').get().n,0);
  assert.equal(db.sqlite.prepare("SELECT consumed_at FROM personal_ai_approval_ledger WHERE operation='KNOWLEDGE_PROMOTION'").get().consumed_at,null);
}
test('P2-1: post-mint actual PASS review rejects stale receipt without consumption or writer attempt',async()=>{
  const {db,tuple}=await approvedDB();
  await worker.recordKnowledgeCandidateReview({ASSET_DB:db},{candidate_id:tuple.candidate_id,review_result:'PASS'});
  await rejectedPromotion(db,tuple);
});
test('P2-1: actual re-review between read and reservation rejects with no writer or consumption',async()=>{
  const {db,tuple}=await approvedDB(),prepare=db.prepare.bind(db);let injected=false;
  db.prepare=sql=>{const s=prepare(sql);if(sql===worker.KNOWLEDGE_CANDIDATE_RESERVE){
    const bind=s.bind.bind(s);s.bind=(...args)=>{const bound=bind(...args),run=bound.run.bind(bound);bound.run=async()=>{
      injected=true;const review=await worker.recordKnowledgeCandidateReview({ASSET_DB:db},{candidate_id:tuple.candidate_id,review_result:'PASS'});
      assert.equal(review.structuredContent.review_state,'PASS');return run();};return bound;};}return s;};
  await rejectedPromotion(db,tuple);assert.equal(injected,true);
});
test('P2-1: frozen-clock re-PASS changes generation; fresh equal-expiry receipt can promote once',async()=>{
  const OriginalDate=globalThis.Date,fixed=OriginalDate.now();
  globalThis.Date=class extends OriginalDate {constructor(...args){super(...(args.length?args:[fixed]));}static now(){return fixed;}};
  try {
    const {db,tuple}=await approvedDB();
    await worker.recordKnowledgeCandidateReview({ASSET_DB:db},{candidate_id:tuple.candidate_id,review_result:'PASS'});
    await mint(db,tuple,'same-ms-old');
    const before=db.sqlite.prepare('SELECT reviewed_at FROM knowledge_candidates').get().reviewed_at;
    await worker.recordKnowledgeCandidateReview({ASSET_DB:db},{candidate_id:tuple.candidate_id,review_result:'PASS'});
    const after=db.sqlite.prepare('SELECT reviewed_at FROM knowledge_candidates').get().reviewed_at;
    assert.notEqual(after,before);assert.equal(OriginalDate.parse(after),OriginalDate.parse(before)+1);
    const rejected=await worker.promoteKnowledgeCandidate({ASSET_DB:db},{...tuple,review_result:'PASS'});
    assert.equal(rejected.structuredContent.write_calls,0);
    await mint(db,tuple,'same-ms-fresh');
    const result=await worker.promoteKnowledgeCandidate({ASSET_DB:db},{...tuple,review_result:'PASS'});
    assert.equal(result.structuredContent.status,'WRITTEN');
    assert.equal(db.sqlite.prepare('SELECT count(*) n FROM asset_versions').get().n,1);
    assert.equal(db.sqlite.prepare("SELECT consumed_at FROM personal_ai_approval_ledger WHERE approval_id='knowledge:same-ms-old'").get().consumed_at,null);
    assert.equal(db.sqlite.prepare("SELECT consume_count FROM personal_ai_approval_ledger WHERE approval_id='knowledge:same-ms-fresh'").get().consume_count,1);
  } finally {globalThis.Date=OriginalDate;}
});
for(const change of ["exact_target='{}'","payload_sha256='bad'","operation='write_decision_record'"]) for(const boundary of ['reservation','consumption']) test(`P2-1: approval ${change} races ${boundary}`,async()=>{
  const {db,tuple}=await approvedDB(),prepare=db.prepare.bind(db);let injected=false;
  db.prepare=sql=>{const s=prepare(sql);if(sql===(boundary==='reservation'?worker.KNOWLEDGE_CANDIDATE_RESERVE:worker.APPROVAL_LEDGER_CONSUME)){
    const bind=s.bind.bind(s);s.bind=(...args)=>{const bound=bind(...args),run=bound.run.bind(bound);bound.run=async()=>{
      injected=true;db.sqlite.exec(`UPDATE personal_ai_approval_ledger SET ${change} WHERE approval_id='knowledge:synthetic-1'`);return run();};return bound;};}return s;};
  const result=await worker.promoteKnowledgeCandidate({ASSET_DB:db},{...tuple,review_result:'PASS'});
  assert.equal(result.structuredContent.write_calls,0);assert.equal(injected,true);
  assert.equal(db.sqlite.prepare('SELECT count(*) n FROM assets').get().n,0);
  assert.equal(db.sqlite.prepare("SELECT consumed_at FROM personal_ai_approval_ledger WHERE approval_id='knowledge:synthetic-1'").get().consumed_at,null);
});
for (const change of ["reviewed_at='review-2'","asset_id='knowledge:other'","version=2","content_hash='changed'","review_result='FAIL'"]) {
  for (const boundary of ['reservation','consumption']) test(`P2-1: ${change} races ${boundary}`,async()=>{
    const {db,tuple}=await approvedDB(), prepare=db.prepare.bind(db); let injected=false;
    db.prepare=sql=>{const s=prepare(sql);if(sql===(boundary==='reservation'?worker.KNOWLEDGE_CANDIDATE_RESERVE:worker.APPROVAL_LEDGER_CONSUME)){
      const bind=s.bind.bind(s);s.bind=(...args)=>{const bound=bind(...args),run=bound.run.bind(bound);bound.run=async()=>{
        assert.equal(injected,false);injected=true;db.sqlite.exec(`UPDATE knowledge_candidates SET ${change}`);return run();};return bound;};}return s;};
    await rejectedPromotion(db,tuple);assert.equal(injected,true);
  });
}
for(const change of ["exact_target='{}'","payload_sha256='bad'","exact_target=NULL","payload_sha256=NULL"]) test(`P2-1: signed target corruption ${change}`,async()=>{
  const {db,tuple}=await approvedDB();db.sqlite.exec(`UPDATE personal_ai_approval_ledger SET ${change} WHERE operation='KNOWLEDGE_PROMOTION'`);await rejectedPromotion(db,tuple);
});
const ledgerIndexes={
  unique:'CREATE UNIQUE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,content_hash)',
  partial:'CREATE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,content_hash) WHERE consumed=0',
  expression:'CREATE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,lower(content_hash))',
  descending:'CREATE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,content_hash DESC)',
  collation:'CREATE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,content_hash COLLATE NOCASE)',
  wrong_table:'CREATE TABLE other(operation TEXT,candidate_id TEXT,candidate_version INTEGER,content_hash TEXT); CREATE INDEX idx_approval_ledger_binding ON other(operation,candidate_id,candidate_version,content_hash)',
  extra_enforcing:'CREATE INDEX idx_approval_ledger_binding ON personal_ai_approval_ledger(operation,candidate_id,candidate_version,content_hash); CREATE UNIQUE INDEX extra_enforcing ON personal_ai_approval_ledger(exact_target)'
};
for(const [name,ddl] of Object.entries(ledgerIndexes)) for(const history of [false,true]) test(`P2-2: ${name}, ${history?'idempotent':'adoption'} halts unchanged`,async()=>{
  const db=await unionDB(history);db.sqlite.exec('DROP INDEX idx_approval_ledger_binding;'+ddl);const before=snapshot(db);
  assert.equal(await inspectLedger(db,compatSql),'DRIFT');await assert.rejects(runKnowledgeLedgerMigrations(db,migrations));assert.equal(snapshot(db),before);
});
const candidateDDL=migrationStatements(goldenSql)[0];
const candidateDrifts={missing_column:'CREATE TABLE knowledge_candidates(candidate_id TEXT PRIMARY KEY,status TEXT,asset_id TEXT)',
  type:candidateDDL.replace('version INTEGER','version TEXT'),default:candidateDDL.replace('DEFAULT 1','DEFAULT 2'), literal_whitespace:candidateDDL.replace("'NOT_REVIEWED'","'NOT_ REVIEWED'"), literal_case:candidateDDL.replace("'NOT_REVIEWED'","'not_reviewed'"), pk:candidateDDL.replace('candidate_id TEXT PRIMARY KEY','candidate_id TEXT'),
  nullability:candidateDDL.replace('asset_id TEXT NOT NULL','asset_id TEXT'),constraint:candidateDDL.replace('status TEXT NOT NULL',"status TEXT NOT NULL CHECK(status='DRAFT')")};
for(const [name,ddl] of Object.entries(candidateDrifts)) for(const path of ['legacy','adoption','idempotent']) test(`P2-4: candidate ${name} on ${path} halts unchanged`,async()=>{
  const db=path==='legacy'?legacyDB():await unionDB(path==='idempotent');
  db.sqlite.exec('DROP TABLE IF EXISTS knowledge_candidates;'+ddl);const before=snapshot(db);
  await assert.rejects(runKnowledgeLedgerMigrations(db,migrations));assert.equal(snapshot(db),before);
});
for(const change of ['missing','wrong','unique','partial','expression','descending','collation','extra_enforcing']) for(const index of ['status','asset']) for(const path of ['legacy','adoption','idempotent']) test(`P2-4: candidate ${index} index ${change} on ${path}`,async()=>{
  const db=path==='legacy'?legacyDB():await unionDB(path==='idempotent');
  if(path!=='idempotent')db.sqlite.exec(migrationStatements(goldenSql).slice(0,3).join(';'));
  db.sqlite.exec('DROP INDEX idx_knowledge_candidates_'+index);
  const definitions={missing:'',wrong:'CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(asset_id)',unique:'CREATE UNIQUE INDEX idx_knowledge_candidates_status ON knowledge_candidates(status)',partial:"CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(status) WHERE status='DRAFT'",descending:'CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(status DESC)',collation:'CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(status COLLATE NOCASE)',expression:'CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(lower(status))',extra_enforcing:'CREATE INDEX idx_knowledge_candidates_status ON knowledge_candidates(status); CREATE UNIQUE INDEX candidate_enforcing ON knowledge_candidates(reviewed_at)'};
  let definition=definitions[change];
  if(index==='asset')definition=change==='wrong' ? 'CREATE INDEX idx_knowledge_candidates_asset ON knowledge_candidates(status)' : definition.replaceAll('idx_knowledge_candidates_status','idx_knowledge_candidates_asset').replaceAll('status','asset_id');
  db.sqlite.exec(definition);const before=snapshot(db);await assert.rejects(runKnowledgeLedgerMigrations(db,migrations));assert.equal(snapshot(db),before);
});
for(const change of ['registry','index','candidate','history']) for(const path of ['legacy','adoption','idempotent']) test(`P2-3: pre-batch ${change} drift on ${path} rolls back all migration effects`,async()=>{
  const db=path==='legacy'?legacyDB():await unionDB(path==='idempotent'), batch=db.batch.bind(db);let afterDrift;
  db.batch=async statements=>{
    const changes={registry:path==='legacy'?"CREATE TABLE approval_ledger_operations(operation TEXT PRIMARY KEY,asset_type TEXT,canonical_writer TEXT,single_use INTEGER,replay_guard INTEGER)":"UPDATE approval_ledger_operations SET canonical_writer='wrongWriter' WHERE operation='KNOWLEDGE_PROMOTION'",
      index:path==='legacy'?'CREATE UNIQUE INDEX enforcing ON personal_ai_approval_ledger(exact_target)':'DROP INDEX idx_approval_ledger_state',
      candidate:path==='idempotent'?'ALTER TABLE knowledge_candidates ADD COLUMN extra TEXT':'CREATE TABLE knowledge_candidates(candidate_id TEXT PRIMARY KEY,status TEXT,asset_id TEXT)',
      history:path==='idempotent'?"DELETE FROM d1_migrations WHERE name LIKE '0003%'":"CREATE TABLE d1_migrations(id INTEGER PRIMARY KEY,name TEXT);INSERT INTO d1_migrations VALUES(1,'concurrent')"};
    db.sqlite.exec(changes[change]);afterDrift=snapshot(db);return batch(statements);
  };
  await assert.rejects(runKnowledgeLedgerMigrations(db,migrations));assert.equal(snapshot(db),afterDrift);
});
for(const change of ['registry','index','candidate','history']) test(`P2-3: in-batch ${change} postcondition failure rolls back legacy rebuild, candidate DDL, data and history`,async()=>{
  const db=legacyDB(),before=snapshot(db);let injected=false;
  db.failBefore=sql=>{if(!injected&&sql.startsWith('SELECT CASE WHEN')&&db.sqlite.prepare("SELECT name FROM sqlite_master WHERE name='knowledge_candidates'").get()){
    injected=true;db.sqlite.exec({registry:"UPDATE approval_ledger_operations SET canonical_writer='wrongWriter' WHERE operation='KNOWLEDGE_PROMOTION'",index:'DROP INDEX idx_approval_ledger_binding',candidate:'DROP INDEX idx_knowledge_candidates_asset',history:"INSERT INTO d1_migrations(name) VALUES('concurrent')"}[change]);}return false;};
  await assert.rejects(runKnowledgeLedgerMigrations(db,migrations));assert.equal(injected,true);assert.equal(snapshot(db),before);
});
test('ordered compatibility-only history applies golden suffix and idempotence leaves all bytes unchanged',async()=>{
  const db=await unionDB(true);db.sqlite.exec("DELETE FROM d1_migrations WHERE name='0003_knowledge_candidate_golden_pipeline.sql'");
  assert.equal((await runKnowledgeLedgerMigrations(db,migrations)).status,'APPLIED');
  const before=snapshot(db);assert.equal((await runKnowledgeLedgerMigrations(db,migrations)).status,'ALREADY_APPLIED');assert.equal(snapshot(db),before);
});
test('reversed suffix history and history triggers halt unchanged',async()=>{
  for(const change of ["UPDATE d1_migrations SET id=id+10; UPDATE d1_migrations SET id=1 WHERE name='0003_knowledge_candidate_golden_pipeline.sql'",
    "CREATE TRIGGER history_hook AFTER INSERT ON d1_migrations BEGIN UPDATE approval_ledger_operations SET canonical_writer='wrongWriter'; END;"]){
    const db=await unionDB(true);db.sqlite.exec(change);const before=snapshot(db);
    await assert.rejects(runKnowledgeLedgerMigrations(db,migrations));assert.equal(snapshot(db),before);
  }
});
