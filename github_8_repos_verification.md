# GitHub 8-Repository Verification Report

**Task:** `cf-384b983f9068` (`RECOVER_AND_PUBLISH_GITHUB_8_REPO_VERIFICATION_REPORTS`)  
**Project:** `github-monetization-research`  
**Prior task:** `cf-c9d9adf75064`, prior checked_at **2026-10-21T02:02:25Z**  
**Fresh read-back generated:** 2026-10-21T03:00:04Z  
**Method:** direct read-only GitHub REST API, `raw.githubusercontent.com`, and official `docs.n8n.io` HTTP GETs. No web-search tool was used.

## Executive summary

| Status | Count |
|---|---:|
| VERIFIED | 5 |
| AMBIGUOUS | 1 |
| NOT_FOUND | 2 |
| **Total** | **8** |

Only `n8n-io/n8n` is runnable software. The other five resolved identities are curated resource directories. Two requested names could not be found at all. The `awesome` row is ambiguous because the requested label is generic and the source video page was inaccessible beyond its JavaScript shell; `sindresorhus/awesome` is the leading candidate, not a confirmed mapping.

> **Recovery note.** This is a reconstruction, not a byte-for-byte recovery. The prior run's local-only commit `2f23d1c590fcdf32ce02abb38497d6a15c2db3c2` is not present in this clone, so no prior Markdown bytes or hashes are claimed. All hashes below are newly computed from fresh read-back content.

## Verification table (8 rows)

