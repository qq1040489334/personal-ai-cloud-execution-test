// Offline MCP boundary tests: synthetic KV, signed fixture tokens, no sockets.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createHmac}=require('node:crypto');
const source=fs.readFileSync(path.join(__dirname,'../worker/index.js'),'utf8');
const loaded=import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const cursorAPI=import('data:text/javascript;base64,'+Buffer.from(source+'\nexport {sealTaskCatalogCursor};').toString('base64'));
const sealed=async cursor=>(await cursorAPI).sealTaskCatalogCursor({OAUTH_SIGNING_KEY:'fixture-signing-key'},cursor);
const projectId='cloud-assets-activation';
const id=n=>'cf-'+n.toString(16).padStart(12,'0');
const row=(n,extra={})=>({task_id:id(n),project_id:projectId,
  created_at:'2026-10-25T01:00:00Z',updated_at:'2026-10-25T01:01:00Z',...extra});
function signed(claims={}) {
  const body=Buffer.from(JSON.stringify({kind:'access',aud:'mcp',scope:'task.read',
    task_project:projectId,exp:Math.floor(Date.now()/1000)+60,...claims})).toString('base64url');
  return body+'.'+createHmac('sha256','fixture-signing-key').update(body).digest('base64url');
}
async function call(env,token,name,args={},method='tools/call') {
  const response=await (await loaded).default.fetch(new Request('https://fixture.invalid/mcp',{
    method:'POST',headers:token?{Authorization:'Bearer '+token}:{},
    body:JSON.stringify({jsonrpc:'2.0',id:1,method,params:{name,arguments:args}})}),env);
  return {http:response.status,body:await response.json()};
}
async function catalog(options={}) {
  const records=options.records??[row(1)];
  const entries=new Map(records.map(r=>[r.task_id,r]));
  const listCalls=[],getCalls=[],forbidden=[];
  const deny=what=>{forbidden.push(what);throw Error('private-fixture-secret');};
  const env={OAUTH_SIGNING_KEY:'fixture-signing-key',MCP_AUTH_TOKEN:'fixture-owner-token',
    TASK_REGISTRY:{
      async list(args) {
        listCalls.push(args);
        if(options.listError)throw Error('private-fixture-secret');
        if(options.page)return options.page;
        const offset=args.cursor?Number(args.cursor.slice(2)):0;
        const slice=records.slice(offset,offset+args.limit),end=offset+slice.length;
        return {keys:slice.map(r=>({name:'task:'+r.task_id,metadata:{task_id:r.task_id,
          project_id:r.project_id??null,parent_task_id:r.parent_task_id??null,root_task_id:r.root_task_id??null}})),
          list_complete:end>=records.length,cursor:'p:'+end};
      },
      async get(key,type) {
        getCalls.push(key);assert.equal(type,'json');
        if(options.getError)throw Error('private-fixture-secret');
        return entries.get(key.slice(5))??null;
      },
      put:()=>deny('put'),delete:()=>deny('delete')},
    get ASSET_DB(){return deny('D1');}};
  const previous=global.fetch;global.fetch=()=>deny('network');
  try {
    const token=options.static?'fixture-owner-token':options.noAuth?null:signed(options.claims);
    const result=await call(env,token,'list_registered_tasks',Object.hasOwn(options,'args')?options.args:{},options.method);
    assert.deepEqual(forbidden,[],'catch blocks must not hide forbidden operations');
    assert.ok(!JSON.stringify(result).includes('private-fixture-secret'));
    return {...result,report:result.body.result?.structuredContent,listCalls,getCalls};
  } finally {global.fetch=previous;}
}

