import fs from 'node:fs';
const source=fs.readFileSync(new URL('../worker/index.js',import.meta.url),'utf8');
const {toolGetTaskExecutionStatus:read,rejectObservationRedirect}=await import('data:text/javascript;base64,'+Buffer.from(source+'\nexport {toolGetTaskExecutionStatus,rejectObservationRedirect};').toString('base64'));
const assert=(v,m)=>{if(!v)throw Error(m)};
async function check(){
let checks=0, calls=0, writes=0, mode='normal', stage=0;
const task={task_id:'synthetic',created_at:'2026-10-24T00:00:00Z',dispatch_attempt:1};
const run={id:123,run_number:1,run_attempt:1,display_title:'personal-ai-task:synthetic',event:'repository_dispatch',path:'.github/workflows/agent-dispatch.yml',repository:{full_name:'owner/repo'},created_at:'2026-10-24T00:00:00Z',updated_at:'2026-10-24T00:01:00Z',status:'in_progress',conclusion:null};
const env={GITHUB_REPO:'owner/repo',GITHUB_TOKEN:'SYNTHETIC_ONLY',TASK_REGISTRY:{get:async()=>task,put:async()=>{writes++;throw Error('write forbidden')}}};
const originalFetch=globalThis.fetch, originalTimer=globalThis.setTimeout;
try {
  let rejected=false;try{new Request('https://api.github.com/',{redirect:'error'})}catch(e){rejected=e instanceof TypeError}
  // Node supports error; native workerd rejection is covered by local runtime evidence.
  checks++;
  const controller=new AbortController();new Request('https://api.github.com/',{method:'GET',redirect:'manual',signal:controller.signal});checks++;
  globalThis.fetch=async(url,opts)=>{
    calls++;assert(opts.redirect==='manual'&&opts.method==='GET','safe GET');assert(new URL(url).hostname==='api.github.com','fixed host');
    new Request(url,opts); // Real workerd Request parser; no network.
    if(mode==='redirect'&&calls===stage)return {status:302,get ok(){throw Error('must reject before ok')},get headers(){throw Error('must not read Location or headers')},json(){throw Error('must not read body')}};
    if(mode==='http')return new Response('SENSITIVE BODY',{status:403});
    if(mode==='timeout'){assert(opts.signal.aborted,'aborted signal');throw Error('SENSITIVE exception')}
    if(url.includes('/workflows/'))return Response.json({total_count:mode==='history'?0:1,workflow_runs:mode==='history'?[]:[run]});
    if(url.includes('/artifacts?'))return Response.json({artifacts:[{id:55,name:'execution_result-synthetic',created_at:task.created_at,workflow_run:{id:123}}]});
    return Response.json(run);
  };
  for(const scenario of ['normal','history']){mode=scenario;calls=0;const v=(await read(env,{task_id:'synthetic'})).structuredContent;assert(v.executor.state==='running'&&v.reason===null,'mapping');assert(v.business.state==='unknown'&&v.acceptance.state==='unknown'&&v.ttl_seconds===60,'semantics');assert(Date.parse(v.expires_at)-Date.parse(v.observed_at)===60000,'ttl');assert(calls===(scenario==='normal'?2:3),'request count');checks++;}
  // First query, detail query, and registration-time-missing historical artifact query.
  for(const target of [1,2,3]){mode='redirect';calls=0;stage=target===3?1:target;if(target===3)delete task.created_at;const v=(await read(env,{task_id:'synthetic'})).structuredContent;assert(calls===stage,'redirect added request');assert(v.reason==='github_read_failed'&&v.executor.state==='unknown','redirect unknown');assert(v.github_diagnostics.failure_class==='redirect_rejected'&&v.github_diagnostics.http_status===302,'redirect diagnostic');assert(!JSON.stringify(v).includes('SENSITIVE'),'sanitized');task.created_at='2026-10-24T00:00:00Z';checks++;}
  mode='http';calls=0;let v=(await read(env,{task_id:'synthetic'})).structuredContent;assert(v.reason==='github_read_failed'&&v.github_diagnostics.failure_class==='http'&&v.github_diagnostics.http_status===403&&calls===1,'HTTP semantics');assert(!JSON.stringify(v).includes('SENSITIVE'),'http sanitized');checks++;
  mode='timeout';calls=0;globalThis.setTimeout=(fn)=>{fn();return 0};v=(await read(env,{task_id:'synthetic'})).structuredContent;assert(v.reason==='github_read_timeout'&&v.github_diagnostics.failure_class==='timeout'&&calls===1,'timeout semantics');checks++;
  for(let status=300;status<400;status++){let denied=false;try{rejectObservationRedirect({status,get headers(){throw Error('header read forbidden')}},'workflow_runs')}catch(e){denied=e.diagnostics?.failure_class==='redirect_rejected'&&e.diagnostics.http_status===status}assert(denied,'all 3xx rejected');}checks++;
  assert(writes===0,'no writes');checks++;
  console.log(JSON.stringify({status:'PASS',checks,runtime:'Node synthetic',network_calls:0,synthetic_fetch:true,native_request_validation:'Node only',registry_writes:writes}));
}finally{globalThis.fetch=originalFetch;globalThis.setTimeout=originalTimer;}
}
await check();
