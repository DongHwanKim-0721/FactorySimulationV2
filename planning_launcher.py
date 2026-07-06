from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from engine.planning_core import (
    PLANNING_WORKBOOK_SHEETS,
    PlanningWorkbookError,
    PlanningWorkbookRunConfig,
    PlanningWorkbookRunRequest,
    PlanningWorkbookRunRequestError,
    PlanningWorkbookRunResult,
    PlanningWorkbookRunSummary,
    PlanningWorkbookValidationError,
    create_planning_workbook_template,
    load_xlsx_sheet_rows,
    run_planning_workbook,
)


SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_6 = 24
FIELD_WIDTH = 34
PATH_FIELD_WIDTH = 62
SUMMARY_HEIGHT = 16
WINDOW_WIDTH = 980
WINDOW_HEIGHT = 720
WORKBOOK_CONTRACT_DOC_PATH = Path("docs/planning-workbook-contract.md")

RUN_METADATA_FIELD_LABELS = (
    ("plan_batch_id", "Plan batch id"),
    ("plan_period", "Plan period"),
    ("plan_type", "Plan type"),
    ("work_order_import_batch_id", "Work-order import batch id"),
    ("equipment_snapshot_batch_id", "Equipment snapshot batch id"),
    ("equipment_snapshot_at", "Equipment snapshot timestamp"),
    ("tbd_import_batch_id", "T.B.D import batch id"),
    ("engine_version", "Engine version"),
)


RunService = Callable[[PlanningWorkbookRunRequest], PlanningWorkbookRunResult]
TemplateService = Callable[..., object]


@dataclass(frozen=True)
class PlanningLauncherInputs:
    input_workbook_path: str
    json_output_path: str
    report_workbook_output_path: str
    plan_batch_id: str
    plan_period: str
    plan_type: str
    work_order_import_batch_id: str
    equipment_snapshot_batch_id: str
    equipment_snapshot_at: str
    tbd_import_batch_id: str
    engine_version: str


@dataclass(frozen=True)
class WorkbookContractInspection:
    workbook_path: Path
    missing_sheet_names: tuple[str, ...]
    sheet_row_counts: tuple[tuple[str, int], ...]

    @property
    def is_valid(self) -> bool:
        return not self.missing_sheet_names


@dataclass(frozen=True)
class RunReadinessInspection:
    missing_input_workbook: bool
    missing_output_path: bool
    missing_metadata_fields: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return (
            not self.missing_input_workbook
            and not self.missing_output_path
            and not self.missing_metadata_fields
        )


@dataclass(frozen=True)
class SuggestedOutputPaths:
    json_output_path: Path
    report_workbook_output_path: Path


def build_run_request(inputs: PlanningLauncherInputs) -> PlanningWorkbookRunRequest:
    return PlanningWorkbookRunRequest(
        input_workbook_path=inputs.input_workbook_path,
        config=PlanningWorkbookRunConfig(
            plan_batch_id=inputs.plan_batch_id,
            plan_period=inputs.plan_period,
            plan_type=inputs.plan_type,
            work_order_import_batch_id=inputs.work_order_import_batch_id,
            equipment_snapshot_batch_id=inputs.equipment_snapshot_batch_id,
            equipment_snapshot_at=inputs.equipment_snapshot_at,
            tbd_import_batch_id=inputs.tbd_import_batch_id,
            engine_version=inputs.engine_version,
        ),
        json_output_path=_blank_to_none(inputs.json_output_path),
        report_workbook_output_path=_blank_to_none(
            inputs.report_workbook_output_path
        ),
    )


def suggest_output_paths(
    input_workbook_path: str | Path,
) -> SuggestedOutputPaths:
    path = _required_path(input_workbook_path, "input workbook path")
    stem = path.stem if path.stem else "planning-input"
    return SuggestedOutputPaths(
        json_output_path=path.with_name(f"{stem}-planning-run-report.json"),
        report_workbook_output_path=path.with_name(
            f"{stem}-planning-run-report.xlsx"
        ),
    )


def output_artifact_paths(
    result: PlanningWorkbookRunResult,
) -> tuple[Path, ...]:
    paths: list[Path] = []
    if result.json_output_path is not None:
        paths.append(result.json_output_path)
    if result.report_workbook_output_path is not None:
        paths.append(result.report_workbook_output_path)
    return tuple(paths)


def format_output_artifacts(paths: tuple[Path, ...]) -> str:
    if not paths:
        return "No output artifacts have been generated in this session."
    return "\n".join(
        (
            "Generated output artifacts:",
            *(f"  {path}" for path in paths),
        )
    )