test('catalog paginates source keys with bounded limit and keeps new/reviewed registrations',async()=>{
  const records=[row(1,{status:'PENDING'}),row(2,{reviewed:true,status:'PASS'}),row(3,{status:'running'})];
  const first=await catalog({records,args:{limit:2}});
  assert.deepEqual(first.listCalls,[{prefix:'task:',limit:2}]);
  assert.deepEqual(first.report.tasks.map(r=>r.task_id),[id(1),id(2)]);
  assert.equal(first.report.pagination.limit,2);assert.equal(first.report.pagination.limit_applies_to,'registry_keys');
  assert.equal(first.report.pagination.has_more,true);assert.match(first.report.pagination.next_cursor,/^tc1\./);
  const second=await catalog({records,args:{limit:2,cursor:first.report.pagination.next_cursor}});
  assert.deepEqual(second.listCalls,[{prefix:'task:',limit:2,cursor:'p:2'}]);
  assert.deepEqual(second.report.tasks.map(r=>r.task_id),[id(3)]);
  assert.equal(second.report.pagination.has_more,false);assert.equal(second.report.pagination.next_cursor,null);
  for(const r of [...first.report.tasks,...second.report.tasks]) {
    assert.equal(r.registration_state,'registered');assert.equal(r.runtime_state,'unknown');assert.equal(r.agent_state,'unknown');
    assert.deepEqual(r.execution_identity,{state:'unknown',employee_id:null,agent_id:null,
      configured:null,observed:null,receipt_identity_verified:false,reason:'trusted_agent_identity_unavailable'});
  }
  assert.equal(second.report.full_task_coverage,false);assert.equal(second.report.consistency,'eventual');
});

test('catalog permits empty filtered pages with continuation; cross-page ancestor is verified',async()=>{
  const records=[row(1,{project_id:'other-project'}),row(2,{project_id:null,parent_task_id:id(3)}),row(3)];
  const first=await catalog({records,args:{limit:1}});
  assert.deepEqual(first.report.tasks,[]);assert.equal(first.report.pagination.has_more,true);
  const second=await catalog({records,args:{limit:1,cursor:first.report.pagination.next_cursor}});
  assert.equal(second.report.tasks[0].project_id,projectId);
  assert.deepEqual(second.getCalls,['task:'+id(2),'task:'+id(3)]);
});

test('catalog uses default 50, accepts max 100, and empty registry is not full platform idle',async()=>{
  assert.equal((await catalog()).listCalls[0].limit,50);
  assert.equal((await catalog({args:{limit:100}})).listCalls[0].limit,100);
  const empty=await catalog({records:[]});assert.deepEqual(empty.report.tasks,[]);
  assert.equal(empty.report.pagination.has_more,false);assert.equal(empty.report.full_task_coverage,false);
});

test('catalog does not expose prompts, notes, accounts, model/employee claims or raw status',async()=>{
  const secret='private-fixture-secret';
  const malicious=row(1,{goal:secret,instructions:[secret],review_note:secret,account:secret,
    status:'success',execution_status:'PASS',workflow_conclusion:'success',employee_id:'Codex',agent_id:'Grok',
    execution_identity:{state:'verified',employee_id:'Codex',configured:{model:'grok'},observed:{session_id:secret}},
    dispatch_contract:{task_id:id(1),project_id:projectId,goal:secret,instructions:[secret]}});
  const r=await catalog({records:[malicious]});
  const task=r.report.tasks[0];
  assert.deepEqual(Object.keys(task).sort(),['task_id','project_id','parent_task_id','root_task_id',
    'registration_state','created_at','registry_updated_at','runtime_state','agent_state','execution_identity'].sort());
  assert.ok(!JSON.stringify(r.body).includes('Codex'));assert.ok(!JSON.stringify(r.body).includes('Grok'));
  assert.equal(task.execution_identity.configured,null);assert.equal(task.execution_identity.observed,null);
});

test('catalog rejects invalid arguments before storage access',async()=>{
  for(const args of [{limit:0},{limit:101},{limit:1.5},{limit:'2'},{limit:null},
    {cursor:''},{cursor:'a\nb'},{cursor:'a'.repeat(8193)},{project_id:'other'},
    {prompt:'private-fixture-secret'},[],null]) {
    const r=await catalog({args});
    assert.equal(r.body.result.isError,true);assert.equal(r.body.result.content[0].text,'TASK_CATALOG_ARGUMENTS_REJECTED');
    assert.deepEqual(r.listCalls,[]);assert.deepEqual(r.getCalls,[]);
  }
});

