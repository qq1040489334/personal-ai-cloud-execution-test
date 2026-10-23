// Replacement for old ISO-expiry/mock-ledger Worker scenarios. Real production
// schema + triggers, isolated SQLite only. Python historical migration tests remain.
import assert from 'node:assert/strict';
import {fixture,reviewed,approve,api} from './production_gate_harness.mjs';
const scenario=process.argv[2];
const f=fixture();
const reviewArgs=id=>({candidate_id:id,review_result:'FAIL',reviewed_by:'reviewer-fixture',review_evidence_ref:'fixture:fail',review_evidence_sha256:'b'.repeat(64)});
const assets=()=>Number(f.sqlite.prepare('SELECT count(*) n FROM assets').get().n);
const consumed=()=>Number(f.sqlite.prepare("SELECT count(*) n FROM personal_ai_approval_ledger WHERE state='CONSUMED'").get().n);
function blocked(r){assert.equal(r.isError,true);assert.equal(r.structuredContent.status,'BLOCKED');assert.equal(r.structuredContent.retry_allowed,false)}
if(scenario==='direct'||scenario==='mcp'){
 const before=f.calls.length;
 let r;
 if(scenario==='mcp'){const response=await api.handleMcp(new Request('https://fixture.invalid/mcp',{method:'POST',body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'write_knowledge_candidate',arguments:{asset_id:'knowledge:x',content:'unapproved'}}})}),f.env,{}, {scopes:['mcp']});const body=await response.json();r={isError:body.result.isError,structuredContent:body.result.structuredContent};}
 else r=await api.toolWriteKnowledgeCandidate(f.env,{asset_id:'knowledge:x',content:'unapproved'});
 blocked(r);assert.equal(r.structuredContent.canonical_write_performed,false);assert.equal(f.calls.length,before);assert.equal(assets(),0);
}else if(scenario==='lifecycle'){
 const provenance={source:{identity:'fixture',location:'fixture'},source_version:'1',content_version:'1',captured_at:new Date().toISOString()};
 const c=await api.stageKnowledgeCandidate(f.env,{candidate_id:'lifecycle',asset_id:'knowledge:lifecycle',title:'fixture',content:'hello',provenance});assert.equal(c.isError,false);
 assert.equal((await api.readKnowledgeCandidate(f.env,{candidate_id:'lifecycle'})).structuredContent.candidate.status,'DRAFT');
 assert.equal((await api.submitKnowledgeCandidateForReview(f.env,{candidate_id:'lifecycle'})).isError,false);
 const noEvidence=await api.recordKnowledgeCandidateReview(f.env,{candidate_id:'lifecycle',review_result:'PASS'});assert.equal(noEvidence.isError,true);
 const reviewed=await api.recordKnowledgeCandidateReview(f.env,{...reviewArgs('lifecycle'),review_result:'PASS'});assert.equal(reviewed.isError,false);assert.equal(assets(),0);
 const invoke=async(op,scopes)=>{const response=await api.handleMcp(new Request('https://fixture.invalid/mcp',{method:'POST',body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'write_knowledge_candidate',arguments:{candidate_operation:op,candidate_id:'lifecycle'}}})}),f.env,{}, {scopes});return response.json()};
 assert.equal((await invoke('read',['asset.read'])).result.isError,false);assert.equal((await invoke('review',['asset.read'])).error.code,-32002);assert.equal((await invoke('read',[])).error.code,-32001);
}else{
 const k=await reviewed(f);let args;
 if(scenario==='forged'){
  const r=await api.toolWriteKnowledgeCandidate(f.env,{candidate_id:k.candidate_id,promotion_decision:'PROMOTE',approved_by:'fake'});blocked(r);assert.equal(assets(),0);
 }else{
  args=await approve(f,k);f.calls.length=0;
  if(scenario==='draft')f.sqlite.prepare("UPDATE knowledge_candidates SET status='DRAFT' WHERE candidate_id=?").run(k.candidate_id);
  if(scenario==='hash')args.content_hash='0'.repeat(64);
  if(scenario==='bound'){const other=await reviewed(f,'other-candidate');args={...args,candidate_id:other.candidate_id,candidate_version:other.version,content_hash:other.content_hash};}
  if(scenario==='expired'){
   const now=Date.now();f.sqlite.prepare('UPDATE personal_ai_approval_ledger SET created_at=?,expires_at=? WHERE approval_id=?').run(now-300001,now-1,args.approval_id);
  }
  if(scenario==='consumed')f.sqlite.prepare("UPDATE personal_ai_approval_ledger SET consumed=1,state='CONSUMED',consume_count=1,consumed_at=? WHERE approval_id=?").run(Date.now(),args.approval_id);
  if(['fail','reapprove'].includes(scenario)){
   const fail=await api.recordKnowledgeCandidateReview(f.env,reviewArgs(k.candidate_id));assert.equal(fail.isError,false);
   assert.equal(f.sqlite.prepare('SELECT invalidated FROM personal_ai_approval_ledger WHERE approval_id=?').get(args.approval_id).invalidated,1);
   if(scenario==='reapprove')assert.equal((await api.recordKnowledgeCandidateReview(f.env,{...reviewArgs(k.candidate_id),review_result:'PASS'})).isError,false);
  }
  if(scenario==='reserved_with'){const done=await api.toolWriteKnowledgeCandidate(f.env,args);assert.equal(done.isError,false);assert.equal(assets(),1)}
  if(scenario.startsWith('reserved'))f.sqlite.prepare("UPDATE knowledge_candidates SET status='PROMOTION_RESERVED' WHERE candidate_id=?").run(k.candidate_id);
  if(scenario==='schema')f.sqlite.exec('CREATE INDEX unexpected_idx ON knowledge_candidates(title)');
  if(scenario==='fail_first'){
   const normalBatch=f.db.batch;let injected=false;
   f.db.batch=async ss=>{if(!injected&&ss[0]?.sql.includes("SET status='PROMOTION_RESERVED'")){injected=true;assert.equal((await api.recordKnowledgeCandidateReview(f.env,reviewArgs(k.candidate_id))).isError,false);}return normalBatch(ss)};
  }
  if(scenario==='review_cas'){
   const normalBatch=f.db.batch;let injected=false;
   f.db.batch=async ss=>{if(!injected&&ss[0]?.sql.startsWith('UPDATE knowledge_candidates SET status=?,review_state=')){injected=true;f.sqlite.prepare('UPDATE knowledge_candidates SET reviewed_at=? WHERE candidate_id=?').run('concurrent-review',k.candidate_id);}return normalBatch(ss)};
   assert.equal((await api.recordKnowledgeCandidateReview(f.env,reviewArgs(k.candidate_id))).isError,true);
   assert.equal(f.sqlite.prepare('SELECT invalidated FROM personal_ai_approval_ledger WHERE approval_id=?').get(args.approval_id).invalidated,0);
   assert.equal(f.sqlite.prepare('SELECT review_state FROM knowledge_candidates WHERE candidate_id=?').get(k.candidate_id).review_state,'PASS');
  }
  let result;
  if(['writer_failure','readback_failure','race_consume','race_writer','race_close'].includes(scenario)){
   const normalBatch=f.db.batch;
   let reviewResult=null;
   if(scenario==='race_consume')f.db.batch=async ss=>{const out=await normalBatch(ss);if(ss[0]?.sql.includes("SET status='PROMOTION_RESERVED'"))reviewResult=await api.recordKnowledgeCandidateReview(f.env,reviewArgs(k.candidate_id));return out};
   result=await api.guardedKnowledgePromote(f.env,args,{
    writer:async(env,input)=>{
     if(scenario==='race_writer')reviewResult=await api.recordKnowledgeCandidateReview(f.env,reviewArgs(k.candidate_id));
     if(scenario==='writer_failure')return {isError:true};
     const written=await api.writeKnowledgeCandidate(env,input);
     if(scenario==='race_close')reviewResult=await api.recordKnowledgeCandidateReview(f.env,reviewArgs(k.candidate_id));
     return written;
    },verifyVersion:async(...a)=>scenario==='readback_failure'?false:api.verifyKnowledgeVersion(...a)
   });
   if(scenario.startsWith('race')){assert.equal(result.isError,false);assert.equal(assets(),1)}else{blocked(result);assert.equal(result.structuredContent.outcome,'UNKNOWN_RECONCILE_REQUIRED')}assert.equal(consumed(),1);
   if(scenario.startsWith('race')){assert.equal(reviewResult.structuredContent.status,'REJECTED');assert.equal(reviewResult.structuredContent.review_recorded,false);}
  }else{
   result=await api.toolWriteKnowledgeCandidate(f.env,args);
   if(['success','repeat','terminal','no_mint'].includes(scenario)){
    assert.equal(result.isError,false);assert.equal(result.structuredContent.read_back_verified,true);assert.equal(assets(),1);assert.equal(consumed(),1);
    if(scenario==='no_mint'){assert.ok(f.calls.some(sql=>sql.startsWith('UPDATE personal_ai_approval_ledger')));assert.ok(!f.calls.some(sql=>/^\s*INSERT\s+INTO\s+(personal_ai_approval_ledger|approval_assertion_commits_v1)/i.test(sql)));}
    if(scenario==='repeat'){blocked(await api.toolWriteKnowledgeCandidate(f.env,args));assert.equal(assets(),1);assert.equal(consumed(),1)}
    if(scenario==='terminal'){assert.equal((await api.recordKnowledgeCandidateReview(f.env,reviewArgs(k.candidate_id))).structuredContent.status,'REJECTED');assert.equal(f.sqlite.prepare('SELECT status FROM knowledge_candidates WHERE candidate_id=?').get(k.candidate_id).status,'CANONICAL_READBACK_VERIFIED')}
   }else {blocked(result);assert.equal(assets(),scenario==='reserved_with'?1:0);}
   if(scenario==='reapprove'){const refreshed=f.sqlite.prepare('SELECT * FROM knowledge_candidates WHERE candidate_id=?').get(k.candidate_id);const fresh=await approve(f,refreshed,'B');const done=await api.toolWriteKnowledgeCandidate(f.env,fresh);assert.equal(done.isError,false);assert.equal(assets(),1);assert.equal(consumed(),1)}
  }
 }
}
console.log(JSON.stringify({scenario,passed:true,production_access:false}));