def inspect_run_readiness(inputs: PlanningLauncherInputs) -> RunReadinessInspection:
    return RunReadinessInspection(
        missing_input_workbook=not inputs.input_workbook_path.strip(),
        missing_output_path=(
            not inputs.json_output_path.strip()
            and not inputs.report_workbook_output_path.strip()
        ),
        missing_metadata_fields=tuple(
            label
            for key, label in RUN_METADATA_FIELD_LABELS
            if not getattr(inputs, key).strip()
        ),
    )


def format_run_readiness_inspection(
    inspection: RunReadinessInspection,
) -> str:
    if inspection.is_valid:
        return (
            "Run preflight passed\n"
            "Input workbook, output path, and required metadata are present."
        )

    lines = ["Run preflight failed", "", "Required before execution:"]
    if inspection.missing_input_workbook:
        lines.append("  Input workbook")
    if inspection.missing_output_path:
        lines.append("  JSON report or report workbook output path")
    for field in inspection.missing_metadata_fields:
        lines.append(f"  {field}")
    return "\n".join(lines)


def inspect_workbook_contract(
    workbook_path: str | Path,
) -> WorkbookContractInspection:
    path = _required_path(workbook_path, "input workbook path")
    sheet_rows = load_xlsx_sheet_rows(path)
    required_sheet_names = tuple(PLANNING_WORKBOOK_SHEETS.values())
    return WorkbookContractInspection(
        workbook_path=path,
        missing_sheet_names=tuple(
            sheet_name
            for sheet_name in required_sheet_names
            if sheet_name not in sheet_rows
        ),
        sheet_row_counts=tuple(
            (sheet_name, len(sheet_rows[sheet_name]))
            for sheet_name in required_sheet_names
            if sheet_name in sheet_rows
        ),
    )


def format_workbook_contract_inspection(
    inspection: WorkbookContractInspection,
) -> str:
    if inspection.is_valid:
        lines = [
            "Workbook contract check passed",
            f"Workbook: {inspection.workbook_path}",
            "",
            "Required sheets:",
        ]
    else:
        lines = [
            "Workbook contract check failed",
            f"Workbook: {inspection.workbook_path}",
            "",
            "Missing required sheets:",
            *(
                f"  {sheet_name}"
                for sheet_name in inspection.missing_sheet_names
            ),
            "",
            "Loaded required sheets:",
        ]

    if inspection.sheet_row_counts:
        lines.extend(
            f"  {sheet_name}: {row_count} rows"
            for sheet_name, row_count in inspection.sheet_row_counts
        )
    else:
        lines.append("  None")

    return "\n".join(lines)


def format_workbook_contract_reference(
    *,
    base_path: str | Path | None = None,
) -> str:
    doc_path = WORKBOOK_CONTRACT_DOC_PATH
    display_path = doc_path if base_path is None else Path(base_path) / doc_path
    sheets = "\n".join(
        f"  {sheet_name}"
        for sheet_name in PLANNING_WORKBOOK_SHEETS.values()
    )
    return (
        "Workbook contract document\n"
        f"Path: {display_path}\n"
        "\n"
        "Required input sheets:\n"
        f"{sheets}\n"
        "\n"
        "Run metadata must be entered explicitly in this window."
    )


def format_run_summary(
    result: PlanningWorkbookRunResult,
) -> str:
    lines = [
        "Run complete",
        f"Input workbook: {result.input_workbook_path}",
    ]
    if result.json_output_path is not None:
        lines.append(f"JSON report: {result.json_output_path}")
    if result.report_workbook_output_path is not None:
        lines.append(f"Report workbook: {result.report_workbook_output_path}")

    lines.extend(("", *format_summary_lines(result.summary)))
    return "\n".join(lines)