test('catalog permission gates reject unauthenticated, asset-only and invalid task claims before KV',async()=>{
  const cases=[{noAuth:true},{claims:{scope:'asset.read'}},{claims:{scope:'task.read',task_project:'other'}},
    {claims:{scope:'task.read',aud:'other'}},{claims:{exp:1}},{claims:{exp:null}},
    {claims:{scope:'mcp',aud:'other'}},{claims:{scope:'mcp',exp:null}},
    {claims:{scope:'mcp',kind:'refresh'}}];
  for(const options of cases) {
    const r=await catalog(options);assert.ok(r.http===401||r.body.error?.code===-32002);
    assert.deepEqual(r.listCalls,[]);assert.deepEqual(r.getCalls,[]);
  }
  assert.equal((await catalog({static:true})).body.result.isError,false);
  assert.equal((await catalog({claims:{scope:'mcp'}})).body.result.isError,false);
});

test('catalog discovery is read-only and does not grant observer or write scope to task.read',async()=>{
  for(const claims of [{scope:'task.read'},{scope:'mcp'}]) {
    const r=await catalog({claims,method:'tools/list'});
    const tool=r.body.result.tools.find(t=>t.name==='list_registered_tasks');
    assert.equal(tool.annotations.readOnlyHint,true);assert.equal(tool.inputSchema.properties.limit.maximum,100);
    assert.deepEqual(r.listCalls,[]);
  }
  const r=await catalog({claims:{scope:'asset.read'},method:'tools/list'});
  assert.ok(!r.body.result.tools.some(t=>t.name==='list_registered_tasks'));
});

test('catalog fails closed for incomplete/malformed pages and source failure, without partial tasks',async()=>{
  const key={name:'task:'+id(1)};
  const cursor=await sealed('p:1');
  for(const page of [{keys:[],list_complete:false},{keys:[],list_complete:false,cursor:'p:1'},
    {keys:[key,key],list_complete:true},{keys:[key],list_complete:'true'},
    {keys:[{name:'other:'+id(1)}],list_complete:true},
    {keys:[{name:'task:../../secret'}],list_complete:true},
    {keys:[key,{name:'task:'+id(2)}],list_complete:true}]) {
    const r=await catalog({page,args:{limit:1,cursor}});
    assert.equal(r.body.result.isError,true);assert.equal(r.report,undefined);
  }
  for(const options of [{listError:true},{getError:true}]) {
    const r=await catalog(options);assert.equal(r.body.result.content[0].text,'TASK_CATALOG_SOURCE_FAILED');
  }
  // KV can legitimately return an empty nonterminal page (for example expirations).
  const empty=await catalog({page:{keys:[],list_complete:false,cursor:'p:2'},args:{cursor}});
  assert.deepEqual(empty.report.tasks,[]);assert.equal(empty.report.pagination.has_more,true);
});

test('cursor confidentiality fix hides source metadata and round-trips only through authenticated encryption',async()=>{
  const raw=Buffer.from(JSON.stringify({last_key:'task:'+id(2),project:'foreign-private-project'})).toString('base64url');
  const first=await catalog({page:{keys:[{name:'task:'+id(1)}],list_complete:false,cursor:raw}});
  const token=first.report.pagination.next_cursor;
  assert.match(token,/^tc1\.[A-Za-z0-9_-]{16}\.[A-Za-z0-9_-]+$/);
  assert.ok(!JSON.stringify(first.body).includes(raw));assert.ok(!JSON.stringify(first.body).includes('foreign-private-project'));
  assert.ok(!Buffer.from(token.split('.')[2],'base64url').includes(Buffer.from('foreign-private-project')));
  const next=await catalog({page:{keys:[],list_complete:true},args:{cursor:token}});
  assert.equal(next.listCalls[0].cursor,raw);assert.equal(next.report.pagination.has_more,false);
  // Existing static-only deployments can use their existing owner token as key material.
  const ownerEnv={MCP_AUTH_TOKEN:'fixture-owner-token'};
  const ownerToken=await (await cursorAPI).sealTaskCatalogCursor(ownerEnv,raw);
  assert.match(ownerToken,/^tc1\./);
});

