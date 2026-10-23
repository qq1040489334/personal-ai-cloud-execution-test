// Synthetic local tests only. No credentials, production API or network access.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHmac } = require('node:crypto');
const source = fs.readFileSync(path.join(__dirname, '../worker/index.js'), 'utf8');
const loaded = import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const taskId = 'cf-synthetic-status';
const run = { repository: {full_name: 'fixture/repo'}, id: 123, run_attempt: 2, status: 'completed', conclusion: 'success',
  created_at: '2026-01-01T01:00:00Z', updated_at: '2026-01-01T01:10:00Z', run_started_at: '2026-01-01T01:01:00Z' };
const artifact = { id: 456, name: `execution_result-${taskId}`, workflow_run: { id: 123 } };
async function probe(options = {}) {
  const writes = [];
  const calls = [];
  const fetchAttempts = [];
  let registryReads = 0;
  const forbid = name => { writes.push(name); throw Error('forbidden ' + name); };
  const env = {
    MCP_AUTH_TOKEN: 'synthetic-only', OAUTH_SIGNING_KEY: 'synthetic-key',
    GITHUB_TOKEN: 'synthetic-only', GITHUB_REPO: options.repo || 'fixture/repo',
    TASK_REGISTRY: {
      get: async (key, type) => {
        registryReads++;
        assert.equal(key, 'task:' + taskId); assert.equal(type, 'json');
        if (options.registryError) throw Error('private failure');
        return options.missingTask ? null : { task_id: taskId, dispatch_attempt: 3, dispatch_accepted_at: '2026-01-01T00:00:00Z', execution_status: 'BLOCKED', review_verdict: 'PASS' };
      },
      put: () => forbid('KV.put'), delete: () => forbid('KV.delete'), list: () => forbid('KV.list')
    },
    get ASSET_DB() { return forbid('D1 access'); },
  };
  let token = 'synthetic-only';
  if (options.oauth) {
    const claims = {kind:'access', aud:'mcp', scope:'mcp', exp:Math.floor(Date.now()/1000)+60, ...options.oauth};
    const body = Buffer.from(JSON.stringify(claims)).toString('base64url');
    token = body + '.' + createHmac('sha256', env.OAUTH_SIGNING_KEY).update(body).digest('base64url');
  }
  let call = 0;
  const previousTimer = global.setTimeout;
  if (options.timeout) global.setTimeout = callback => { queueMicrotask(callback); return 0; };
  const previous = global.fetch;
  global.fetch = async (url, init) => {
    calls.push(url); fetchAttempts.push({url, method:init.method, redirect:init.redirect}); call++;
    assert.equal(init.method, 'GET'); assert.equal(init.redirect, 'error');
    assert.ok(init.signal instanceof AbortSignal);
    assert.equal(url, call === 1
      ? `https://api.github.com/repos/fixture/repo/actions/artifacts?name=execution_result-${taskId}`
      : 'https://api.github.com/repos/fixture/repo/actions/runs/123');
    assert.ok(call <= 2, 'no extra fetch/events/dispatch/artifact download');
    if (options.timeout && init.signal.aborted) throw Error('aborted');
    if (options.timeout) return new Promise((resolve, reject) => {
      init.signal.addEventListener('abort', () => reject(Error('aborted')), {once:true});
    });
    if (options.failAt === call) throw Error('synthetic secret must not escape');
    if (options.httpStatus) return new Response('{}', {status: options.httpStatus});
    return new Response(options.badJson ? '{' : JSON.stringify(call === 1
      ? {artifacts: options.noArtifact ? [] : [options.artifact || artifact]}
      : {...run, ...options.run}));
  };
  try {
    const worker = (await loaded).default;
    const response = await worker.fetch(new Request('https://worker.invalid/mcp', {
      method: 'POST', headers: options.unauthorized ? {} : {Authorization: 'Bearer ' + token},
      body: JSON.stringify({jsonrpc: '2.0', id: 1, method: options.method || 'tools/call', params: {
        name: 'get_task_execution_status', arguments: {task_id: options.invalid ? '../bad' : taskId}
      }})
    }), env);
    const body = await response.json();
    assert.deepEqual(writes, []);
    // Verify after the Worker returns: its catch blocks must not hide a forbidden call.
    assert.ok(fetchAttempts.length <= 2);
    for (const [i, attempt] of fetchAttempts.entries()) {
      assert.equal(attempt.method, 'GET'); assert.equal(attempt.redirect, 'error');
      assert.equal(attempt.url, i === 0
        ? `https://api.github.com/repos/fixture/repo/actions/artifacts?name=execution_result-${taskId}`
        : 'https://api.github.com/repos/fixture/repo/actions/runs/123');
    }
    assert.ok(!JSON.stringify(body).includes('synthetic secret'));
    return {response, body, calls, registryReads, result: body.result?.structuredContent};
  } finally { global.fetch = previous; global.setTimeout = previousTimer; }
}
test('registered MCP route is strictly read-only and preserves separate axes and source times', async () => {
  const {result: r, calls} = await probe();
  assert.equal(calls.length, 2);
  assert.equal(r.executor.state, 'completed'); assert.equal(r.executor.run_attempt, 2);
  assert.equal(r.registry.dispatch_attempt, 3); assert.equal(r.mapping.run_id, 123);
  assert.equal(r.executor.updated_at, run.updated_at); assert.equal(r.executor.completed_at, null);
  assert.notEqual(r.observed_at, r.executor.updated_at);
  assert.equal(Date.parse(r.expires_at) - Date.parse(r.observed_at), 60000);
  assert.equal(r.business.state, 'unknown'); assert.equal(r.acceptance.state, 'unknown');
  assert.equal(r.agent_state, 'unknown'); assert.equal(r.full_task_coverage, false);
});
for (const [label, options, reason] of [
  ['missing registration', {missingTask:true}, 'task_registration_unavailable'],
  ['KV failure', {registryError:true}, 'registry_read_failed'],
  ['no mapping', {noArtifact:true}, 'task_run_mapping_unavailable'],
  ['artifact identity', {artifact:{...artifact,name:'wrong'}}, 'invalid_task_run_mapping'],
  ['run identity', {run:{id:999}}, 'run_identity_mismatch'],
  ['missing attempt', {run:{run_attempt:null}}, 'incomplete_source_fields'],
  ['unknown status', {run:{status:'new-status'}}, 'incomplete_source_fields'],
  ['missing conclusion', {run:{conclusion:null}}, 'incomplete_source_fields'],
  ['conflicting source', {run:{status:'in_progress'}}, 'inconsistent_source_fields'],
  ['artifact network failure', {failAt:1}, 'github_read_failed'],
  ['run network failure', {failAt:2}, 'github_read_failed'],
  ['bounded timeout', {timeout:true}, 'github_read_timeout'],
  ['403', {httpStatus:403}, 'github_read_failed'],
  ['429', {httpStatus:429}, 'github_read_failed'],
  ['malformed JSON', {badJson:true}, 'github_read_failed'],
]) test(label + ' degrades honestly without writes', async () => {
  const {result:r} = await probe(options);
  assert.equal(r.reason, reason); assert.equal(r.executor.state, 'unknown');
});
for (const [status,state] of [['in_progress','running'],['queued','queued'],['waiting','queued']]) {
  test(status + ' is scoped only to mapped run', async () => {
    const {result:r} = await probe({run:{status,conclusion:null}});
    assert.equal(r.executor.state,state); assert.equal(r.agent_state,'unknown');
  });
}
test('missing/invalid source timestamps are null, never observation substitutes', async () => {
  const {result:r} = await probe({run:{created_at:null,updated_at:'bad',run_started_at:null}});
  assert.equal(r.executor.updated_at,null); assert.equal(r.executor.created_at,null);
  assert.equal(r.executor.run_started_at,null); assert.equal(r.executor.completed_at,null);
});
test('unauthenticated request never reads task or GitHub', async () => {
  const r = await probe({unauthorized:true}); assert.equal(r.response.status,401); assert.equal(r.calls.length,0);
});
test('invalid input never calls GitHub', async () => {
  const r = await probe({invalid:true}); assert.equal(r.body.result.isError,true); assert.equal(r.calls.length,0);
});
test('tool discovery advertises strict read-only entry', async () => {
  const r = await probe({method:'tools/list'});
  assert.equal(r.body.result.tools.find(t=>t.name==='get_task_execution_status').annotations.readOnlyHint,true);
  assert.equal(r.calls.length,0);
});

for (const [label, oauth] of [
  ['asset-only', {scope:'asset.read'}], ['unknown', {scope:'unrecognized'}],
  ['missing', {scope:null}], ['wrong audience', {aud:'other'}],
  ['missing expiry', {exp:null}], ['expired', {exp:1}],
]) test('review: OAuth ' + label + ' fails before any task/GitHub read', async () => {
  const r = await probe({oauth});
  assert.ok(r.response.status === 401 || r.body.error?.code === -32002);
  assert.equal(r.calls.length,0); assert.equal(r.registryReads,0);
});
test('review: valid OAuth retains existing task access', async () => {
  assert.equal((await probe({oauth:{}})).result.executor.state,'completed');
});
for (const [label, options, reason] of [
  ['foreign repository', {run:{repository:{full_name:'other/repo'}}}, 'run_repository_mismatch'],
  ['missing repository', {run:{repository:null}}, 'run_repository_mismatch'],
  ['invalid configured path', {repo:'fixture/repo/../../other/repo'}, 'github_configuration_unavailable'],
]) test('review: ' + label + ' is unknown', async () => {
  const r = await probe(options);
  assert.equal(r.result.reason,reason); assert.equal(r.result.executor.state,'unknown');
});
