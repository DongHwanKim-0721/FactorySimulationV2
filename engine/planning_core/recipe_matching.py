from __future__ import annotations

from dataclasses import dataclass

from .contracts import ProductionPlanLine, RecipeHeader


SELECTABLE_RECIPE_STATUSES = {"AUTO_CANDIDATE", "USER_CONFIRMED"}


@dataclass(frozen=True)
class RecipePlanMatch:
    plan_source_row_id: str
    domain_code: str
    item_code: str
    status: str
    selected_recipe_id: str
    candidate_recipe_ids: tuple[str, ...]
    deprecated_recipe_ids: tuple[str, ...]
    tbd_recipe_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class MissingRecipeReportRow:
    plan_source_row_id: str
    plan_batch_id: str
    domain_code: str
    item_code: str
    item_name: str
    customer_name: str
    customer_order_ref: str
    reason: str
    raw_values: dict[str, object]


@dataclass(frozen=True)
class RecipeMatchingResult:
    matches: tuple[RecipePlanMatch, ...]
    tbd_report_rows: tuple[MissingRecipeReportRow, ...]


def match_plan_lines_to_recipes(
    plan_lines: tuple[ProductionPlanLine, ...] | list[ProductionPlanLine],
    recipe_headers: tuple[RecipeHeader, ...] | list[RecipeHeader],
) -> RecipeMatchingResult:
    matches: list[RecipePlanMatch] = []
    tbd_report_rows: list[MissingRecipeReportRow] = []

    for plan_line in plan_lines:
        headers = sorted(
            (
                header
                for header in recipe_headers
                if (
                    header.domain_code == plan_line.domain_code
                    and header.item_code == plan_line.item_code
                )
            ),
            key=lambda header: (header.recipe_id, header.recipe_version),
        )
        selectable = tuple(
            header
            for header in headers
            if header.recipe_status in SELECTABLE_RECIPE_STATUSES
        )
        deprecated_recipe_ids = tuple(
            header.recipe_id
            for header in headers
            if header.recipe_status == "DEPRECATED"
        )
        tbd_recipe_ids = tuple(
            header.recipe_id
            for header in headers
            if header.recipe_status == "TBD"
        )

        if len(selectable) == 1:
            status = "MATCHED"
            selected_recipe_id = selectable[0].recipe_id
            reason = "SINGLE_SELECTABLE_RECIPE"
        elif len(selectable) > 1:
            status = "AMBIGUOUS"
            selected_recipe_id = ""
            reason = "MULTIPLE_SELECTABLE_RECIPES"
        elif deprecated_recipe_ids:
            status = "DEPRECATED_ONLY"
            selected_recipe_id = ""
            reason = "DEPRECATED_ONLY"
        else:
            status = "MISSING"
            selected_recipe_id = ""
            reason = "MISSING"

        match = RecipePlanMatch(
            plan_source_row_id=plan_line.source_row_id,
            domain_code=plan_line.domain_code,
            item_code=plan_line.item_code,
            status=status,
            selected_recipe_id=selected_recipe_id,
            candidate_recipe_ids=tuple(header.recipe_id for header in selectable),
            deprecated_recipe_ids=deprecated_recipe_ids,
            tbd_recipe_ids=tbd_recipe_ids,
            reason=reason,
        )
        matches.append(match)

        if status in {"DEPRECATED_ONLY", "MISSING"}:
            tbd_report_rows.append(_tbd_report_row(plan_line, reason))

    return RecipeMatchingResult(
        matches=tuple(matches),
        tbd_report_rows=tuple(tbd_report_rows),
    )


def _tbd_report_row(
    plan_line: ProductionPlanLine,
    reason: str,
) -> MissingRecipeReportRow:
    return MissingRecipeReportRow(
        plan_source_row_id=plan_line.source_row_id,
        plan_batch_id=plan_line.plan_batch_id,
        domain_code=plan_line.domain_code,
        item_code=plan_line.item_code,
        item_name=plan_line.item_name,
        customer_name=plan_line.customer_name,
        customer_order_ref=plan_line.customer_order_ref,
        reason=reason,
        raw_values=plan_line.raw_values,
    )