test('cursor confidentiality fix rejects raw, tampered, expired and foreign-context tokens before any KV read',async()=>{
  const valid=await sealed('p:1');
  const tampered=valid.slice(0,22)+(valid[22]==='A'?'B':'A')+valid.slice(23);
  const wrongKey=await (await cursorAPI).sealTaskCatalogCursor({OAUTH_SIGNING_KEY:'another-existing-fixture-key'},'p:1');
  const previousNow=Date.now;let expired;
  try {Date.now=()=>0;expired=await sealed('p:1');} finally {Date.now=previousNow;}
  const context='registered-task-catalog:v1:task::cloud-assets-activation';
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(context+'\0fixture-signing-key'));
  const key=await crypto.subtle.importKey('raw',digest,{name:'AES-GCM'},false,['encrypt']);
  async function crafted(payload,aad=context) {
    const iv=crypto.getRandomValues(new Uint8Array(12));
    const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:new TextEncoder().encode(aad)},key,
      new TextEncoder().encode(JSON.stringify(payload)));
    return 'tc1.'+Buffer.from(iv).toString('base64url')+'.'+Buffer.from(encrypted).toString('base64url');
  }
  const claims={v:1,project:projectId,cursor:'p:1',exp:Math.floor(Date.now()/1000)+900};
  const wrongProject=await crafted({...claims,project:'foreign-private-project'});
  const wrongContext=await crafted(claims,'another-namespace');
  for(const cursor of ['p:1',tampered,expired,wrongKey,wrongProject,wrongContext]) {
    const r=await catalog({args:{cursor}});assert.equal(r.body.result.content[0].text,'TASK_CATALOG_ARGUMENTS_REJECTED');
    assert.deepEqual(r.listCalls,[]);assert.deepEqual(r.getCalls,[]);
  }
});

test('cursor confidentiality fix round-trips maximum escaped source cursors within advertised schema bounds',async()=>{
  const discovery=await catalog({method:'tools/list'});
  const schema=discovery.body.result.tools.find(t=>t.name==='list_registered_tasks').inputSchema.properties.cursor;
  for(const raw of ['a'.repeat(2048),'\\'.repeat(2048),'"'.repeat(2048)]) {
    const first=await catalog({page:{keys:[],list_complete:false,cursor:raw}});
    const token=first.report.pagination.next_cursor;
    assert.ok(token.length<=schema.maxLength);assert.match(token,new RegExp(schema.pattern));
    const second=await catalog({page:{keys:[],list_complete:true},args:{cursor:token}});
    assert.equal(second.listCalls[0].cursor,raw);assert.equal(second.body.result.isError,false);
  }
});

test('catalog verifies body, metadata, contracts and all declared ancestors; bounded metadata can fall back',async()=>{
  const cases=[
    {records:[row(1,{parent_task_id:id(2)})]},
    {records:[row(1,{parent_task_id:id(2)}),row(2,{parent_task_id:id(1)})]},
    {records:[row(1,{parent_task_id:id(2)}),row(2,{project_id:'other'})]},
    {records:[row(1,{dispatch_contract:{task_id:id(2),project_id:projectId}})]},
    {page:{keys:[{name:'task:'+id(1),metadata:{project_id:'other'}}],list_complete:true}},
    {page:{keys:[{name:'task:'+id(1),metadata:{task_id:id(2),project_id:projectId}}],list_complete:true}},
    {page:{keys:[{name:'task:'+id(1),metadata:'private-fixture-secret'}],list_complete:true}}
  ];
  for(const options of cases) assert.equal((await catalog(options)).body.result.isError,true);
  const fallback=await catalog({page:{keys:[{name:'task:'+id(1),metadata:{project_id:'truncated',metadata_bounded:true}}],list_complete:true}});
  assert.equal(fallback.report.tasks[0].project_id,projectId);
});