def format_summary_lines(summary: PlanningWorkbookRunSummary) -> tuple[str, ...]:
    lines = [
        f"Calculation authority: {summary.calculation_authority}",
        "Deferred capabilities: "
        + _joined_or_none(summary.deferred_capabilities),
        (
            "Recipe matching: "
            f"{summary.matched_count} matched, "
            f"{summary.missing_count} missing, "
            f"{summary.ambiguous_count} ambiguous, "
            f"{summary.tbd_report_row_count} T.B.D rows"
        ),
        "Skipped scenarios: "
        + _joined_or_none(summary.skipped_scenario_ids),
        "",
        "Scenario ranking:",
    ]
    if summary.ranked_scenarios:
        for scenario in summary.ranked_scenarios:
            lines.append(
                "  "
                f"{scenario.rank}. {scenario.scenario_id} | "
                f"score {scenario.deterministic_score:g} | "
                f"missing {scenario.missing_recipe_count} | "
                f"ambiguous {scenario.ambiguous_recipe_count} | "
                f"risk {scenario.risk_score_total:g}"
            )
    else:
        lines.append("  None")

    lines.extend(("", "Top bottleneck risks:"))
    if summary.top_bottleneck_risks:
        for risk in summary.top_bottleneck_risks:
            lines.append(
                "  "
                f"{risk.scenario_id} | {risk.domain_code} | "
                f"{risk.process_group} | {risk.equipment_group} | "
                f"{risk.risk_level} | score {risk.risk_score:g} | "
                f"{_joined_or_none(risk.signals)}"
            )
    else:
        lines.append("  None")

    return tuple(lines)