| # | Requested name | Status | Resolved repository / identity | Source URL(s) |
|---:|---|---|---|---|
| 1 | `n8n` | **VERIFIED** | `n8n-io/n8n` — Fair-code workflow automation platform with native AI capabilities. Combine visual building with custom cod... | <https://github.com/n8n-io/n8n>, <https://github.com/n8n-io/n8n/commit/1ebe2cf55975b220aa63df91fe8e7f6d9659c94f> |
| 2 | `awesome-remote-job` | **VERIFIED** | `lukasz-madon/awesome-remote-job` — A curated list of awesome remote jobs and resources. Inspired by https://github.com/vinta/awesome-python | <https://github.com/lukasz-madon/awesome-remote-job>, <https://github.com/lukasz-madon/awesome-remote-job/commit/d7c1d773841358f72212c4c1a123adff6af56c78> |
| 3 | `awesome-telegram-groups` | **VERIFIED** | `stkw0/awesome-telegram-groups` — List of telegram groups  | <https://github.com/stkw0/awesome-telegram-groups>, <https://github.com/stkw0/awesome-telegram-groups/commit/1d7089adc4c8fda86aaa4c5305d2ef9fbb63de34> |
| 4 | `awesome` | **AMBIGUOUS** | `sindresorhus/awesome` — 😎 Awesome lists about all kinds of interesting topics [NOTE: Pull requests are temporarily disabled until I... | <https://github.com/sindresorhus/awesome>, <https://github.com/sindresorhus/awesome/commit/bc98e517ddca672f55f9857d714fc3ea3c3540b2> |
| 5 | `awesome-quant` | **VERIFIED** | `wilsonfreitas/awesome-quant` — A curated list of insanely awesome libraries, packages and resources for Quants (Quantitative Finance) | <https://github.com/wilsonfreitas/awesome-quant>, <https://github.com/wilsonfreitas/awesome-quant/commit/b52a1a942eda36a6539b886f26a4a391883580d6> |
| 6 | `awesome-public-datasets` | **VERIFIED** | `awesomedata/awesome-public-datasets` — A topic-centric list of HQ open datasets. | <https://github.com/awesomedata/awesome-public-datasets>, <https://github.com/awesomedata/awesome-public-datasets/commit/f484e9f66d4633ce35781e62a6fd05bb150b8eee> |
| 7 | `ai-money-mindset` | **NOT_FOUND** | No exact repository found | <https://api.github.com/search/repositories?q=%22ai-money-mindset%22+in%3Aname>, <https://api.github.com/repos/ai-money-mindset/ai-money-mindset> |
| 8 | `ai-goods-monitor` | **NOT_FOUND** | No exact repository found | <https://api.github.com/search/repositories?q=%22ai-goods-monitor%22+in%3Aname>, <https://api.github.com/repos/ai-goods-monitor/ai-goods-monitor> |

## Per-row evidence

### 1. `n8n` — VERIFIED

Exact repository n8n-io/n8n exists and was independently read back at a pinned commit.

- Repository: <https://github.com/n8n-io/n8n>
- Pinned commit: `1ebe2cf55975b220aa63df91fe8e7f6d9659c94f` (<https://github.com/n8n-io/n8n/commit/1ebe2cf55975b220aa63df91fe8e7f6d9659c94f>)
- Default branch: `master`; archived: `false`
- Stars/forks/open issues at read-back: 208166 / 61199 / 1209
- Last push: `2026-10-20T23:52:29Z`; maintenance classification: **active**
- License: Sustainable Use License 1.0 (non-.ee source) plus n8n Enterprise License for .ee files; GitHub API reports Other/NOASSERTION; not OSI-approved open source.
- README: `README.md`, 3998 bytes, SHA-256 `1b2642bc182969047627fc3568c785bad291fb9a2c7d655b19813608bf69ce27`, dual-source match `true`
- License file: `LICENSE.md`, 4445 bytes, SHA-256 `d2f621f59aa4c10eab79b6333e59d9d3d5b53307dcfd16dbd75e40e679e84965`, dual-source match `true`
- Enterprise license file: `LICENSE_EE.md`, 1879 bytes, SHA-256 `6110c69fd3b92928328a89e863dc2c862ea449f2335c352a9c4a137a36b13040`, dual-source match `true`
- Read-back sources: <https://raw.githubusercontent.com/n8n-io/n8n/1ebe2cf55975b220aa63df91fe8e7f6d9659c94f/README.md>, <https://api.github.com/repos/n8n-io/n8n/contents/README.md?ref=1ebe2cf55975b220aa63df91fe8e7f6d9659c94f>
- Notes: Only runnable software repository among the eight. Self-hostable workflow automation platform; use as an optional execution layer behind the existing control plane, subject to the Sustainable Use License.

### 2. `awesome-remote-job` — VERIFIED

Exact repository lukasz-madon/awesome-remote-job exists and was independently read back at a pinned commit.

- Repository: <https://github.com/lukasz-madon/awesome-remote-job>
- Pinned commit: `d7c1d773841358f72212c4c1a123adff6af56c78` (<https://github.com/lukasz-madon/awesome-remote-job/commit/d7c1d773841358f72212c4c1a123adff6af56c78>)
- Default branch: `master`; archived: `false`
- Stars/forks/open issues at read-back: 49731 / 4876 / 137
- Last push: `2026-09-21T15:00:51Z`; maintenance classification: **active**
- License: CC0-1.0 declared in the README license section; no root LICENSE file and GitHub API license is null.
- README: `README.md`, 67391 bytes, SHA-256 `53cb059d10e6c20e33e7c490e88327aa222a7b0de2d6863629a94732952db26c`, dual-source match `true`
- Read-back sources: <https://raw.githubusercontent.com/lukasz-madon/awesome-remote-job/d7c1d773841358f72212c4c1a123adff6af56c78/README.md>, <https://api.github.com/repos/lukasz-madon/awesome-remote-job/contents/README.md?ref=d7c1d773841358f72212c4c1a123adff6af56c78>
- Notes: Curated resource directory (Markdown lists), not runnable software. Useful as a research input only.

### 3. `awesome-telegram-groups` — VERIFIED

Exact repository stkw0/awesome-telegram-groups exists and was independently read back at a pinned commit.

- Repository: <https://github.com/stkw0/awesome-telegram-groups>
- Pinned commit: `1d7089adc4c8fda86aaa4c5305d2ef9fbb63de34` (<https://github.com/stkw0/awesome-telegram-groups/commit/1d7089adc4c8fda86aaa4c5305d2ef9fbb63de34>)
- Default branch: `master`; archived: `false`
- Stars/forks/open issues at read-back: 137 / 19 / 1
- Last push: `2020-11-17T19:15:58Z`; maintenance classification: **dormant**
- License: WTFPL (root LICENSE file); GitHub API license key wtfpl.
- README: `README.md`, 5658 bytes, SHA-256 `d4f8f665e89bb862f15099840f0006aae52eb682c3525b1874d4fdee91806eb5`, dual-source match `true`
- License file: `LICENSE`, 487 bytes, SHA-256 `40f2791ae84e097cc964b740cbd974e78296a36aa1490dcb76dcc004bf865ac8`, dual-source match `true`
- Read-back sources: <https://raw.githubusercontent.com/stkw0/awesome-telegram-groups/1d7089adc4c8fda86aaa4c5305d2ef9fbb63de34/README.md>, <https://api.github.com/repos/stkw0/awesome-telegram-groups/contents/README.md?ref=1d7089adc4c8fda86aaa4c5305d2ef9fbb63de34>
- Notes: Curated Telegram group list, not runnable software. Last push 2020-11-17; treat links as stale and verify before use.

### 4. `awesome` — AMBIGUOUS

The requested label is generic. sindresorhus/awesome is the leading candidate and exists, but the source video was unreadable beyond its JavaScript shell, so the intended identity cannot be confirmed.

- Repository: <https://github.com/sindresorhus/awesome>
- Pinned commit: `bc98e517ddca672f55f9857d714fc3ea3c3540b2` (<https://github.com/sindresorhus/awesome/commit/bc98e517ddca672f55f9857d714fc3ea3c3540b2>)
- Default branch: `main`; archived: `false`
- Stars/forks/open issues at read-back: 521987 / 37598 / 105
- Last push: `2026-09-02T02:10:47Z`; maintenance classification: **active**
- License: CC0-1.0 (root license file); GitHub API license key cc0-1.0.
- README: `readme.md`, 78330 bytes, SHA-256 `465cd781335e44587d238f666800104b63d4fc8ba2395d6422974dcba421c616`, dual-source match `true`
- License file: `license`, 6478 bytes, SHA-256 `d06492a8af3ebf435233748dbbc572abc189f2e9abcf0505a0e34a0212c728b3`, dual-source match `true`
- Read-back sources: <https://raw.githubusercontent.com/sindresorhus/awesome/bc98e517ddca672f55f9857d714fc3ea3c3540b2/readme.md>, <https://api.github.com/repos/sindresorhus/awesome/contents/readme.md?ref=bc98e517ddca672f55f9857d714fc3ea3c3540b2>
- Notes: Leading candidate only. The repository itself is verified; the mapping from the source's generic 'awesome' label to this repository is not.

### 5. `awesome-quant` — VERIFIED

Exact repository wilsonfreitas/awesome-quant exists and was independently read back at a pinned commit.

- Repository: <https://github.com/wilsonfreitas/awesome-quant>
- Pinned commit: `b52a1a942eda36a6539b886f26a4a391883580d6` (<https://github.com/wilsonfreitas/awesome-quant/commit/b52a1a942eda36a6539b886f26a4a391883580d6>)
- Default branch: `main`; archived: `false`
- Stars/forks/open issues at read-back: 30225 / 4192 / 146
- Last push: `2026-10-21T01:17:29Z`; maintenance classification: **active**
- License: No LICENSE file and no explicit license declaration found at the pinned commit; GitHub API license is null. Treat as all rights reserved unless the owner states otherwise.
- README: `README.md`, 156097 bytes, SHA-256 `6f2edfb35e721f7614e091435a6e189ebc032a5608e8c736fa8e7c7e8b35f15a`, dual-source match `true`
- Read-back sources: <https://raw.githubusercontent.com/wilsonfreitas/awesome-quant/b52a1a942eda36a6539b886f26a4a391883580d6/README.md>, <https://api.github.com/repos/wilsonfreitas/awesome-quant/contents/README.md?ref=b52a1a942eda36a6539b886f26a4a391883580d6>
- Notes: Curated quantitative-finance resource directory, not runnable software. Use as a link catalog only; do not copy contents without a license grant.

### 6. `awesome-public-datasets` — VERIFIED

Exact repository awesomedata/awesome-public-datasets exists and was independently read back at a pinned commit.

- Repository: <https://github.com/awesomedata/awesome-public-datasets>
- Pinned commit: `f484e9f66d4633ce35781e62a6fd05bb150b8eee` (<https://github.com/awesomedata/awesome-public-datasets/commit/f484e9f66d4633ce35781e62a6fd05bb150b8eee>)
- Default branch: `master`; archived: `false`
- Stars/forks/open issues at read-back: 79653 / 11905 / 165
- Last push: `2026-10-20T17:04:40Z`; maintenance classification: **active**
- License: MIT (root LICENSE file); GitHub API license key mit.
- README: `README.rst`, 278575 bytes, SHA-256 `e9da8267a50d32b1707f3bd85eb26d6e9899390c222bf8c76432dac5107a3266`, dual-source match `true`
- License file: `LICENSE`, 1122 bytes, SHA-256 `6f1baa6803708ad92643e9f00a7fac14c0c19e39b1fbca732cde94a9adaf981b`, dual-source match `true`
- Read-back sources: <https://raw.githubusercontent.com/awesomedata/awesome-public-datasets/f484e9f66d4633ce35781e62a6fd05bb150b8eee/README.rst>, <https://api.github.com/repos/awesomedata/awesome-public-datasets/contents/README.rst?ref=f484e9f66d4633ce35781e62a6fd05bb150b8eee>
- Notes: Curated open-dataset directory, not runnable software. Individual linked datasets have their own licenses.

### 7. `ai-money-mindset` — NOT_FOUND

No repository with this exact name was found. GitHub search for the quoted name in:name returned 0 results, and the direct repository API path returned HTTP 404.

- Search: <https://api.github.com/search/repositories?q=%22ai-money-mindset%22+in%3Aname> returned `total_count = 0`
- Direct repository API: <https://api.github.com/repos/ai-money-mindset/ai-money-mindset> returned HTTP `404`
- Notes: Do not treat similarly named third-party repositories as the requested project without independent confirmation.

### 8. `ai-goods-monitor` — NOT_FOUND

No repository with this exact name was found. GitHub search for the quoted name in:name returned 0 results, and the direct repository API path returned HTTP 404.

- Search: <https://api.github.com/search/repositories?q=%22ai-goods-monitor%22+in%3Aname> returned `total_count = 0`
- Direct repository API: <https://api.github.com/repos/ai-goods-monitor/ai-goods-monitor> returned HTTP `404`
- Notes: Do not treat similarly named third-party repositories as the requested project without independent confirmation.

## n8n license analysis

**Conclusion:** n8n is **source-available fair-code, not OSI-approved open source**. The repository's `LICENSE.md` applies the **Sustainable Use License 1.0** to non-`.ee` source, while `.ee` files require the separate **n8n Enterprise License** (`LICENSE_EE.md`). GitHub's license API reports `Other` / `NOASSERTION`.

Key Sustainable Use License points:

- Use or modify only for your own internal business purposes or for non-commercial/personal use.
- Distribute only free of charge for non-commercial purposes; do not remove licensing or copyright notices.
- Any violation terminates the license, with a 30-day cure period in the described notice scenario.

**Agency / client workflows:** official n8n FAQ permits building and running workflows for clients **on the operator's own instance only if clients cannot create or edit them** and have no access to the n8n instance or workflow logic. It explicitly disallows hosting n8n as a service where clients build workflows, letting external users build/configure workflows through a custom UI, API, MCP, or AI agent, white-labeling, and using enterprise features without an Enterprise license. For managing n8n across multiple client environments, the FAQ says to contact `license@n8n.io`; a partner program for multi-instance management is in development.

Sources: <https://docs.n8n.io/n8n-community-license> (HTTP 200), <https://docs.n8n.io/n8n-community-license/community-license/license-faq> (HTTP 200). The README-linked legacy URL <https://docs.n8n.io/sustainable-use-license/> returned HTTP 404 at check time and was not used as substantive evidence.

## Architecture reuse analysis

**Decision: do not replace the Cloudflare Worker/D1 + Hermes control plane.** Keep the existing control plane authoritative for ingress, authentication, policy, approvals, state, provenance, and scheduling.

Recommended reuse posture for n8n:

- Treat n8n as an **optional self-hosted workflow execution adapter** behind the existing control plane, reached through a narrow authenticated webhook/callback boundary.
- Keep identity, policy, approval, and persistence decisions in Cloudflare/Hermes; n8n must not become the source of truth.
- Run n8n as an internal operator tool. Do not expose the editor to clients or external end users.
- Pin the n8n version and leave `.ee` features disabled unless an Enterprise license is obtained.
- For multi-client or multi-instance management, obtain written licensing clarity from `license@n8n.io` before deployment.

The five `awesome-*` repositories are curated lists, not runnable software. Use them as research/link catalogs only; do not add them as runtime dependencies or copy content without checking each item's license. The two `NOT_FOUND` names must not be mapped to similarly named unrelated repositories.

## Read-back content hashes

Each value is SHA-256 over the UTF-8 file body read at the pinned commit. Every row below matched across two independent GitHub read paths (`raw.githubusercontent.com` and the Contents API).

| Repository | File | Bytes | SHA-256 | Dual-source match |
|---|---|---:|---|---|
| `n8n-io/n8n` | `README.md` | 3998 | `1b2642bc182969047627fc3568c785bad291fb9a2c7d655b19813608bf69ce27` | true |
| `n8n-io/n8n` | `LICENSE.md` | 4445 | `d2f621f59aa4c10eab79b6333e59d9d3d5b53307dcfd16dbd75e40e679e84965` | true |
| `n8n-io/n8n` | `LICENSE_EE.md` | 1879 | `6110c69fd3b92928328a89e863dc2c862ea449f2335c352a9c4a137a36b13040` | true |
| `lukasz-madon/awesome-remote-job` | `README.md` | 67391 | `53cb059d10e6c20e33e7c490e88327aa222a7b0de2d6863629a94732952db26c` | true |
| `stkw0/awesome-telegram-groups` | `README.md` | 5658 | `d4f8f665e89bb862f15099840f0006aae52eb682c3525b1874d4fdee91806eb5` | true |
| `stkw0/awesome-telegram-groups` | `LICENSE` | 487 | `40f2791ae84e097cc964b740cbd974e78296a36aa1490dcb76dcc004bf865ac8` | true |
| `sindresorhus/awesome` | `readme.md` | 78330 | `465cd781335e44587d238f666800104b63d4fc8ba2395d6422974dcba421c616` | true |
| `sindresorhus/awesome` | `license` | 6478 | `d06492a8af3ebf435233748dbbc572abc189f2e9abcf0505a0e34a0212c728b3` | true |
| `wilsonfreitas/awesome-quant` | `README.md` | 156097 | `6f2edfb35e721f7614e091435a6e189ebc032a5608e8c736fa8e7c7e8b35f15a` | true |
| `awesomedata/awesome-public-datasets` | `README.rst` | 278575 | `e9da8267a50d32b1707f3bd85eb26d6e9899390c222bf8c76432dac5107a3266` | true |
| `awesomedata/awesome-public-datasets` | `LICENSE` | 1122 | `6f1baa6803708ad92643e9f00a7fac14c0c19e39b1fbca732cde94a9adaf981b` | true |

## Limitations and provenance

- The source video page was inaccessible beyond its JavaScript shell during the prior run. Repository names came from the user-provided screenshot/task contract, not from a verified transcript.
- Prior checked_at is labeled **2026-10-21T02:02:25Z**. Prior commit `2f23d1c590fcdf32ce02abb38497d6a15c2db3c2` was local only and never pushed; it is absent from this clone, so exact prior file bytes cannot be recovered.
- `docs.n8n.io/sustainable-use-license/` returned HTTP 404; current official n8n license pages returned HTTP 200 and were used.
- Star/fork/issue counts are point-in-time snapshots. `stkw0/awesome-telegram-groups` last pushed in 2020 and is classified dormant.
- `wilsonfreitas/awesome-quant` has no root license file and no explicit license declaration at the pinned commit; this report does not infer a license for it.
- No secret, credential, production, workflow, deployment, trade, or post write was performed. Only the two allowlisted report files were written.

## Deterministic checks

- Row count: `8`; statuses: `VERIFIED=5`, `AMBIGUOUS=1`, `NOT_FOUND=2`.
- JSON/Markdown agreement: checked programmatically against the same row data.
- Read-back hashes: recomputed from content and compared across raw and Contents API sources; all matched.
- Evidence JSON: `github_8_repos_evidence.json`.