test('catalog caps ancestor depth and per-request reads instead of scanning unbounded lineage',async()=>{
  const deep=Array.from({length:65},(_,i)=>row(i+1,i===64?{}:{parent_task_id:id(i+2)}));
  const r=await catalog({records:deep,args:{limit:1}});assert.equal(r.body.result.isError,true);
  assert.ok(r.getCalls.length<=64);
  const records=[];
  for(let i=1;i<=100;i++)records.push(row(i,{parent_task_id:id(100+i)}));
  for(let i=101;i<=200;i++)records.push(row(i,{parent_task_id:id(200+i)}));
  for(let i=301;i<=400;i++)records.push(row(i));
  const capped=await catalog({records,args:{limit:100}});assert.equal(capped.body.result.isError,true);
  assert.equal(capped.getCalls.length,200);
});

async function observe(options={}) {
  const taskId=id(1),run={id:123,run_number:10,run_attempt:2,
    repository:{full_name:'fixture/repo'},display_title:'personal-ai-task:'+taskId,
    event:'repository_dispatch',path:'.github/workflows/agent-dispatch.yml',
    head_sha:'a'.repeat(40),created_at:'2026-10-25T01:00:01Z',
    updated_at:'2026-10-25T01:00:02Z',status:'in_progress',conclusion:null,
    actor:{login:'Codex'},model:'Grok',employee_id:'Codex',...options.run};
  const attempted=[];
  const deny=what=>{attempted.push(what);throw Error('forbidden');};
  const env={MCP_AUTH_TOKEN:'fixture-owner-token',GITHUB_TOKEN:'synthetic',GITHUB_REPO:'fixture/repo',
    TASK_REGISTRY:{get:async()=>row(1,{dispatch_attempt:1,employee_id:'Codex',
      execution_identity:{employee_id:'Grok',model:'Codex'}}),
      put:()=>deny('put'),delete:()=>deny('delete'),list:()=>deny('list')},
    get ASSET_DB(){return deny('D1');}};
  const previous=global.fetch,calls=[];
  global.fetch=async(url,init)=>{
    calls.push(url);assert.equal(init.method,'GET');assert.equal(init.redirect,'manual');
    if(url.includes('/actions/workflows/'))return new Response(JSON.stringify({total_count:1,workflow_runs:[run]}));
    assert.equal(url,'https://api.github.com/repos/fixture/repo/actions/runs/123');
    return new Response(JSON.stringify({...run,...options.detail}));
  };
  try {
    const r=await call(env,'fixture-owner-token','get_task_execution_status',{task_id:taskId});
    assert.deepEqual(attempted,[]);assert.equal(calls.length,2);return r.body.result.structuredContent;
  } finally {global.fetch=previous;}
}

test('observer adds verified workflow provenance without claiming configured model, employee or receipt identity',async()=>{
  const r=await observe();assert.equal(r.executor.state,'running');assert.equal(r.agent_state,'unknown');
  assert.deepEqual(r.execution_identity,{state:'unknown',employee_id:null,agent_id:null,
    configured:null,receipt_identity_verified:false,reason:'trusted_agent_identity_unavailable',
    observed:{source:'github_actions_run_api',executor_kind:'github_actions_workflow_run',
      repository:'fixture/repo',run_id:123,run_attempt:2,
      workflow_path:'.github/workflows/agent-dispatch.yml',run_head_sha:'a'.repeat(40)}});
  assert.equal(r.business.state,'unknown');assert.equal(r.acceptance.state,'unknown');
  assert.equal(r.ttl_seconds,60);assert.ok(!JSON.stringify(r).includes('Codex'));assert.ok(!JSON.stringify(r).includes('Grok'));
  const missing=await observe({run:{head_sha:'private-fixture-secret'}});
  assert.equal(missing.execution_identity.observed.run_head_sha,null);
});

test('observer never publishes observed identity from a mismatched/invalid run',async()=>{
  for(const detail of [{repository:{full_name:'other/repo'}},{run_attempt:1},{status:'unexpected'},
    {display_title:'personal-ai-task:'+id(2)}]) {
    const r=await observe({detail});assert.equal(r.executor.state,'unknown');
    assert.equal(r.execution_identity.observed,null);assert.equal(r.execution_identity.configured,null);
  }
});
