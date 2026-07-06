# FactorySimulation Documentation Index

Updated: 2026-07-06

Use this file to decide which documents are the current contract.

## Trust Levels

- CURRENT: authoritative for the current product direction.
- ACTIVE: current product contract or completed MVP baseline that future product work should extend.
- REFERENCE: implemented and useful, but frozen or not the future product direction.
- ARCHIVE: historical context only.

## Read Order

1. `CONTEXT.md` - shortest repo-level summary.
2. `docs/DOCS_INDEX.md` - trust levels and document map.
3. `docs/AGENT_CONTEXT.md` - working context for new Codex sessions.
4. `docs/CURRENT_STATE.md` - current product state and watch-outs.
5. `docs/DECISION_LOG.md` - durable decisions.
6. `docs/prd/active/production-planning-pivot.md` - active PRD for the planning-core pivot.
7. `docs/prd/active/production-planning-mvp-slices.md` - implementation sequence for the first MVP.
8. `docs/prd/active/production-planning-issue-drafts.md` - published GitHub issue record for issues #16-#22.
9. `docs/planning-workbook-contract.md` - executable Excel workbook and CLI contract.
10. `docs/prd/active/production-planning-ui-slices.md` - implemented planning UI workbook-runner baseline and slice contract.

## CURRENT Documents

- `docs/DOCS_INDEX.md`
- `docs/AGENT_CONTEXT.md`
- `docs/CURRENT_STATE.md`
- `docs/DECISION_LOG.md`

These documents define the current product direction: FactorySimulation V2 has pivoted to a production-planning core, and the first planning-core MVP package (#16-#22) is complete.

## ACTIVE Documents

- `docs/prd/active/production-planning-pivot.md`
- `docs/prd/active/production-planning-mvp-slices.md`
- `docs/prd/active/production-planning-issue-drafts.md`
- `docs/planning-workbook-contract.md`
- `docs/prd/active/production-planning-ui-slices.md`

These are active product/data, implementation-sequence, issue-record, executable workbook, and planning UI contracts for the planning core. The #16-#22 MVP package and first planning UI workbook-runner baseline are complete; future slices should extend this baseline rather than reopen the route/canvas prototype direction.

## REFERENCE Documents

- `docs/prd/done/route-based-material-routing.md`
- `docs/prd/done/canvas-click-route-selection.md`
- `docs/prd/done/operator-resource-constraints.md`
- `docs/prd/done/monthly-expected-production.md`
- `docs/prd/done/ui-and-process-block-taxonomy.md`
- `docs/manual-smoke-checklist.md`

These describe the frozen Tkinter route/canvas prototype. Use them for demos, regression checks, or maintenance when explicitly requested. Do not infer future production-planning requirements from them.

## ARCHIVE Documents

- `docs/prd/archive/`
- `docs/handoffs/archive/`

These are historical notes. They should not override CURRENT or ACTIVE documents.

## Product Boundary

The route/canvas prototype is preserved, but future product work should start from:

- monthly/weekly production plan imports
- historical work-order routing imports
- recipe candidate and confirmed recipe records
- equipment master/current snapshots
- Excel T.B.D recipe tables
- user-authored comparison scenarios
- deterministic planning calculations

AI can draft and recommend. It cannot be the calculation verifier.
