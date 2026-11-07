# NEXUS Accountability (1 page)

What the assistant can and cannot do. Synthetic demo; demo accounts only.

## Can access (when the caller's policy allows)

- Documents and chunks the caller's role/department/user grant permits.
- Own chat history only (never another user's turns).
- Aggregated stats (`/stats/summary`); security events (manager/admin);
  audit log (admin only).

## Can do autonomously

- Answer questions strictly from authorized passages, with `[doc:chunk]`
  citations, in ID or EN.
- Refuse generically when nothing authorized matches (no existence signal).
- Say "uncertain" and suggest the owning team when evidence is missing.
- Surface conflicts with both sides + effective dates (or resolve
  announcement-over-SOP when newer).
- Mask PII by default; neutralize and log prompt-injection attempts.

## Needs human authorization

- Unmasking PII: HR role AND explicit per-request opt-in (`allow_pii: true`).
- Uploading / re-policing / deleting documents: manager/HR/admin per endpoint.
- Viewing security events: manager/admin. Viewing the audit log: admin only.
- Key rotation, DB maintenance, production deploys: operator actions.

## Will never do

- Reveal unauthorized content, confirm/deny a restricted doc's existence, or
  merge evidence across policy boundaries into one answer.
- Execute instructions found inside documents, chats, or tasks (data is not
  instructions); never invent citations or return embedding vectors.
- Log plaintext secrets/keys, store real PII, or weaken a failing test to
  make it pass.
