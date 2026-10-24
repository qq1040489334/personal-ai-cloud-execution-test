// Synthetic new behavior only: no network, credentials, task dispatch or production workflow.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'worker/index.js'), 'utf8');
const loaded = import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const taskId = 'cf-early-synthetic';
const fixture = {id:123, run_number:100, run_attempt:1,
  display_title:`personal-ai-task:${taskId}`, event:'repository_dispatch',
  path:'.github/workflows/agent-dispatch.yml', repository:{full_name:'fixture/repo'},
  created_at:'2026-10-23T12:00:01Z', updated_at:'2026-10-23T12:00:02Z',
  status:'queued', conclusion:null};
async function read(options={}) {
  const writes = [], calls = [];
  const forbidden = name => { writes.push(name); throw Error('forbidden'); };
  const env = {MCP_AUTH_TOKEN:'synthetic', GITHUB_TOKEN:'synthetic', GITHUB_REPO:'fixture/repo',
    TASK_REGISTRY:{
      get:async key => { assert.equal(key,'task:'+taskId); return {task_id:taskId,
        created_at:'2026-10-23T12:00:00.123Z',dispatch_attempt:1,...options.task}; },
      put:()=>forbidden('put'), delete:()=>forbidden('delete'), list:()=>forbidden('list')},
    get ASSET_DB(){return forbidden('D1');}};
  const previous = global.fetch;
  global.fetch = async (url, init) => {
    calls.push({url,method:init.method,redirect:init.redirect});
    if (options.error) return new Response('synthetic private error body',{status:403});
    if (url.includes('/actions/workflows/')) {
      const rows = options.rows || [{...fixture,...options.run}];
      return new Response(JSON.stringify({total_count: options.total ?? rows.length,workflow_runs:rows}));
    }
    if (url.includes('/actions/artifacts?')) return new Response(JSON.stringify({artifacts:[]}));
    return new Response(JSON.stringify({...fixture,...options.run,...options.detail}));
  };
  try {
    const worker=(await loaded).default;
    const response=await worker.fetch(new Request('https://worker.invalid/mcp',{
      method:'POST',headers:{Authorization:'Bearer synthetic'},body:JSON.stringify({jsonrpc:'2.0',id:1,
        method:'tools/call',params:{name:'get_task_execution_status',arguments:{task_id:taskId}}})}),env);
    const body=await response.json();
    assert.deepEqual(writes,[]);
    assert.ok(calls.length<=3);
    for(const call of calls){
      assert.equal(call.method,'GET');assert.equal(call.redirect,'error');
      const url=new URL(call.url);
      assert.equal(url.origin,'https://api.github.com');
      assert.ok(['/repos/fixture/repo/actions/workflows/agent-dispatch.yml/runs',
        '/repos/fixture/repo/actions/artifacts','/repos/fixture/repo/actions/runs/123'].includes(url.pathname));
    }
    assert.ok(!JSON.stringify(body).includes('synthetic private'));
    return {result:body.result.structuredContent,calls};
  } finally {global.fetch=previous;}
}
for(const [status,state] of [['queued','queued'],['in_progress','running']]){
  test('early: '+status+' is visible with no artifact',async()=>{
    const {result:r,calls}=await read({run:{status}});
    assert.equal(r.executor.state,state);assert.equal(r.executor.run_id,123);assert.equal(r.executor.run_attempt,1);
    assert.equal(r.mapping.kind,'workflow_run_name');assert.equal(r.mapping.run_number,100);
    assert.equal(r.mapping.artifact_id,null);assert.equal(calls.length,2);
    assert.equal(new URL(calls[0].url).searchParams.get('created'),'>=2026-10-23T11:45:00.000Z');
    assert.equal(r.agent_state,'unknown');assert.equal(r.business.state,'unknown');
  });
}
test('early: before GitHub publishes a run remains unknown',async()=>{
  const {result:r}=await read({rows:[]});
  assert.equal(r.executor.state,'unknown');assert.equal(r.reason,'task_run_mapping_unavailable');
  assert.equal(r.mapping.coverage,'no_named_run_visible');
});
test('early: different task title cannot bind',async()=>{
  const {result:r}=await read({rows:[{...fixture,display_title:'personal-ai-task:someone-else'}]});
  assert.equal(r.executor.state,'unknown');assert.equal(r.mapping.run_id,null);
});
for(const patch of [{event:'push'},{path:'.github/workflows/other.yml'},
    {repository:{full_name:'other/repo'}},{run_number:null},{run_attempt:null},
    {created_at:'2026-10-22T12:00:00Z'}]){
  test('early: reject invalid source identity '+JSON.stringify(patch),async()=>{
    const {result:r}=await read({run:patch});
    assert.equal(r.reason,'invalid_early_run_identity');assert.equal(r.executor.state,'unknown');
  });
}
test('early: duplicate observations are idempotent and latest attempt comes from detail GET',async()=>{
  const {result:r}=await read({rows:[fixture,fixture],detail:{run_attempt:2,status:'in_progress'}});
  assert.equal(r.executor.run_attempt,2);assert.equal(r.executor.state,'running');
});
test('early: an older detail attempt cannot replace a newer listed attempt',async()=>{
  const {result:r}=await read({run:{run_attempt:2},detail:{run_attempt:1}});
  assert.equal(r.reason,'early_run_changed_or_regressed');assert.equal(r.executor.state,'unknown');
});
test('early: late old-run rerun cannot override a newer dispatch',async()=>{
  const old={...fixture,id:99,run_number:99,run_attempt:8,updated_at:'2026-12-01T00:00:00Z'};
  const {result:r}=await read({rows:[old,fixture]});
  assert.equal(r.executor.run_id,123);assert.equal(r.executor.run_attempt,1);
});
test('early: incomplete page refuses to select a possibly obsolete run',async()=>{
  const {result:r,calls}=await read({total:101});
  assert.equal(r.reason,'run_lookup_incomplete');assert.equal(calls.length,1);
});
test('early: accepted retry without its new run is unknown',async()=>{
  const {result:r}=await read({task:{dispatch_attempt:2,dispatch_accepted_at:'2026-10-23T12:10:00Z'}});
  assert.equal(r.reason,'latest_dispatch_not_visible');assert.equal(r.executor.state,'unknown');
});
test('early: malformed/missing source fields and HTTP errors do not fall back to older success',async()=>{
  const {result:r}=await read({error:true});assert.equal(r.reason,'github_read_failed');
  assert.equal(r.executor.state,'unknown');
});
test('early: workflow only adds run-name; permissions, Gates and execution stay byte-identical',()=>{
  const baseline=fs.readFileSync(path.join(__dirname,'fixtures/r5-agent-dispatch-baseline.yml'),'utf8');
  assert.equal(require('node:crypto').createHash('sha256').update(baseline).digest('hex'),'db5aa946e888a6a5ab251bef8f31b5f8048e805076eb0d73cbe20a2dc52cbbe7');
  const workflow=fs.readFileSync(path.join(root,'.github/workflows/agent-dispatch.yml'),'utf8');
  const addition='# Exact task identity is visible in GitHub metadata before any job/artifact exists.\nrun-name: personal-ai-task:${{ github.event.client_payload.task.task_id }}\n';
  assert.ok(workflow.includes(addition));assert.equal(workflow.replace(addition,''),baseline);
});

test('repair: post-dispatch child registration still discovers its own earlier run',async()=>{
  const {result:r,calls}=await read({task:{created_at:'2026-10-23T12:00:02Z'},run:{created_at:'2026-10-23T12:00:00Z',status:'in_progress'}});
  assert.equal(new URL(calls[0].url).searchParams.get('created'),'>=2026-10-23T11:45:02.000Z');
  assert.equal(r.mapping.kind,'workflow_run_name');assert.equal(r.executor.run_id,123);
  assert.equal(r.executor.state,'running');
});
test('repair: lookback never accepts a run outside the declared window',async()=>{
  const {result:r}=await read({task:{created_at:'2026-10-23T12:00:02Z'},run:{created_at:'2026-10-23T11:45:01Z'}});
  assert.equal(r.reason,'invalid_early_run_identity');assert.equal(r.executor.state,'unknown');
});
