# Permission Matrix — Synthetic Dataset (SYNTHETIC)

Nusantara Digital Group — all data below is fictitious. No real PII.
Seeded via `nexus/scripts/seed_data.py`, which ingests every file through the
real ingest service (`parse -> chunk -> AES encrypt -> embed -> index`).

Demo users (see `scripts/seed_users.py`): `siti` (employee/engineering),
`hana` (hr/hr), `budi` (manager/engineering), `dewi` (finance/finance),
`agus` (admin/it, bypasses all policies).

## Policy levels

| Level | Policy | Who can read |
|---|---|---|
| PUBLIC | `allowed_roles: [admin, manager, hr, finance, employee]` | everyone |
| HR_ONLY | `allowed_roles: [admin, hr]` | hana, agus |
| FIN_ONLY | `allowed_roles: [admin, finance]` | dewi, agus |
| MGR_ONLY | `allowed_roles: [admin, manager]` | budi, agus |
| GARUDA | `allowed_users: [siti, budi]` (+admin bypass) | siti, budi, agus |
| ENG_DEPT | `allowed_departments: [engineering]` (+admin bypass) | siti, budi, agus |

## Files

### docs/ (24 files: 21 markdown, 2 txt, 1 json)

| File | Level | Notes |
|---|---|---|
| hr-leave-policy-v1.md | PUBLIC | conflict pair: 12 days (SOP, 2025-06-01) |
| hr-leave-policy-v2.md | PUBLIC | conflict pair: 14 days (SOP, 2026-02-01) |
| transport-allowance-sop.md | PUBLIC | conflict pair: Rp500.000 (SOP, 2026-01-15) |
| transport-allowance-announcement.md | PUBLIC | conflict pair: Rp750.000 (announcement, 2026-03-10, resolves) |
| wfh-policy-v1.md | PUBLIC | conflict pair: 2 days WFH (SOP, 2026-01-20) |
| wfh-policy-v2.md | PUBLIC | conflict pair: 3 days WFH (SOP, 2026-04-05) |
| onboarding-checklist-v1.md | PUBLIC | conflict pair: 5 steps (SOP, 2026-01-10) |
| onboarding-checklist-v2.md | PUBLIC | conflict pair: 7 steps (SOP, 2026-03-22) |
| onboarding-guide.md | PUBLIC | orientation guide, no figures |
| it-security-policy.md | PUBLIC | basic-retrieval target (reset password akun) |
| general-office-sop.md | PUBLIC | office hours, meeting rooms |
| office-event-announcement.md | PUBLIC | **prompt injection #1** (ignore previous instructions) |
| employee-directory.md | PUBLIC | **PII-heavy**: fake NIK 317400000000000x, phones, emails |
| project-garuda-charter.md | GARUDA | cross-source anchor (md) |
| finance-expense-memo.md | FIN_ONLY | conflict pair: Rp2.000.000 (memo, 2026-01-05) |
| finance-expense-sop.md | FIN_ONLY | conflict pair: Rp5.000.000 (SOP, 2026-04-01, resolves) |
| finance-quarterly-report.md | FIN_ONLY | revenue Rp1.200.000.000 + **injection #2** |
| hr-salary-records.md | HR_ONLY | salary figures Rp8.500.000 etc. |
| hr-compensation-memo.md | HR_ONLY | **prompt injection #3** (system prompt override) |
| manager-performance-review.md | MGR_ONLY | manager-restricted review |
| project-komodo-brief.md | ENG_DEPT | engineering-department only |
| it-acceptable-use-policy.txt | PUBLIC | txt format coverage |
| sop-archive-note.txt | PUBLIC | txt equivalent + PDF/DOCX note (pypdf/python-docx absent) |
| policy-faq.json | PUBLIC | json format coverage |

### chats/ (10 JSON exports)

| File | Level | Notes |
|---|---|---|
| chat-garuda-01/02/03.json | GARUDA | milestone Fase Satu/Dua discussion (cross-source) |
| chat-komodo-01/02.json | ENG_DEPT | Komodo tahapan discussion |
| chat-general-01..05.json | PUBLIC | orientation, leave procedure, WFH, rooms, canteen |

### tasks/ (4 files, 15 records)

| File | Level | Records |
|---|---|---|
| tasks-garuda.json | GARUDA | 4 Garuda milestone tasks (cross-source) |
| tasks-komodo.csv | ENG_DEPT | 4 Komodo tasks (csv coverage) |
| tasks-office.csv | PUBLIC | 4 office tasks (csv coverage) |
| tasks-finance.json | FIN_ONLY | 3 finance tasks |

Totals: 24 docs + 10 chat exports + 15 task records = 38 ingested files.
