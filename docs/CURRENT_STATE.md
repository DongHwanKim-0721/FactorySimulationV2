# Current State

Updated: 2026-06-10

## Product Goal

FactorySimulation should model the real factory layout first, then simulate multiple raw material inputs moving through their own routes over shared equipment. The goal is production coverage analysis: lead time, waiting, bottlenecks, and weekly/monthly expected production across a factory layout, not only one product path.

## Current Behavior

- Route-based material flow is the active model when INPUT blocks exist.
- Each INPUT block owns an ordered route of actual non-input block IDs.
- Empty routes are invalid in route mode.
- Consecutive repeated route steps are shown and simulated as pass counts.
- Non-consecutive revisits re-enter the same equipment queue.
- Shared equipment creates waiting time across multiple input routes.
- Hoists affect lead time only when explicitly included in a route.
- Operator assignments constrain route step start times without changing duration or capacity.
- User-facing lead time and waiting time are shown in hours.
- Weekly/monthly expected production panels use realized simulation output, not theoretical bottleneck CAPA.

## Implemented PRDs

- `docs/prd/done/route-based-material-routing.md`
- `docs/prd/done/operator-resource-constraints.md`
- `docs/prd/done/monthly-expected-production.md`
- `docs/prd/done/ui-and-process-block-taxonomy.md`

## Active PRDs

There are no active PRDs at the time of this cleanup. Add new planning docs under `docs/prd/active/`.

## Historical Reference

Older phase PRDs and handoffs were moved into:

- `docs/prd/archive/`
- `docs/handoffs/archive/`

These are preserved for history and should not override this file or the done PRDs.

## Current Verification

Last local automated verification:

```text
pytest -q
99 passed
```

The desktop executable was rebuilt with:

```powershell
pyinstaller --noconsole --onefile --name FactorySimulation main.py
```

## Watch-Outs

- Do not reintroduce connection-based material flow as the active model.
- Do not make hoists implicit; users must include hoists in routes.
- Do not split one INPUT route into branches in the first route model.
- Do not treat historical handoffs as the current contract.
- Do not close GitHub issues automatically; the user asked to review first.

