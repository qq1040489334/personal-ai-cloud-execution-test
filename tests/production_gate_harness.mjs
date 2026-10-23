// Synthetic in-memory SQLite adapter. Never contacts production.
import {DatabaseSync} from 'node:sqlite';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../worker/index.js',import.meta.url),'utf8');
const api=await import('data:text/javascript;base64,'+Buffer.from(source+`\nexport {SNAPSHOT,handleMcp,writeKnowledgeCandidate,verifyKnowledgeVersion,checkedSchema,stageKnowledgeCandidate,recordKnowledgeCandidateReview,submitKnowledgeCandidateForReview,readKnowledgeCandidate,guardedKnowledgePromote,toolWriteKnowledgeCandidate,exactTarget,candidatePayload,hash,RP,SEED_EVIDENCE};`).toString('base64'));
export {api};
export function fixture(){
 const sqlite=new DatabaseSync(':memory:');sqlite.exec('PRAGMA foreign_keys=ON');
 for(const type of ['table','index','trigger'])for(const row of api.SNAPSHOT)if(row.type===type&&row.sql)sqlite.exec(row.sql);
 for(const [operation,type,writer] of [['KNOWLEDGE_PROMOTION','KNOWLEDGE','writeKnowledgeCandidate'],['decision_write','DECISION','writeDecisionRecord'],['deploy_worker_version','DEPLOY','deployWorkerVersion'],['knowledge_write','KNOWLEDGE','writeKnowledgeCandidate'],['write_decision_record','DECISION','writeDecisionRecord'],['write_project_status_record','REALITY','writeProjectStatusRecord']])sqlite.prepare('INSERT INTO approval_ledger_operations VALUES (?,?,?,1,1)').run(operation,type,writer);
 const calls=[];
 const db={prepare(sql){return {bind(...args){return statement(sql,args)},...statement(sql,[])}}};
 function statement(sql,args){return {sql,args,async first(){calls.push(sql);return sqlite.prepare(sql).get(...args)||null},async all(){calls.push(sql);return {results:sqlite.prepare(sql).all(...args)}},async run(){calls.push(sql);const r=sqlite.prepare(sql).run(...args);return {meta:{changes:Number(r.changes)}}}};}
 db.batch=async statements=>{sqlite.exec('BEGIN');try{const out=[];for(const st of statements)out.push(await st.run());sqlite.exec('COMMIT');return out}catch(e){sqlite.exec('ROLLBACK');throw e}};
 return {sqlite,db,env:{ASSET_DB:db},calls};
}
export async function reviewed(f,id='cand-r5'){
 const provenance={source:{identity:'synthetic',location:'fixture'},source_version:'1',content_version:'1',captured_at:new Date().toISOString()};
 const created=await api.stageKnowledgeCandidate(f.env,{candidate_id:id,asset_id:'knowledge:'+id,title:'fixture',content:'fixture',provenance});
 if(created.isError)throw Error(created.text);
 const reviewed=await api.recordKnowledgeCandidateReview(f.env,{candidate_id:id,review_result:'PASS',reviewed_by:'independent-fixture',review_evidence_ref:'fixture:review',review_evidence_sha256:'a'.repeat(64)});
 if(reviewed.isError)throw Error(reviewed.text);
 return f.sqlite.prepare('SELECT * FROM knowledge_candidates WHERE candidate_id=?').get(id);
}
export async function approve(f,k,letter='A'){
 const now=Date.now(), ceremony=letter.repeat(43),approval='knowledge:'+ceremony,challenge='PAI:'+ceremony+':fixture';
 const owner=letter.toLowerCase().repeat(64),signer='s'.repeat(73),epoch='fixture-epoch-0001';
 const exact=api.exactTarget(api.candidatePayload(k)),digest=await api.hash(exact);
 f.sqlite.prepare(`INSERT INTO approval_credential_counters_v1 VALUES (?,?,?,?,'ACTIVE','MONOTONIC',2,1,?,?,?)`).run(owner,api.RP,signer,epoch,now,now,api.SEED_EVIDENCE);
 f.sqlite.prepare(`INSERT INTO personal_ai_approval_ledger (approval_id,requesting_user_hash,operation,exact_target,payload_sha256,created_at,expires_at,state,exact_target_json,time_basis) VALUES (?,?,'KNOWLEDGE_PROMOTION',?,?,?,?,'CHALLENGE_PENDING',?,'epoch_ms_v1')`).run(challenge,owner,'knowledge:v1:sha256:'+digest,digest,now,now+300000,exact);
 f.sqlite.prepare(`INSERT INTO approval_assertion_commits_v1 VALUES (?,?,?,?,?,?,?,?,'MONOTONIC',2,3,?,?,?,?,?)`).run(ceremony,challenge,approval,owner,api.RP,signer,epoch,1,exact,digest,now,now+300000,now);
 return {candidate_operation:'promote',candidate_id:k.candidate_id,candidate_version:k.version,content_hash:k.content_hash,approval_id:approval};
}
