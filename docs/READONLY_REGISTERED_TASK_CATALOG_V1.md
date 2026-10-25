# Registered task catalog candidate v1

Local candidate based on `6fc432c39231e88ebf7c7137b95c45fcf81fcc2f`.
No schema, binding, workflow, dispatch, review, approval or deployment changes.
The existing `task_execution_observation.v1` contract gains an additive
`execution_identity` field; existing executor/business/acceptance state semantics
and the 60-second observation TTL are preserved.

## Calling the catalog

Send the existing MCP endpoint a `tools/call` request:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_registered_tasks","arguments":{"limit":50}}}
```

Authorization: the existing owner static MCP token or an unexpired OAuth access
token with audience `mcp` and scope `mcp`; alternatively the existing exclusive
`task.read` scope bound to `task_project=cloud-assets-activation`. No new scope,
credential, OAuth registration or authorization request is introduced. Asset-only
tokens cannot call or discover the new tool. Existing `task.read` permissions for
the observer and write tools remain unchanged: they are still denied.

The catalog is fixed to `cloud-assets-activation` for all authorized callers.
`project_id`, when provided, must equal that value. Unknown arguments, explicit
null, invalid limit and invalid cursor are rejected before accessing KV.

## Paging and coverage

- `limit` defaults to 50, must be an integer from 1 through 100, and bounds KV
  source keys, not the number of matched project tasks. Each request makes exactly
  one KV `list` call with prefix `task:`. It does not scan all registry pages.
- Pass `pagination.next_cursor` unchanged as the next request's `cursor` while
  `has_more=true`. This is an AES-GCM encrypted and authenticated application
  continuation bound to this fixed project/namespace, expiring after 15 minutes;
  it uses the existing OAuth signing key (or existing owner MCP token in a
  static-only deployment). Raw source cursors are never returned. It is not an
  authentication token; normal authorization is still required. Key rotation
  invalidates outstanding cursors. Empty pages can have `has_more=true` after filtering or source expiry.
  Application tokens are bounded to 8192 characters, covering the encrypted JSON
  worst case for the permitted 2048-character printable source cursor.
  Stop only on `has_more=false`, not on an empty tasks array.
- KV is eventually consistent. Concurrent changes may invalidate a cursor or
  cause omissions/repetitions across pages. Clients should deduplicate task IDs;
  this API does not promise an atomic snapshot or a global task count.
- `full_task_coverage=false` on every response, including the last/empty page.
  The scope is one page of registered tasks in the fixed project. Registry
  completion says nothing about other execution systems or all employees being
  idle. No `list_tasks` source name should be used to manufacture projector
  coverage.
- Read bodies and all declared parent/root references to verify membership,
  including ancestors outside the current page; compare complete metadata and
  dispatch-contract identity fields with the body. Cycles, missing/conflicting
  lineage and malformed source pages fail closed. Bounded metadata falls back to
  the full body. At most 200 body reads per request and 64 lineage nodes per
  traversal are allowed; lower `limit` for complex ancestry if necessary.
- On `TASK_CATALOG_SOURCE_FAILED` there is no partial tasks response, cursor or
  exception text. Malformed, oversized or immediately repeating source cursors
  are rejected. Raw/tampered/expired or incorrectly bound application cursors
  fail before KV access. Source reads do not establish an enduring snapshot.
  Encryption hides cursor content; page count, filtering and timing can still
  reveal traversal shape. This is not a project-specific namespace or a guarantee
  that other projects' existence is hidden.

## Minimal fields and identity boundary

Each task returns only `task_id`, the verified fixed `project_id`,
`parent_task_id`, `root_task_id`, validated `created_at`/`registry_updated_at`,
`registration_state=registered`, `runtime_state=unknown`, `agent_state=unknown`
and `execution_identity`. There are no prompts, titles, instructions, notes,
contracts, account/credential fields or raw registry statuses in the response.
Reviewed/completed and newly registered records are both eligible.

The identity contract is deliberately explicit:

```json
{"state":"unknown","employee_id":null,"agent_id":null,"configured":null,"observed":null,"receipt_identity_verified":false,"reason":"trusted_agent_identity_unavailable"}
```

The catalog never changes this based on task/registry/receipt claims. The strict
single-task observer fills `observed` only after its existing run mapping and
status checks pass. It reports only `source=github_actions_run_api`,
`executor_kind=github_actions_workflow_run`, repository, run ID/attempt,
allowlisted workflow path (otherwise null), and a validated `run_head_sha`
(otherwise null). That SHA describes the run head, not a verified workflow
revision. No extra GETs or receipt downloads are added.

`configured` remains null because the current checkout's OpenCode/DeepSeek
configuration does not identify the workflow revision used by a historical run.
`employee_id`, `agent_id`, identity `state`, receipt verification, business and
acceptance remain unknown. GitHub actor, git author, model strings and untrusted
agent-result `execution_identity` fields are never used as employee identities.
A running workflow is not proof of a Codex/Grok session or model inference.

## Exact remaining work

Trusted model/employee identity is not implemented end to end. Existing receipts
copy agent-controlled fields and lack verified engine/session attribution. A
follow-up must bind the actual executed workflow revision/configuration and a
trusted receipt to run ID/attempt/task ID, overwrite conflicting agent-provided
claims, and map executor IDs to employees only in trusted existing configuration.
This requires no new state schema in principle, but it does change the workflow/
receipt-producing path and is deliberately outside this read-only candidate.
Real Codex/Grok employees additionally require their real execution source.

The owner-private office v59 source/deployment was not available in this cloud
checkout. No UI adapter, deployment, production runtime verification or renewed
network probe is included. Production API and office reachability remain the
previously documented blockers.

## Offline checks

```sh
node --test tests/test_registered_task_catalog.cjs tests/test_task_execution_status.cjs tests/test_early_task_run.cjs tests/test_production_compat.cjs
```

The new file has 12 original boundary tests plus three cursor privacy regressions. Storage/network attempts are
recorded even when a caught exception would hide them; all fetches in observer
fixtures are mocked. Existing narrow observer and permission regressions are
included. This does not run the full suite or any historical/production task.
