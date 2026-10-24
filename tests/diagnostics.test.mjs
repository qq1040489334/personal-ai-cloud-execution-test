// Synthetic only. No real network, credentials, registry writes or timers.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const source=fs.readFileSync(new URL('../worker/index.js',import.meta.url),'utf8');
const baseline=execFileSync('git',['show','ff84f630bcd9305468c5ee02b2063db094f2b77a'],{cwd:fileURLToPath(new URL('..',import.meta.url)),encoding:'utf8'});
assert.equal(createHash('sha256').update(baseline).digest('hex'),'34690cf4f8d1a941ebf3c6839c0695ee3988ba928d578d8a24001dc3a9514467');
const load=s=>import('data:text/javascript;base64,'+Buffer.from(s+'\nexport {toolGetTaskExecutionStatus};').toString('base64'));
const api=await load(source),old=await load(baseline);
const task={task_id:'cf-fixture',created_at:'2026-10-23T12:00:00Z',dispatch_attempt:1};
const secret='PRIVATE_TOKEN_DO_NOT_OUTPUT';
const run={id:123,run_number:2,run_attempt:1,event:'repository_dispatch',path:'.github/workflows/agent-dispatch.yml',repository:{full_name:'fixture/repo'},display_title:'personal-ai-task:cf-fixture',created_at:task.created_at,updated_at:task.created_at,run_started_at:task.created_at,status:'completed',conclusion:'success'};
async function invoke(reply,implementation=api){
 const saved={fetch:globalThis.fetch,setTimeout:globalThis.setTimeout,clearTimeout:globalThis.clearTimeout};
 let abort;const calls=[];let writes=0;
 const deny=()=>{writes++;throw Error(secret)};
 globalThis.setTimeout=fn=>{abort=fn;return 1};globalThis.clearTimeout=()=>{};
 globalThis.fetch=async(url,init)=>{calls.push({url,method:init.method,redirect:init.redirect,headers:init.headers});return reply(calls.length,abort,init)};
 try{
 const result=await implementation.toolGetTaskExecutionStatus({GITHUB_REPO:'fixture/repo',GITHUB_TOKEN:secret,TASK_REGISTRY:{get:async()=>task,put:deny,delete:deny,list:deny},get ASSET_DB(){return deny()}},{task_id:task.task_id});
 assert.equal(writes,0);assert.ok(!JSON.stringify(result).includes(secret));
 assert.ok(calls.every(x=>x.method==='GET'&&x.redirect===(implementation===api?'manual':'error')));
 return {r:result.structuredContent,calls};
 }finally{Object.assign(globalThis,saved)}
}
function check(r,kind,status=null){
 assert.equal(r.executor.state,'unknown');assert.equal(r.mapping.kind,'unknown');assert.equal(r.agent_state,'unknown');assert.equal(r.business.state,'unknown');assert.equal(r.acceptance.state,'unknown');
 assert.equal(r.reason,kind==='timeout'?'github_read_timeout':'github_read_failed');assert.equal(r.ttl_seconds,60);assert.equal(Date.parse(r.expires_at)-Date.parse(r.observed_at),60000);
 assert.deepEqual(Object.keys(r.github_diagnostics).sort(),['stage','failure_class','http_status','github_request_id','rate_limit_remaining'].sort());
 assert.equal(r.github_diagnostics.stage,'workflow_runs');assert.equal(r.github_diagnostics.failure_class,kind);assert.equal(r.github_diagnostics.http_status,status);
}
for(const status of [401,403,404,429])test('HTTP '+status+' is classified without reading body',async()=>{
 const {r,calls}=await invoke(()=>({ok:false,status,headers:new Headers({'x-github-request-id':'A1:B2:C3','x-ratelimit-remaining':'0',Authorization:secret,location:'https://'+secret}),json(){throw Error('body must not be read')},text(){throw Error('body must not be read')}}));
 check(r,'http',status);assert.equal(calls.length,1);assert.equal(r.github_diagnostics.github_request_id,'A1:B2:C3');assert.equal(r.github_diagnostics.rate_limit_remaining,0);
});
for(const label of ['network','redirect'])test(label+' exception does not leak',async()=>{const {r,calls}=await invoke(()=>{throw new TypeError(label+secret)});check(r,'network_or_redirect');assert.equal(calls.length,1)});
test('timeout uses abort classification',async()=>{const {r,calls}=await invoke((n,abort)=>{abort();throw Error(secret)});check(r,'timeout');assert.equal(calls.length,1)});
test('JSON failure',async()=>{const {r}=await invoke(()=>new Response(secret,{status:200}));check(r,'response_json',200)});
for(const payload of [null,[],true,42,'bad'])test('invalid JSON top-level '+JSON.stringify(payload),async()=>{const {r}=await invoke(()=>new Response(JSON.stringify(payload)));check(r,'response_shape',200)});
for(const value of [secret,'https://private.invalid',':'.repeat(129),'','ABC xyz'])test('request-id rejects '+value.slice(0,20),async()=>{const {r}=await invoke(()=>new Response(secret,{status:403,headers:{'x-github-request-id':value}}));assert.equal(r.github_diagnostics.github_request_id,null)});
for(const [value,expected] of [['0',0],['5000',5000],['01',1],['-1',null],['1.5',null],['1e3',null],['99999999999',null],['',null],[secret,null]])test('remaining validates '+value,async()=>{const {r}=await invoke(()=>new Response(secret,{status:429,headers:{'x-ratelimit-remaining':value}}));assert.equal(r.github_diagnostics.rate_limit_remaining,expected)});
const strip=r=>{const {observed_at,expires_at,...rest}=r;return rest};
for(const status of ['queued','in_progress','completed'])test('success unchanged '+status,async()=>{
 const row={...run,status,conclusion:status==='completed'?'success':null};const response=n=>new Response(JSON.stringify(n===1?{total_count:1,workflow_runs:[row]}:row));
 const a=await invoke(response),b=await invoke(response,old);assert.deepEqual(strip(a.r),strip(b.r));assert.deepEqual(a.calls,b.calls.map(call=>({...call,redirect:'manual'})));assert.equal(a.calls.length,2);assert.equal(a.r.github_diagnostics,undefined);
});
test('incomplete shape keeps existing reason',async()=>{const reply=()=>new Response('{}');const a=await invoke(reply),b=await invoke(reply,old);assert.deepEqual(strip(a.r),strip(b.r));assert.equal(a.r.reason,'run_lookup_incomplete');assert.equal(a.calls.length,1)});

test('timeout during body decode remains timeout',async()=>{const {r,calls}=await invoke((n,abort)=>({ok:true,status:200,headers:new Headers(),async json(){abort();throw Error(secret)}}));check(r,'timeout',200);assert.equal(calls.length,1)});