class PlanningWorkbookLauncher:
    def __init__(
        self,
        root: tk.Tk | tk.Toplevel,
        *,
        run_service: RunService = run_planning_workbook,
        template_service: TemplateService = create_planning_workbook_template,
    ) -> None:
        self.root = root
        self.run_service = run_service
        self.template_service = template_service
        self.variables = {
            "input_workbook_path": tk.StringVar(),
            "json_output_path": tk.StringVar(),
            "report_workbook_output_path": tk.StringVar(),
            "plan_batch_id": tk.StringVar(),
            "plan_period": tk.StringVar(),
            "plan_type": tk.StringVar(),
            "work_order_import_batch_id": tk.StringVar(),
            "equipment_snapshot_batch_id": tk.StringVar(),
            "equipment_snapshot_at": tk.StringVar(),
            "tbd_import_batch_id": tk.StringVar(),
            "engine_version": tk.StringVar(),
        }
        self.status_var = tk.StringVar(value="Ready")
        self.last_output_artifacts: tuple[Path, ...] = ()

        self._configure_window()
        self._create_widgets()

    def _configure_window(self) -> None:
        self.root.title("Planning Workbook Runner")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(860, 620)

    def _create_widgets(self) -> None:
        main = ttk.Frame(self.root, padding=SPACE_4)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        title = ttk.Label(
            main,
            text="Planning Workbook Runner",
            font=("Arial", 14, "bold"),
        )
        title.grid(row=0, column=0, sticky=tk.W, pady=(0, SPACE_3))

        template_frame = ttk.LabelFrame(
            main,
            text="Template",
            padding=SPACE_3,
        )
        template_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, SPACE_3))
        template_frame.columnconfigure(0, weight=1)
        ttk.Button(
            template_frame,
            text="Create sample template",
            command=lambda: self._create_template(blank=False),
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, SPACE_2))
        ttk.Button(
            template_frame,
            text="Create blank template",
            command=lambda: self._create_template(blank=True),
        ).grid(row=0, column=1, sticky=tk.W)

        body = ttk.PanedWindow(main, orient=tk.VERTICAL)
        body.grid(row=2, column=0, sticky=tk.NSEW)

        run_frame = ttk.LabelFrame(
            body,
            text="Run configuration",
            padding=SPACE_3,
        )
        body.add(run_frame, weight=3)
        run_frame.columnconfigure(1, weight=1)

        row = 0
        row = self._path_row(
            run_frame,
            row,
            "Input workbook",
            "input_workbook_path",
            self._choose_input_workbook,
        )
        row = self._path_row(
            run_frame,
            row,
            "JSON report",
            "json_output_path",
            lambda: self._choose_output_path(
                "json_output_path",
                "Planning report JSON",
                ".json",
            ),
        )
        row = self._path_row(
            run_frame,
            row,
            "Report workbook",
            "report_workbook_output_path",
            lambda: self._choose_output_path(
                "report_workbook_output_path",
                "Planning report workbook",
                ".xlsx",
            ),
        )

        ttk.Separator(run_frame).grid(
            row=row,
            column=0,
            columnspan=3,
            sticky=tk.EW,
            pady=(SPACE_2, SPACE_3),
        )
        row += 1

        fields = (
            ("Plan batch id", "plan_batch_id"),
            ("Plan period", "plan_period"),
            ("Plan type", "plan_type"),
            ("Work-order import batch id", "work_order_import_batch_id"),
            ("Equipment snapshot batch id", "equipment_snapshot_batch_id"),
            ("Equipment snapshot timestamp", "equipment_snapshot_at"),
            ("T.B.D import batch id", "tbd_import_batch_id"),
            ("Engine version", "engine_version"),
        )
        for label, key in fields:
            row = self._field_row(run_frame, row, label, key)

        action_row = ttk.Frame(run_frame)
        action_row.grid(
            row=row,
            column=0,
            columnspan=3,
            sticky=tk.EW,
            pady=(SPACE_3, 0),
        )
        ttk.Button(
            action_row,
            text="Check workbook",
            command=self._check_workbook,
        ).pack(side=tk.LEFT, padx=(0, SPACE_2))
        ttk.Button(
            action_row,
            text="Suggest output paths",
            command=self._suggest_output_paths,
        ).pack(side=tk.LEFT, padx=(0, SPACE_2))
        ttk.Button(
            action_row,
            text="Check run fields",
            command=self._check_run_fields,
        ).pack(side=tk.LEFT, padx=(0, SPACE_2))
        ttk.Button(
            action_row,
            text="Run workbook",
            command=self._run_workbook,
        ).pack(side=tk.LEFT)
        ttk.Button(
            action_row,
            text="Contract",
            command=self._show_contract_reference,
        ).pack(side=tk.LEFT, padx=(SPACE_2, 0))
        ttk.Button(
            action_row,
            text="Show outputs",
            command=self._show_output_artifacts,
        ).pack(side=tk.LEFT, padx=(SPACE_2, 0))
        ttk.Label(
            action_row,
            textvariable=self.status_var,
        ).pack(side=tk.LEFT, padx=(SPACE_3, 0))

        summary_frame = ttk.LabelFrame(
            body,
            text="Summary",
            padding=SPACE_3,
        )
        body.add(summary_frame, weight=2)
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)
        self.summary_text = tk.Text(
            summary_frame,
            height=SUMMARY_HEIGHT,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.summary_text.grid(row=0, column=0, sticky=tk.NSEW)
        summary_scroll = ttk.Scrollbar(
            summary_frame,
            orient=tk.VERTICAL,
            command=self.summary_text.yview,
        )
        summary_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        self._set_summary("Select a workbook, enter run metadata, and choose at least one output path.")

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        key: str,
        command: Callable[[], None],
    ) -> int:
        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky=tk.W,
            padx=(0, SPACE_2),
            pady=SPACE_1,
        )
        ttk.Entry(
            parent,
            textvariable=self.variables[key],
            width=PATH_FIELD_WIDTH,
        ).grid(row=row, column=1, sticky=tk.EW, pady=SPACE_1)
        ttk.Button(parent, text="Browse", command=command).grid(
            row=row,
            column=2,
            sticky=tk.E,
            padx=(SPACE_2, 0),
            pady=SPACE_1,
        )
        return row + 1

    def _field_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        key: str,
    ) -> int:
        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky=tk.W,
            padx=(0, SPACE_2),
            pady=SPACE_1,
        )
        if key == "plan_type":
            field = ttk.Combobox(
                parent,
                textvariable=self.variables[key],
                values=("MONTHLY", "WEEKLY"),
                width=FIELD_WIDTH,
            )
        else:
            field = ttk.Entry(
                parent,
                textvariable=self.variables[key],
                width=FIELD_WIDTH,
            )
        field.grid(row=row, column=1, sticky=tk.W, pady=SPACE_1)
        return row + 1

    def _choose_input_workbook(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose planning input workbook",
            filetypes=(("Excel workbooks", "*.xlsx"), ("All files", "*.*")),
        )
        if path:
            self.variables["input_workbook_path"].set(path)

    def _choose_output_path(
        self,
        key: str,
        title: str,
        extension: str,
    ) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=title,
            defaultextension=extension,
            filetypes=(("Expected format", f"*{extension}"), ("All files", "*.*")),
        )
        if path:
            self.variables[key].set(path)

    def _create_template(self, *, blank: bool) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Create planning workbook template",
            defaultextension=".xlsx",
            filetypes=(("Excel workbooks", "*.xlsx"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            self.template_service(path, blank=blank)
        except (OSError, PlanningWorkbookError) as exc:
            self._show_error("Template creation failed", str(exc))
            return
        self.status_var.set("Template created")
        self._set_summary(f"Template created: {Path(path)}")

    def _suggest_output_paths(self) -> None:
        try:
            suggested = suggest_output_paths(
                self.variables["input_workbook_path"].get()
            )
        except PlanningWorkbookRunRequestError as exc:
            self.status_var.set("Output path suggestion failed")
            self._set_summary(str(exc))
            self._show_error("Output path suggestion failed", str(exc))
            return

        if not self.variables["json_output_path"].get().strip():
            self.variables["json_output_path"].set(str(suggested.json_output_path))
        if not self.variables["report_workbook_output_path"].get().strip():
            self.variables["report_workbook_output_path"].set(
                str(suggested.report_workbook_output_path)
            )

        self.status_var.set("Output paths suggested")
        self._set_summary(
            "Output paths suggested\n"
            f"JSON report: {suggested.json_output_path}\n"
            f"Report workbook: {suggested.report_workbook_output_path}"
        )

    def _check_run_fields(self) -> bool:
        inspection = inspect_run_readiness(self._inputs())
        if inspection.is_valid:
            self.status_var.set("Run preflight passed")
        else:
            self.status_var.set("Run preflight failed")
        self._set_summary(format_run_readiness_inspection(inspection))
        return inspection.is_valid

    def _check_workbook(self) -> None:
        try:
            inspection = inspect_workbook_contract(
                self.variables["input_workbook_path"].get()
            )
        except (OSError, PlanningWorkbookError, PlanningWorkbookRunRequestError) as exc:
            self.status_var.set("Workbook check failed")
            self._set_summary(str(exc))
            self._show_error("Workbook check failed", str(exc))
            return

        if inspection.is_valid:
            self.status_var.set("Workbook check passed")
        else:
            self.status_var.set("Workbook check failed")
        self._set_summary(format_workbook_contract_inspection(inspection))

    def _run_workbook(self) -> None:
        if not self._check_run_fields():
            self._show_error("Run preflight failed", self._summary_value())
            return

        try:
            request = build_run_request(self._inputs())
            result = self.run_service(request)
        except PlanningWorkbookValidationError as exc:
            details = _validation_error_text(exc)
            self.status_var.set("Validation failed")
            self._set_summary(details)
            self._show_error("Validation failed", details)
            return
        except (OSError, PlanningWorkbookError, PlanningWorkbookRunRequestError) as exc:
            self.status_var.set("Run failed")
            self._set_summary(str(exc))
            self._show_error("Run failed", str(exc))
            return

        self.status_var.set("Run complete")
        self.last_output_artifacts = output_artifact_paths(result)
        self._set_summary(format_run_summary(result))

    def _show_contract_reference(self) -> None:
        self.status_var.set("Workbook contract")
        self._set_summary(format_workbook_contract_reference())

    def _show_output_artifacts(self) -> None:
        self.status_var.set("Output artifacts")
        self._set_summary(format_output_artifacts(self.last_output_artifacts))

    def _inputs(self) -> PlanningLauncherInputs:
        return PlanningLauncherInputs(
            input_workbook_path=self.variables["input_workbook_path"].get(),
            json_output_path=self.variables["json_output_path"].get(),
            report_workbook_output_path=self.variables[
                "report_workbook_output_path"
            ].get(),
            plan_batch_id=self.variables["plan_batch_id"].get(),
            plan_period=self.variables["plan_period"].get(),
            plan_type=self.variables["plan_type"].get(),
            work_order_import_batch_id=self.variables[
                "work_order_import_batch_id"
            ].get(),
            equipment_snapshot_batch_id=self.variables[
                "equipment_snapshot_batch_id"
            ].get(),
            equipment_snapshot_at=self.variables["equipment_snapshot_at"].get(),
            tbd_import_batch_id=self.variables["tbd_import_batch_id"].get(),
            engine_version=self.variables["engine_version"].get(),
        )

    def _set_summary(self, text: str) -> None:
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state=tk.DISABLED)

    def _summary_value(self) -> str:
        return self.summary_text.get("1.0", tk.END).strip()

    def _show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self.root)


def _blank_to_none(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _required_path(path: str | Path, field_name: str) -> Path:
    if not str(path).strip():
        raise PlanningWorkbookRunRequestError(f"{field_name} is required")
    return Path(path)


def _joined_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "None"


def _validation_error_text(exc: PlanningWorkbookValidationError) -> str:
    lines = [str(exc)]
    for stage, errors in sorted(exc.errors_by_stage.items()):
        for error in errors:
            lines.append(f"{stage}: {error}")
    return "\n".join(lines)


def main() -> None:
    root = tk.Tk()
    PlanningWorkbookLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
