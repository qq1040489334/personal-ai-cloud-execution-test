// Candidate adapter for the EXISTING Site /knowledge passkey completion route.
// It has no verifier, credentials, approval database or Canonical writer of its own.
// The deployed Site must supply its existing verifier as a server-owned closure.
const OPERATION = "KNOWLEDGE_PROMOTION";
const HASH = /^[0-9a-f]{64}$/;
const reject = (reason) => Response.json({ status: "BLOCKED", reason }, { status: 403 });
const digest = async (value) => Array.from(new Uint8Array(await crypto.subtle.digest(
  "SHA-256", new TextEncoder().encode(value))), b => b.toString(16).padStart(2, "0")).join("");

export function createKnowledgeApprovalRoute({ db, humanGate, origin } = {}) {
  // humanGate.verifyAndConsume is the existing WebAuthn challenge CAS, NOT an
  // HTTP receipt supplied by the caller. It must verify signature, RP, origin,
  // UP+UV, counter, exact payload and one-use challenge before returning a grant.
  return async function knowledgeApprovalRoute(request) {
    if (!db || typeof humanGate?.verifyAndConsume !== "function" || !origin)
      return reject("EXISTING_SITE_HUMAN_GATE_UNAVAILABLE");
    if (request.method !== "POST" || new URL(request.url).pathname !== "/knowledge/approve" ||
        new URL(request.url).origin !== origin || request.headers.get("Origin") !== origin)
      return reject("APPROVAL_ORIGIN_OR_ROUTE_INVALID");
    try {
      const input = await request.json();
      if (Object.keys(input).some(k => !["candidate_id", "candidate_version", "content_hash", "assertion"].includes(k)) ||
          typeof input.candidate_id !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9:_-]{0,127}$/.test(input.candidate_id) ||
          !Number.isSafeInteger(input.candidate_version) || input.candidate_version < 1 || !HASH.test(input.content_hash))
        return reject("EXACT_CANDIDATE_REQUIRED");
      const candidate = await db.prepare("SELECT * FROM knowledge_candidates WHERE candidate_id = ?")
        .bind(input.candidate_id).first();
      if (!candidate || candidate.status !== "APPROVED_FOR_PROMOTION" || candidate.review_state !== "PASS" ||
          candidate.version !== input.candidate_version || candidate.content_hash !== input.content_hash || !candidate.reviewed_at)
        return reject("CANDIDATE_NOT_REVIEWED_PASS");
      // Includes review generation and asset destination so a FAIL/re-PASS or
      // changed destination cannot reuse an old ceremony, even with equal content.
      const exactTarget = JSON.stringify({ operation: OPERATION, candidate_id: candidate.candidate_id,
        candidate_version: candidate.version, content_hash: candidate.content_hash,
        asset_id: candidate.asset_id, review_result: "PASS", reviewed_at: candidate.reviewed_at });
      const payloadHash = await digest(exactTarget);
      const grant = await humanGate.verifyAndConsume({ request, assertion: input.assertion,
        operation: OPERATION, exact_target: exactTarget, payload_sha256: payloadHash });
      const now = Math.floor(Date.now() / 1000);
      if (grant?.verified !== true || grant.operation !== OPERATION || grant.exact_target !== exactTarget ||
          grant.payload_sha256 !== payloadHash || !HASH.test(grant.requesting_user_hash) ||
          typeof grant.signer_identity !== "string" || !grant.signer_identity.trim() ||
          typeof grant.ceremony_id !== "string" || !/^[a-zA-Z0-9:_-]{1,128}$/.test(grant.ceremony_id) ||
          !Number.isSafeInteger(grant.expires_at) || grant.expires_at <= now || grant.expires_at > now + 300)
        return reject("WEBAUTHN_EXACT_GRANT_REQUIRED");
      const approvalId = `knowledge:${grant.ceremony_id}`;
      // INSERT SELECT rechecks the state after the passkey ceremony. A FAIL
      // that won first or a changed review generation makes the mint a no-op.
      const result = await db.prepare(`INSERT INTO personal_ai_approval_ledger
        (approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
         created_at, expires_at, asset_type, candidate_id, candidate_version,
         content_hash, review_result, approved_by)
        SELECT ?, ?, 'KNOWLEDGE_PROMOTION', ?, ?, ?, ?, 'KNOWLEDGE', candidate_id,
          version, content_hash, 'PASS', ? FROM knowledge_candidates
        WHERE candidate_id = ? AND version = ? AND content_hash = ? AND asset_id = ?
          AND status = 'APPROVED_FOR_PROMOTION' AND review_state = 'PASS' AND reviewed_at = ?`)
        .bind(approvalId, grant.requesting_user_hash, exactTarget, payloadHash, now,
          grant.expires_at, grant.signer_identity, candidate.candidate_id, candidate.version,
          candidate.content_hash, candidate.asset_id, candidate.reviewed_at).run();
      if (Number(result?.meta?.changes) !== 1) return reject("CANDIDATE_CHANGED_DURING_APPROVAL");
      return Response.json({ status: "REGISTERED", operation: OPERATION, approval_id: approvalId,
        candidate_id: candidate.candidate_id, candidate_version: candidate.version,
        content_hash: candidate.content_hash, expires_at: grant.expires_at, canonical_write_performed: false });
    } catch {
      // Never retry an ambiguous mint. Reconcile the same ceremony ID read-only.
      return reject("APPROVAL_MINT_FAILED_RECONCILE_REQUIRED");
    }
  };
}
