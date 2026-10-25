// Synthetic boundary tests; no production requests or credentials.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {createHmac}=require('node:crypto');
const source=fs.readFileSync(require('node:path').join(__dirname,'../worker/index.js'),'utf8');
const loaded=import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
async function call(method,name,args,scope='task.read') {
  const payload={kind:'access',aud:'mcp',scope,task_project:'cloud-assets-activation',exp:Math.floor(Date.now()/1000)+60};
  const body=Buffer.from(JSON.stringify(payload)).toString('base64url');
  const token=body+'.'+createHmac('sha256','synthetic').update(body).digest('base64url');
  const deny=()=>{throw Error('unexpected storage/network access');};
  const env={OAUTH_SIGNING_KEY:'synthetic',get TASK_REGISTRY(){return deny();},get ASSET_DB(){return deny();}};
  const old=global.fetch;global.fetch=deny;
  try {return await (await (await loaded).default.fetch(new Request('https://worker.invalid/mcp',{
    method:'POST',headers:{Authorization:'Bearer '+token},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params:{name,arguments:args}})}),env)).json();}
  finally{global.fetch=old;}
}
test('task.read discovery adds only the fixed-project registered catalog',async()=>{
  const r=await call('tools/list');assert.deepEqual(r.result.tools.map(t=>t.name),['get_task_result','list_pending_results','list_registered_tasks']);
});
test('production task.read cannot enter new observation or write branches',async()=>{
  for(const name of ['get_task_execution_status','submit_task','write_knowledge_candidate']) {
    const r=await call('tools/call',name,{task_id:'cf-123456789abc'});assert.equal(r.error.code,-32002);
  }
});
test('production task.read input guard stays fail closed',async()=>{
  const r=await call('tools/call','get_task_result',{task_id:'../other'});assert.equal(r.result.isError,true);
});
test('production Knowledge gate still rejects raw promotion without exact registered approval',async()=>{
  const r=await call('tools/call','write_knowledge_candidate',{content:'synthetic'},'mcp');
  assert.equal(r.result.structuredContent.reason,'EXACT_REGISTERED_KNOWLEDGE_APPROVAL_REQUIRED');
  assert.equal(r.result.structuredContent.canonical_write_performed,false);
});
test('task.read issued tokens retain project binding through access and refresh',async()=>{
 const api=await import('data:text/javascript;base64,'+Buffer.from(source+'\nexport {issueTokens,mcpAuthorized,tokenEndpoint};').toString('base64'));
 const env={OAUTH_SIGNING_KEY:'synthetic'};
 const tokens=await api.issueTokens(env,'task.read');
 const auth=await api.mcpAuthorized(new Request('https://fixture.invalid/mcp',{headers:{Authorization:'Bearer '+tokens.access_token}}),env);
 assert.equal(auth.payload.task_project,'cloud-assets-activation');
 const response=await api.tokenEndpoint(new Request('https://fixture.invalid/token',{method:'POST',body:new URLSearchParams({grant_type:'refresh_token',refresh_token:tokens.refresh_token})}),env);
 assert.equal(response.status,200);
 const refreshed=await response.json();
 assert.deepEqual((await api.mcpAuthorized(new Request('https://fixture.invalid/mcp',{headers:{Authorization:'Bearer '+refreshed.access_token}}),env)).scopes,['task.read']);
});
