from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from engine.models import (
    Operator,
    OperatorAssignment,
    ProcessBlock,
    ProcessConnection,
    Scenario,
    UNIVERSAL_OPERATOR_BLOCK_TYPES,
    operator_can_handle_block,
)
from engine.operator_library import (
    OperatorTemplate,
    default_operator_library_path,
    delete_operator_template,
    load_operator_templates,
    save_operator_templates,
    upsert_operator_template,
)
from engine.scenario_io import load as load_scenario_file
from engine.scenario_io import save as save_scenario_file
from engine.simulation import BlockResult, BundleRecord, SimulationResult, simulate


@dataclass(frozen=True)
class BlockType:
    label: str
    color: str
    icon: str
    default_process_time_per_ea: float = 30.0
    default_concurrent_capacity: int = 1
    default_input_quantity: int = 10
    default_input_time: float = 0.0
    default_transport_capacity: int = 4
    default_transport_time: float = 3.0


BLOCK_TYPES: dict[str, BlockType] = {
    "INPUT": BlockType("원자재 투입", "#2563eb", "📥", default_input_quantity=10),
    "WORK_WAITING": BlockType("작업대기", "#64748b", "⏳"),
    "PREPROCESS": BlockType("전처리", "#0f766e", "🧰"),
    "BENDING": BlockType("구부", "#d97706", "🔧"),
    "DRAWING": BlockType("인발", "#7c3aed", "🧵"),
    "CUTTING": BlockType("절단", "#f59e0b", "✂️", 45),
    "HEAT": BlockType("열처리", "#dc2626", "🔥", 120),
    "CORRECTION": BlockType("교정", "#db2777", "⚙️"),
    "POSTPROCESS": BlockType("후처리", "#0891b2", "🧼"),
    "INSPECTION": BlockType("검사", "#4f46e5", "🔍"),
    "PACKING": BlockType("포장", "#16a34a", "📦"),
    "HOIST": BlockType("호이스트", "#0f766e", "🏗️", default_transport_capacity=4),
    "FREE": BlockType("Free Block", "#6b7280", "📋", 30),
}

OPERATOR_QUALIFICATION_TYPES = tuple(
    block_type
    for block_type in BLOCK_TYPES
    if block_type not in UNIVERSAL_OPERATOR_BLOCK_TYPES
)


def format_flow_diagram(
    process_flow: list[int],
    connections: list[ProcessConnection],
    block_label: Callable[[int], str],
    block_icon: Callable[[int], str] | None = None,
) -> str:
    flow_ids = set(process_flow)
    icon_for = block_icon or (lambda _block_id: "")

    def label(block_id: int) -> str:
        return f"{icon_for(block_id)}{block_label(block_id)}"

    visible_connections = [
        connection
        for connection in connections
        if connection.from_block in flow_ids and connection.to_block in flow_ids
    ]
    if visible_connections:
        return "\n".join(
            f"{label(connection.from_block)} -> {label(connection.to_block)}"
            for connection in visible_connections
        )

    return "\n".join(label(block_id) for block_id in process_flow)


def format_qualification_summary(qualified_process_types: set[str]) -> str:
    return f"자격 {len(qualified_process_types)}개"


def format_operator_qualification_summary(operator: Operator) -> str:
    return format_qualification_summary(operator.qualified_process_types)


TOKEN_STATE_LABELS = {
    "not_arrived": "도착 전",
    "waiting": "대기 중",
    "processing": "처리 중",
    "complete": "완료",
}

PRODUCT_TOKEN_COLORS = [
    "#2563eb",
    "#16a34a",
    "#d97706",
    "#7c3aed",
    "#dc2626",
    "#0891b2",
    "#be185d",
    "#4d7c0f",
]


@dataclass
class PlaybackState:
    current_time: float = 0.0
    is_playing: bool = False
    speed_multiplier: float = 1.0
    selected_token_id: str | None = None
    is_stale: bool = False
    is_compact: bool = False


@dataclass(frozen=True)
class BundleTokenState:
    token_id: str
    bundle_id: int | None
    block_id: int
    product_name: str
    material_name: str
    quantity: int
    state: str
    arrival_time: float
    start_time: float
    completion_time: float
    progress: float
    bundle_count: int = 1
    is_aggregate: bool = False
    source_token_ids: tuple[str, ...] = ()


class AnimationController:
    target_playback_seconds = 30.0
    compact_threshold = 24

    def __init__(self) -> None:
        self.state = PlaybackState()

    def set_result(self, result: SimulationResult) -> None:
        self.state.current_time = min(self.state.current_time, result.total_time)
        self.state.is_playing = False
        self.state.selected_token_id = None
        self.state.is_stale = False
        self.state.is_compact = False

    def mark_structure_changed(self) -> None:
        self.state.is_playing = False
        self.state.is_stale = True

    def mark_layout_changed(self) -> None:
        self.state.is_playing = False

    def clear(self) -> None:
        self.state = PlaybackState()

    def set_time(self, current_time: float, total_time: float) -> None:
        self.state.current_time = max(0.0, min(float(current_time), total_time))

    def playback_minutes_per_second(self, total_time: float) -> float:
        if total_time <= 0:
            return 0.0
        return (total_time / self.target_playback_seconds) * self.state.speed_multiplier

    def advance(self, total_time: float, elapsed_ms: int) -> bool:
        step = self.playback_minutes_per_second(total_time) * (elapsed_ms / 1000)
        self.set_time(self.state.current_time + step, total_time)
        if self.state.current_time >= total_time:
            self.state.is_playing = False
            return True
        return False

    def token_states(
        self,
        result: SimulationResult,
        include_not_arrived: bool = False,
    ) -> list[BundleTokenState]:
        records_by_bundle = self._records_by_bundle(result)
        sink_ids = self._sink_block_ids(result)
        tokens: list[BundleTokenState] = []

        for bundle_id in sorted(records_by_bundle):
            records = records_by_bundle[bundle_id]
            token = self._token_for_bundle(records, sink_ids)
            if include_not_arrived or token.state != "not_arrived":
                tokens.append(token)

        return tokens

    def display_tokens(self, result: SimulationResult) -> list[BundleTokenState]:
        active_tokens = self.token_states(result)
        if len(active_tokens) <= self.compact_threshold:
            self.state.is_compact = False
            return active_tokens

        self.state.is_compact = True
        return self._aggregate_tokens(active_tokens)

    def current_summary(self, tokens: list[BundleTokenState]) -> dict[str, int]:
        summary = {state: 0 for state in TOKEN_STATE_LABELS}
        for token in tokens:
            summary[token.state] = summary.get(token.state, 0) + token.bundle_count
        return summary

    def selected_token(
        self,
        result: SimulationResult,
    ) -> BundleTokenState | None:
        selected_id = self.state.selected_token_id
        if not selected_id:
            return None

        display_tokens = self.display_tokens(result)
        for token in display_tokens:
            if token.token_id == selected_id:
                return token

        for token in self.token_states(result, include_not_arrived=True):
            if token.token_id == selected_id:
                return token
        return None

    def product_color(self, product_name: str) -> str:
        index = sum(ord(char) for char in product_name) % len(PRODUCT_TOKEN_COLORS)
        return PRODUCT_TOKEN_COLORS[index]

    def _records_by_bundle(
        self,
        result: SimulationResult,
    ) -> dict[int, list[BundleRecord]]:
        records_by_bundle: dict[int, list[BundleRecord]] = {}
        for block_result in result.timeline:
            for bundle in block_result.bundles:
                records_by_bundle.setdefault(bundle.bundle_id, []).append(bundle)

        for records in records_by_bundle.values():
            records.sort(
                key=lambda bundle: (
                    bundle.arrival_time,
                    bundle.start_time,
                    bundle.completion_time,
                    bundle.block_id,
                )
            )
        return records_by_bundle

    def _sink_block_ids(self, result: SimulationResult) -> set[int]:
        block_ids = {item.block_id for item in result.timeline}
        parent_ids = {
            connection.from_block
            for connection in self._active_connections
            if connection.from_block in block_ids
        }
        return block_ids - parent_ids

    @property
    def _active_connections(self) -> list[ProcessConnection]:
        return getattr(self, "connections", [])

    def set_connections(self, connections: list[ProcessConnection]) -> None:
        self.connections = connections

    def _token_for_bundle(
        self,
        records: list[BundleRecord],
        sink_ids: set[int],
    ) -> BundleTokenState:
        current_time = self.state.current_time
        first = records[0]

        if current_time < first.arrival_time:
            return self._build_token(first, "not_arrived", 0.0)

        for record in records:
            if current_time < record.arrival_time:
                return self._build_token(record, "not_arrived", 0.0)
            if current_time < record.start_time:
                return self._build_token(record, "waiting", 0.0)
            if current_time < record.completion_time:
                progress = self._progress(current_time, record.start_time, record.completion_time)
                return self._build_token(record, "processing", progress)

        last = records[-1]
        if last.block_id in sink_ids:
            return self._build_token(last, "complete", 1.0)
        return self._build_token(last, "not_arrived", 0.0)

    def _build_token(
        self,
        record: BundleRecord,
        state: str,
        progress: float,
    ) -> BundleTokenState:
        return BundleTokenState(
            token_id=f"bundle:{record.bundle_id}",
            bundle_id=record.bundle_id,
            block_id=record.block_id,
            product_name=record.product_name,
            material_name=record.material_name,
            quantity=record.quantity,
            state=state,
            arrival_time=record.arrival_time,
            start_time=record.start_time,
            completion_time=record.completion_time,
            progress=progress,
            source_token_ids=(f"bundle:{record.bundle_id}",),
        )

    def _aggregate_tokens(
        self,
        tokens: list[BundleTokenState],
    ) -> list[BundleTokenState]:
        grouped: dict[tuple[int, str, str, str], list[BundleTokenState]] = {}
        for token in tokens:
            key = (
                token.block_id,
                token.state,
                token.product_name,
                token.material_name,
            )
            grouped.setdefault(key, []).append(token)

        aggregates: list[BundleTokenState] = []
        for key, group in sorted(grouped.items()):
            block_id, state, product_name, material_name = key
            source_ids = tuple(token.token_id for token in group)
            aggregates.append(
                BundleTokenState(
                    token_id=(
                        f"aggregate:{block_id}:{state}:"
                        f"{product_name}:{material_name}"
                    ),
                    bundle_id=None,
                    block_id=block_id,
                    product_name=product_name,
                    material_name=material_name,
                    quantity=sum(token.quantity for token in group),
                    state=state,
                    arrival_time=min(token.arrival_time for token in group),
                    start_time=min(token.start_time for token in group),
                    completion_time=max(token.completion_time for token in group),
                    progress=sum(token.progress for token in group) / len(group),
                    bundle_count=sum(token.bundle_count for token in group),
                    is_aggregate=True,
                    source_token_ids=source_ids,
                )
            )
        return aggregates

    def _progress(self, current_time: float, start_time: float, completion_time: float) -> float:
        if completion_time <= start_time:
            return 1.0
        return max(0.0, min(1.0, (current_time - start_time) / (completion_time - start_time)))


class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("공정 시뮬레이션 프로그램 v1.2")
        self.root.geometry("1600x900")
        self.root.minsize(1200, 700)
        self.root.configure(bg="#e8edf3")

        style = ttk.Style()
        style.theme_use("clam")
        self._configure_style(style)

        self.scenario = Scenario()
        self.operator_library_path = default_operator_library_path()
        self.operator_templates = self.load_operator_library()
        self.last_result: SimulationResult | None = None
        self.animation = AnimationController()
        self._animation_after_id: str | None = None
        self.connection_start_kind: str | None = None
        self.connection_start_id: int | None = None
        self.status_var = tk.StringVar(value="준비 완료")

        self._create_widgets()
        self.root.bind("<Escape>", self.handle_escape)

    def _configure_style(self, style: ttk.Style) -> None:
        style.configure(
            ".",
            background="#e8edf3",
            foreground="#1f2937",
            font=("Arial", 10),
        )
        style.configure("App.TFrame", background="#e8edf3")
        style.configure("Toolbar.TFrame", background="#1f2937", relief=tk.FLAT)
        style.configure(
            "ToolbarTitle.TLabel",
            background="#1f2937",
            foreground="#f8fafc",
            font=("Arial", 16, "bold"),
        )
        style.configure(
            "Toolbar.TButton",
            background="#334155",
            foreground="#f8fafc",
            bordercolor="#475569",
            focusthickness=1,
            focuscolor="#93c5fd",
            padding=(10, 6),
        )
        style.map(
            "Toolbar.TButton",
            background=[("active", "#475569"), ("pressed", "#0f172a")],
            foreground=[("disabled", "#94a3b8")],
        )
        style.configure(
            "Panel.TLabelframe",
            background="#f8fafc",
            bordercolor="#cbd5e1",
            relief=tk.GROOVE,
        )
        style.configure(
            "Panel.TLabelframe.Label",
            background="#e8edf3",
            foreground="#0f172a",
            font=("Arial", 11, "bold"),
        )
        style.configure("Panel.TFrame", background="#f8fafc")
        style.configure("Panel.TLabel", background="#f8fafc", foreground="#334155")
        style.configure("Playback.TFrame", background="#f8fafc")
        style.configure("Status.TLabel", background="#dbe3ec", foreground="#334155")
        style.configure("TNotebook", background="#f8fafc", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(12, 6),
            background="#e2e8f0",
            foreground="#475569",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff"), ("active", "#f1f5f9")],
            foreground=[("selected", "#0f172a")],
        )

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self.root, style="App.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(main_frame, style="Toolbar.TFrame", padding=(12, 8))
        toolbar.pack(fill=tk.X)
        ttk.Label(
            toolbar,
            text="공정 시뮬레이션 프로그램 v1.2",
            style="ToolbarTitle.TLabel",
        ).pack(side=tk.LEFT, padx=10)

        button_frame = ttk.Frame(toolbar, style="Toolbar.TFrame")
        button_frame.pack(side=tk.RIGHT, padx=10)
        for label, command in (
            ("시뮬레이션 실행", self.run_simulation),
            ("저장", self.save_scenario),
            ("불러오기", self.load_scenario),
            ("초기화", self.clear_all),
        ):
            ttk.Button(
                button_frame,
                text=label,
                command=command,
                style="Toolbar.TButton",
            ).pack(side=tk.LEFT, padx=3)

        content_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(content_paned, width=205, style="App.TFrame")
        center_frame = ttk.Frame(content_paned, style="App.TFrame")
        right_frame = ttk.Frame(content_paned, width=420, style="App.TFrame")
        content_paned.add(left_frame, weight=0)
        content_paned.add(center_frame, weight=3)
        content_paned.add(right_frame, weight=1)

        self.palette_view = PaletteView(left_frame, self)
        self.canvas_view = CanvasView(center_frame, self)
        self.result_view = ResultView(right_frame, self)

        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            anchor=tk.W,
            style="Status.TLabel",
            padding=(10, 4),
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def run(self) -> None:
        self.root.mainloop()

    def load_operator_library(self) -> list[OperatorTemplate]:
        try:
            return load_operator_templates(self.operator_library_path)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            messagebox.showwarning(
                "작업자 보관함 오류",
                f"작업자 보관함을 불러올 수 없습니다:\n{exc}",
            )
            return []

    def save_operator_library(self) -> bool:
        try:
            save_operator_templates(
                self.operator_templates,
                self.operator_library_path,
            )
        except OSError as exc:
            messagebox.showerror(
                "작업자 보관함 오류",
                f"작업자 보관함 저장 중 오류가 발생했습니다:\n{exc}",
            )
            return False
        return True

    def save_operator_to_library(self, operator_id: int) -> None:
        operator = self.find_operator(operator_id)
        if operator is None:
            return

        template, created = upsert_operator_template(
            self.operator_templates,
            operator.name,
            operator.qualified_process_types,
        )
        if not self.save_operator_library():
            return

        self.palette_view.refresh_operator_templates()
        action = "저장" if created else "갱신"
        self.status_var.set(f"자주 쓰는 작업자 {action}: {template.name}")

    def load_operator_template(self, template_id: int) -> None:
        template = self.find_operator_template(template_id)
        if template is None:
            return

        operator = self.scenario.add_operator(
            name=template.name,
            x=320,
            y=140 + len(self.scenario.operators) * 90,
            qualified_process_types=set(template.qualified_process_types),
        )
        self.mark_structure_changed(
            "작업자가 추가되어 시뮬레이션 재실행이 필요합니다."
        )
        self.canvas_view.redraw()
        self.status_var.set(f"작업자 불러오기 완료: {operator.name}")

    def delete_operator_template(self, template_id: int) -> None:
        template = self.find_operator_template(template_id)
        if template is None:
            return
        if not messagebox.askyesno(
            "자주 쓰는 작업자 삭제",
            f"{template.name} 작업자 템플릿을 삭제하시겠습니까?",
        ):
            return

        deleted = delete_operator_template(self.operator_templates, template_id)
        if deleted is None or not self.save_operator_library():
            return

        self.palette_view.refresh_operator_templates()
        self.status_var.set(f"자주 쓰는 작업자 삭제됨: {deleted.name}")

    def find_operator_template(self, template_id: int) -> OperatorTemplate | None:
        return next(
            (
                template
                for template in self.operator_templates
                if template.id == template_id
            ),
            None,
        )

    def add_block(self, block_type: str) -> None:
        block_type_info = BLOCK_TYPES[block_type]
        custom_name = ""
        if block_type == "FREE":
            custom_name = self.prompt_free_block_name()
            if not custom_name:
                return

        block = self.scenario.add_block(
            block_type=block_type,
            x=150,
            y=100 + len(self.scenario.blocks) * 100,
            process_time_per_ea=block_type_info.default_process_time_per_ea,
            concurrent_capacity=block_type_info.default_concurrent_capacity,
            input_quantity=block_type_info.default_input_quantity,
            input_time=block_type_info.default_input_time,
            transport_capacity=block_type_info.default_transport_capacity,
            transport_time=block_type_info.default_transport_time,
            custom_name=custom_name,
        )
        self.mark_structure_changed("블록이 변경되어 시뮬레이션 재실행이 필요합니다.")
        self.canvas_view.redraw()
        self.status_var.set(f"{self.block_display_name(block)} 블록이 추가되었습니다.")

    def prompt_free_block_name(self) -> str:
        dialog = tk.Toplevel(self.root)
        dialog.title("Free Block 이름 입력")
        dialog.geometry("400x180")
        dialog.configure(bg="#f8fafc")
        dialog.transient(self.root)
        dialog.grab_set()

        result = {"name": ""}
        name_var = tk.StringVar(value="사용자 정의 블록")

        ttk.Label(
            dialog,
            text="블록 이름을 입력하세요:",
            font=("Arial", 11, "bold"),
        ).pack(pady=20)
        entry = ttk.Entry(dialog, textvariable=name_var, width=30, font=("Arial", 10))
        entry.pack(pady=10)
        entry.focus()

        def save_name() -> None:
            result["name"] = name_var.get().strip()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="확인", command=save_name).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="취소", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )
        entry.bind("<Return>", lambda _event: save_name())

        dialog.wait_window()
        return result["name"]

    def add_operator(self) -> None:
        settings = self.prompt_operator_settings()
        if settings is None:
            return

        name, qualified_process_types = settings
        operator = self.scenario.add_operator(
            name=name,
            x=320,
            y=140 + len(self.scenario.operators) * 90,
            qualified_process_types=qualified_process_types,
        )
        self.mark_structure_changed(
            "Operator changed; rerun simulation to refresh results."
        )
        self.canvas_view.redraw()
        self.status_var.set(f"Operator added: {operator.name}")

    def prompt_operator_settings(
        self,
        operator: Operator | None = None,
    ) -> tuple[str, set[str]] | None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Operator Settings")
        dialog.geometry("420x520")
        dialog.configure(bg="#f8fafc")
        dialog.transient(self.root)
        dialog.grab_set()

        result: dict[str, tuple[str, set[str]] | None] = {"settings": None}
        name_var = tk.StringVar(value=operator.name if operator else "Operator")
        selected_types = set(operator.qualified_process_types if operator else ())
        qualification_vars = {
            block_type: tk.BooleanVar(value=block_type in selected_types)
            for block_type in OPERATOR_QUALIFICATION_TYPES
        }

        ttk.Label(
            dialog,
            text="Operator",
            font=("Arial", 14, "bold"),
        ).pack(fill=tk.X, padx=20, pady=(18, 8))

        form_frame = ttk.Frame(dialog, padding=(22, 12), style="Panel.TFrame")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=6)
        name_entry = ttk.Entry(form_frame, textvariable=name_var, width=24)
        name_entry.grid(row=0, column=1, sticky="ew", pady=6)
        name_entry.focus()

        ttk.Label(
            form_frame,
            text="Qualified process types",
            font=("Arial", 10, "bold"),
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(12, 4))

        for row, block_type in enumerate(OPERATOR_QUALIFICATION_TYPES, start=2):
            block_type_info = BLOCK_TYPES[block_type]
            ttk.Checkbutton(
                form_frame,
                text=f"{block_type_info.icon} {block_type_info.label}",
                variable=qualification_vars[block_type],
            ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

        def save_operator_settings() -> None:
            name = name_var.get().strip()
            qualifications = {
                block_type
                for block_type, value in qualification_vars.items()
                if value.get()
            }
            if not name:
                messagebox.showerror("Input Error", "Operator name is required.")
                return
            if not qualifications:
                messagebox.showerror(
                    "Input Error",
                    "Select at least one qualified process type.",
                )
                return
            if operator is not None and not self._operator_edit_keeps_assignments(
                operator,
                qualifications,
            ):
                messagebox.showwarning(
                    "Operator Assignment",
                    "Current assignments require qualifications that were unchecked.",
                )
                return

            result["settings"] = (name, qualifications)
            dialog.destroy()

        button_frame = ttk.Frame(dialog, padding=(16, 0, 16, 14))
        button_frame.pack(fill=tk.X)
        ttk.Button(
            button_frame,
            text="Save",
            command=save_operator_settings,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT,
            padx=5,
        )
        name_entry.bind("<Return>", lambda _event: save_operator_settings())

        dialog.wait_window()
        return result["settings"]

    def _operator_edit_keeps_assignments(
        self,
        operator: Operator,
        qualifications: set[str],
    ) -> bool:
        probe = Operator(
            id=operator.id,
            name=operator.name,
            x=operator.x,
            y=operator.y,
            qualified_process_types=qualifications,
        )
        for assignment in self.scenario.operator_assignments:
            if assignment.operator_id != operator.id:
                continue
            block = self.find_block(assignment.block_id)
            if block is not None and not operator_can_handle_block(probe, block):
                return False
        return True

    def edit_operator(self, operator_id: int) -> None:
        operator = self.find_operator(operator_id)
        if operator is None:
            return
        settings = self.prompt_operator_settings(operator)
        if settings is None:
            return

        operator.name, operator.qualified_process_types = settings
        self.mark_structure_changed(
            "Operator changed; rerun simulation to refresh results."
        )
        self.canvas_view.redraw()
        self.status_var.set(f"Operator updated: {operator.name}")

    def edit_block_parameters(self, block_id: int) -> None:
        block = self.find_block(block_id)
        if not block:
            return

        block_type_info = BLOCK_TYPES[block.type]
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{self.block_display_name(block)} 설정")
        dialog.geometry("460x380")
        dialog.configure(bg="#f8fafc")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=f"{block_type_info.icon} {self.block_display_name(block)}",
            font=("Arial", 14, "bold"),
        ).pack(fill=tk.X, padx=20, pady=12)

        form_frame = ttk.Frame(dialog, padding=(22, 14), style="Panel.TFrame")
        form_frame.pack(fill=tk.BOTH, expand=True)
        form_frame.columnconfigure(1, weight=1)

        row = 0
        name_var = tk.StringVar(value=block.custom_name)
        if block.type == "FREE":
            ttk.Label(form_frame, text="블록 이름:").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=name_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
            row += 1

        product_name_var = tk.StringVar(value=block.product_name)
        material_name_var = tk.StringVar(value=block.material_name)
        input_quantity_var = tk.IntVar(value=block.input_quantity)
        input_time_var = tk.DoubleVar(value=block.input_time)
        process_time_var = tk.DoubleVar(value=block.process_time_per_ea)
        concurrent_capacity_var = tk.IntVar(value=block.concurrent_capacity)
        transport_capacity_var = tk.IntVar(value=block.transport_capacity)
        transport_time_var = tk.DoubleVar(value=block.transport_time)

        if block.type == "INPUT":
            ttk.Label(form_frame, text="제품명:").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=product_name_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
            row += 1

            ttk.Label(form_frame, text="원자재명:").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=material_name_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
            row += 1

            ttk.Label(form_frame, text="투입 원자재 수(EA):").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=input_quantity_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
            row += 1

            ttk.Label(form_frame, text="투입 시간(분):").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=input_time_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
        elif block.type == "HOIST":
            ttk.Label(form_frame, text="1회 운반 수량(EA):").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=transport_capacity_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
            row += 1

            ttk.Label(form_frame, text="1회 이동 시간(분):").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=transport_time_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
        else:
            ttk.Label(form_frame, text="처리 시간(분/EA):").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=process_time_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )
            row += 1

            ttk.Label(form_frame, text="동시 가공 수량(EA):").grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(form_frame, textvariable=concurrent_capacity_var, width=22).grid(
                row=row, column=1, sticky="ew", pady=5
            )

        def save_params() -> None:
            try:
                input_quantity = int(input_quantity_var.get())
                input_time = float(input_time_var.get())
                process_time = float(process_time_var.get())
                concurrent_capacity = int(concurrent_capacity_var.get())
                transport_capacity = int(transport_capacity_var.get())
                transport_time = float(transport_time_var.get())
            except tk.TclError:
                messagebox.showerror(
                    "입력 오류",
                    "수량과 시간은 숫자로 입력해주세요.",
                )
                return

            if block.type == "INPUT":
                product_name = product_name_var.get().strip()
                material_name = material_name_var.get().strip()
                if not product_name:
                    messagebox.showerror(
                        "입력 오류",
                        "제품명을 입력해주세요.",
                    )
                    return
                if not material_name:
                    messagebox.showerror("입력 오류", "원자재명을 입력해주세요.")
                    return
                if input_quantity < 0 or input_time < 0:
                    messagebox.showerror(
                        "입력 오류",
                        "투입 원자재 수와 투입 시간은 0 이상이어야 합니다.",
                    )
                    return
                block.product_name = product_name
                block.material_name = material_name
                block.input_quantity = input_quantity
                block.input_time = input_time
            elif block.type == "HOIST":
                if transport_capacity <= 0 or transport_time <= 0:
                    messagebox.showerror(
                        "입력 오류",
                        "1회 운반 수량은 1 이상, 1회 이동 시간은 0보다 커야 합니다.",
                    )
                    return
                block.transport_capacity = transport_capacity
                block.transport_time = transport_time
            elif process_time <= 0 or concurrent_capacity <= 0:
                messagebox.showerror(
                    "입력 오류",
                    "처리 시간은 0보다 커야 하고 동시 가공 수량은 1 이상이어야 합니다.",
                )
                return
            else:
                block.process_time_per_ea = process_time
                block.concurrent_capacity = concurrent_capacity

            if block.type == "FREE":
                block.custom_name = name_var.get().strip()
            self.mark_structure_changed("파라미터가 변경되어 시뮬레이션 재실행이 필요합니다.")
            self.canvas_view.redraw()
            dialog.destroy()
            self.status_var.set("파라미터가 저장되었습니다.")

        button_frame = ttk.Frame(dialog, padding=10)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="저장", command=save_params).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="취소", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )

    def move_block(self, block_id: int, dx: float, dy: float) -> None:
        block = self.find_block(block_id)
        if not block:
            return
        block.x += dx
        block.y += dy
        self.animation.mark_layout_changed()
        self.canvas_view.redraw()
        self.canvas_view.update_playback_controls()

    def move_operator(self, operator_id: int, dx: float, dy: float) -> None:
        operator = self.find_operator(operator_id)
        if operator is None:
            return
        operator.x += dx
        operator.y += dy
        self.animation.mark_layout_changed()
        self.canvas_view.redraw()
        self.canvas_view.update_playback_controls()

    def start_or_finish_connection(self, block_id: int) -> None:
        self.start_or_finish_connection_target("block", block_id)

    def start_or_finish_operator_connection(self, operator_id: int) -> None:
        self.start_or_finish_connection_target("operator", operator_id)

    def start_or_finish_connection_target(self, kind: str, target_id: int) -> None:
        if self.connection_start_id is None:
            self.connection_start_kind = kind
            self.connection_start_id = target_id
            self.canvas_view.show_connection_start(kind, target_id)
            self.status_var.set(
                f"{self.target_display_name(kind, target_id)}에서 연결을 시작합니다. "
                "대상을 Shift+클릭하세요."
            )
            return

        start_kind = self.connection_start_kind
        start_id = self.connection_start_id
        if start_kind is None:
            self.end_connection_mode()
            return

        try:
            if start_kind == "block" and kind == "block":
                self.scenario.add_connection(start_id, target_id)
            elif start_kind == "operator" and kind == "block":
                self.scenario.add_operator_assignment(start_id, target_id)
            elif start_kind == "block" and kind == "operator":
                self.scenario.add_operator_assignment(target_id, start_id)
            else:
                raise ValueError("작업자끼리는 연결할 수 없습니다.")
        except ValueError as exc:
            messagebox.showwarning("연결 오류", f"연결을 만들 수 없습니다:\n{exc}")
            self.status_var.set("연결을 생성하지 못했습니다.")
        else:
            self.mark_structure_changed("연결이 변경되어 시뮬레이션 재실행이 필요합니다.")
            self.canvas_view.redraw()
            self.status_var.set("연결이 완료되었습니다.")
        finally:
            self.end_connection_mode()

    def cancel_connection(self, _event: object | None = None) -> None:
        if self.connection_start_id is None:
            return
        start_kind = self.connection_start_kind or "block"
        start_name = self.target_display_name(start_kind, self.connection_start_id)
        self.end_connection_mode()
        self.status_var.set(f"{start_name}에서 시작한 연결이 취소되었습니다.")

    def handle_escape(self, event: object | None = None) -> None:
        if self.connection_start_id is not None:
            self.cancel_connection(event)
            return
        self.select_animation_token(None)

    def end_connection_mode(self) -> None:
        self.connection_start_kind = None
        self.connection_start_id = None
        self.canvas_view.end_connection_mode()

    def delete_block(self, block_id: int) -> None:
        block = self.find_block(block_id)
        if not block:
            return
        if not messagebox.askyesno(
            "삭제 확인",
            f"{self.block_display_name(block)} 블록을 삭제하시겠습니까?",
        ):
            return
        self.scenario.delete_block(block_id)
        self.mark_structure_changed("블록이 삭제되어 시뮬레이션 재실행이 필요합니다.")
        self.canvas_view.redraw()
        self.status_var.set("블록이 삭제되었습니다.")

    def delete_operator(self, operator_id: int) -> None:
        operator = self.find_operator(operator_id)
        if operator is None:
            return
        if not messagebox.askyesno(
            "삭제 확인",
            f"{operator.name} 작업자를 삭제하시겠습니까?",
        ):
            return
        self.scenario.delete_operator(operator_id)
        self.mark_structure_changed("작업자가 삭제되어 시뮬레이션 재실행이 필요합니다.")
        self.canvas_view.redraw()
        self.status_var.set("작업자가 삭제되었습니다.")

    def delete_connection(self, connection_id: int) -> None:
        connection = self.find_connection(connection_id)
        if not connection:
            return

        from_block = self.find_block(connection.from_block)
        to_block = self.find_block(connection.to_block)
        from_name = self.block_display_name(from_block) if from_block else "Unknown"
        to_name = self.block_display_name(to_block) if to_block else "Unknown"

        if not messagebox.askyesno(
            "연결 삭제",
            f"{from_name} → {to_name}\n이 연결을 삭제하시겠습니까?",
        ):
            return
        self.scenario.delete_connection(connection_id)
        self.mark_structure_changed("연결이 삭제되어 시뮬레이션 재실행이 필요합니다.")
        self.canvas_view.redraw()
        self.status_var.set("연결이 삭제되었습니다.")

    def delete_operator_assignment(self, assignment_id: int) -> None:
        assignment = self.find_operator_assignment(assignment_id)
        if assignment is None:
            return

        operator = self.find_operator(assignment.operator_id)
        block = self.find_block(assignment.block_id)
        operator_name = operator.name if operator else "Unknown"
        block_name = self.block_display_name(block) if block else "Unknown"

        if not messagebox.askyesno(
            "작업자 연결 삭제",
            f"{operator_name} ↔ {block_name}\n이 작업자 연결을 삭제하시겠습니까?",
        ):
            return
        self.scenario.delete_operator_assignment(assignment_id)
        self.mark_structure_changed("작업자 연결이 삭제되어 시뮬레이션 재실행이 필요합니다.")
        self.canvas_view.redraw()
        self.status_var.set("작업자 연결이 삭제되었습니다.")

    def run_simulation(self) -> None:
        if not self.scenario.blocks:
            messagebox.showwarning("경고", "공정 블록을 추가해주세요.")
            return

        try:
            result = simulate(
                self.scenario.blocks,
                self.scenario.connections,
                self.scenario.operators,
                self.scenario.operator_assignments,
            )
        except ValueError as exc:
            messagebox.showerror("시뮬레이션 오류", str(exc))
            return

        if not result.timeline:
            messagebox.showerror("오류", "시뮬레이션 결과가 없습니다.")
            return

        self.last_result = result
        self.animation.set_connections(self.scenario.connections)
        self.animation.set_result(result)
        self.result_view.display(result)
        self.refresh_animation()
        self.status_var.set(f"시뮬레이션 완료 - 총 리드타임: {result.total_time:.1f}분")

    def save_scenario(self) -> None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            title="시나리오 저장",
        )
        if not filename:
            return

        try:
            save_scenario_file(self.scenario, filename)
        except OSError as exc:
            messagebox.showerror("저장 오류", f"저장 중 오류가 발생했습니다:\n{exc}")
            return

        messagebox.showinfo("저장 완료", f"시나리오가 저장되었습니다:\n{filename}")
        self.status_var.set(f"시나리오 저장됨: {filename}")

    def load_scenario(self) -> None:
        filename = filedialog.askopenfilename(
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            title="시나리오 불러오기",
        )
        if not filename:
            return

        try:
            self.scenario = load_scenario_file(filename)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            messagebox.showerror("불러오기 오류", f"불러오기 중 오류가 발생했습니다:\n{exc}")
            return

        self.last_result = None
        self.connection_start_kind = None
        self.connection_start_id = None
        self.animation.clear()
        self.canvas_view.redraw()
        self.result_view.clear()
        messagebox.showinfo("불러오기 완료", "시나리오가 불러와졌습니다.")
        self.mark_structure_changed("불러온 시나리오는 시뮬레이션 실행이 필요합니다.")
        self.status_var.set(f"시나리오 불러옴: {filename}")

    def clear_all(self) -> None:
        if not messagebox.askyesno("초기화 확인", "모든 블록과 연결을 삭제하시겠습니까?"):
            return
        self.scenario = Scenario()
        self.last_result = None
        self.connection_start_kind = None
        self.connection_start_id = None
        self.animation.clear()
        self.canvas_view.redraw()
        self.result_view.clear()
        self.mark_structure_changed("초기화되어 시뮬레이션 실행이 필요합니다.")
        self.status_var.set("초기화 완료")

    def mark_structure_changed(self, message: str) -> None:
        if self.last_result is not None:
            self.animation.mark_structure_changed()
        else:
            self.animation.state.is_playing = False
            self.animation.state.is_stale = True
        self.stop_animation_timer()
        if hasattr(self, "canvas_view"):
            self.canvas_view.update_playback_controls()
        if hasattr(self, "result_view"):
            self.result_view.set_stale(self.animation.state.is_stale)
        if message:
            self.status_var.set(message)

    def toggle_playback(self) -> None:
        if self.last_result is None:
            self.status_var.set("먼저 시뮬레이션을 실행해주세요.")
            return
        if self.animation.state.is_stale:
            self.status_var.set("결과가 오래되었습니다. 시뮬레이션을 다시 실행해주세요.")
            return

        if self.animation.state.is_playing:
            self.animation.state.is_playing = False
            self.stop_animation_timer()
        else:
            if self.animation.state.current_time >= self.last_result.total_time:
                self.animation.set_time(0, self.last_result.total_time)
            self.animation.state.is_playing = True
            self.schedule_animation_tick()
        self.refresh_animation()

    def stop_playback(self) -> None:
        self.animation.state.is_playing = False
        self.stop_animation_timer()
        total_time = self.last_result.total_time if self.last_result else 0
        self.animation.set_time(0, total_time)
        self.refresh_animation()

    def seek_playhead(self, current_time: float) -> None:
        if self.last_result is None:
            return
        self.animation.state.is_playing = False
        self.stop_animation_timer()
        self.animation.set_time(current_time, self.last_result.total_time)
        self.refresh_animation()

    def set_playback_speed(self, speed_text: str) -> None:
        try:
            self.animation.state.speed_multiplier = float(speed_text.rstrip("x"))
        except ValueError:
            self.animation.state.speed_multiplier = 1.0
        self.canvas_view.update_playback_controls()

    def schedule_animation_tick(self) -> None:
        self.stop_animation_timer()
        self._animation_after_id = self.root.after(100, self.animation_tick)

    def stop_animation_timer(self) -> None:
        if self._animation_after_id is None:
            return
        self.root.after_cancel(self._animation_after_id)
        self._animation_after_id = None

    def animation_tick(self) -> None:
        self._animation_after_id = None
        if not self.last_result or not self.animation.state.is_playing:
            return
        self.animation.advance(self.last_result.total_time, elapsed_ms=100)
        self.refresh_animation()
        if self.animation.state.is_playing:
            self.schedule_animation_tick()

    def select_animation_token(self, token_id: str | None) -> None:
        self.animation.state.selected_token_id = token_id
        self.refresh_animation()

    def refresh_animation(self) -> None:
        if hasattr(self, "canvas_view"):
            self.canvas_view.redraw()
            self.canvas_view.update_playback_controls()
        if hasattr(self, "result_view"):
            self.result_view.update_animation_panel()

    def animation_display_tokens(self) -> list[BundleTokenState]:
        if self.last_result is None or self.animation.state.is_stale:
            self.animation.state.is_compact = False
            return []
        self.animation.set_connections(self.scenario.connections)
        return self.animation.display_tokens(self.last_result)

    def block_display_name(self, block: ProcessBlock | None) -> str:
        if block is None:
            return "Unknown"
        if block.type == "INPUT" and (block.product_name or block.material_name):
            return (
                f"{BLOCK_TYPES[block.type].label}"
                f"({block.product_name}/{block.material_name})"
            )
        if block.type == "FREE" and block.custom_name:
            return block.custom_name
        return BLOCK_TYPES[block.type].label

    def operator_display_name(self, operator: Operator | None) -> str:
        if operator is None:
            return "Unknown"
        return operator.name

    def target_display_name(self, kind: str, target_id: int) -> str:
        if kind == "operator":
            return self.operator_display_name(self.find_operator(target_id))
        return self.block_display_name(self.find_block(target_id))

    def block_result_display_name(self, result: BlockResult) -> str:
        return self.block_display_name(self.find_block(result.block_id))

    def find_block(self, block_id: int) -> ProcessBlock | None:
        return next((block for block in self.scenario.blocks if block.id == block_id), None)

    def find_operator(self, operator_id: int) -> Operator | None:
        return next(
            (
                operator
                for operator in self.scenario.operators
                if operator.id == operator_id
            ),
            None,
        )

    def find_connection(self, connection_id: int) -> ProcessConnection | None:
        return next(
            (
                connection
                for connection in self.scenario.connections
                if connection.id == connection_id
            ),
            None,
        )

    def find_operator_assignment(
        self,
        assignment_id: int,
    ) -> OperatorAssignment | None:
        return next(
            (
                assignment
                for assignment in self.scenario.operator_assignments
                if assignment.id == assignment_id
            ),
            None,
        )

    def bottleneck_reason(self, result: SimulationResult) -> str:
        block = self.find_block(result.bottleneck_id) if result.bottleneck_id else None
        if not block:
            return "병목 없음"
        if block.type == "HOIST":
            return (
                f"이론 처리율 {result.bottleneck_throughput:.3f} EA/분 "
                f"(1회 운반 수량 {block.transport_capacity} EA / "
                f"1회 이동 시간 {block.transport_time:g}분)"
            )
        return (
            f"이론 처리율 {result.bottleneck_throughput:.3f} EA/분 "
            f"(동시 가공 수량 {block.concurrent_capacity} EA / "
            f"처리 시간 {block.process_time_per_ea:g}분/EA)"
        )

    def bottleneck_impact(self, result: SimulationResult) -> str:
        if result.bottleneck_id is None:
            return "없음"
        total_waiting = sum(
            sum(item.waiting_times)
            for item in result.timeline
            if item.block_id != result.bottleneck_id
        )
        return f"다른 공정의 총 대기시간: {total_waiting:.1f}분"


class PaletteView:
    LIST_MAX_WIDTH = 180
    SCROLLBAR_MARGIN = 4

    def __init__(self, parent: tk.Widget, controller: App) -> None:
        self.controller = controller
        self.frame = ttk.LabelFrame(
            parent,
            text="공정 블록 팔레트",
            padding=12,
            style="Panel.TLabelframe",
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=(10, 5), pady=10)
        self._create_widgets()

    def _create_widgets(self) -> None:
        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        process_tab = ttk.Frame(notebook, style="Panel.TFrame")
        operator_tab = ttk.Frame(notebook, style="Panel.TFrame")
        notebook.add(process_tab, text="공정")
        notebook.add(operator_tab, text="작업자")

        palette_body = ttk.Frame(process_tab, style="Panel.TFrame")
        palette_body.pack(side=tk.LEFT, fill=tk.Y, anchor=tk.NW)

        canvas = tk.Canvas(
            palette_body,
            width=self.LIST_MAX_WIDTH,
            bg="#f8fafc",
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(palette_body, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Panel.TFrame")
        buttons: list[tk.Button] = []

        scrollable_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        palette_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def resize_palette(event: tk.Event) -> None:
            width = max(int(event.width), 1)
            canvas.itemconfigure(palette_window, width=width)
            wraplength = max(width - 24, 40)
            for button in buttons:
                button.configure(wraplength=wraplength)

        def resize_container(event: tk.Event) -> None:
            width = self._bounded_list_width(
                int(event.width),
                int(scrollbar.winfo_reqwidth()),
            )
            canvas.configure(width=width)

        def scroll_palette(event: tk.Event) -> str:
            if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
                canvas.yview_scroll(1, "units")
            return "break"

        self.frame.bind("<Configure>", resize_container)
        canvas.bind("<Configure>", resize_palette)
        canvas.bind("<MouseWheel>", scroll_palette)
        canvas.bind("<Button-4>", scroll_palette)
        canvas.bind("<Button-5>", scroll_palette)
        scrollable_frame.bind("<MouseWheel>", scroll_palette)
        scrollable_frame.bind("<Button-4>", scroll_palette)
        scrollable_frame.bind("<Button-5>", scroll_palette)

        for key, block_type in BLOCK_TYPES.items():
            if key == "INPUT":
                detail = f"{block_type.default_input_quantity} EA"
            elif key == "HOIST":
                detail = (
                    f"{block_type.default_transport_capacity} EA/"
                    f"{block_type.default_transport_time:g}분"
                )
            else:
                detail = f"{block_type.default_process_time_per_ea:g}분/EA"
            button = tk.Button(
                scrollable_frame,
                text=f"{block_type.icon} {block_type.label}\n({detail})",
                bg=block_type.color,
                fg=self._text_color_for_button(key),
                font=("Arial", 9, "bold"),
                activebackground=block_type.color,
                activeforeground=self._text_color_for_button(key),
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                cursor="hand2",
                anchor=tk.W,
                justify=tk.LEFT,
                padx=10,
                wraplength=150,
                command=lambda block_key=key: self.controller.add_block(block_key),
            )
            button.bind("<MouseWheel>", scroll_palette)
            button.bind("<Button-4>", scroll_palette)
            button.bind("<Button-5>", scroll_palette)
            button.pack(fill=tk.X, pady=3, ipady=7)
            buttons.append(button)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        operator_body = ttk.Frame(operator_tab, padding=12, style="Panel.TFrame")
        operator_body.pack(fill=tk.BOTH, expand=True)
        ttk.Button(
            operator_body,
            text="작업자 추가",
            command=self.controller.add_operator,
        ).pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            operator_body,
            text="자주 쓰는 작업자",
            style="Panel.TLabel",
            font=("Arial", 10, "bold"),
        ).pack(anchor=tk.W, pady=(2, 6))
        self.operator_list_frame = ttk.Frame(operator_body, style="Panel.TFrame")
        self.operator_list_frame.pack(fill=tk.BOTH, expand=True)
        self.refresh_operator_templates()

    def refresh_operator_templates(self) -> None:
        if not hasattr(self, "operator_list_frame"):
            return

        for child in self.operator_list_frame.winfo_children():
            child.destroy()

        if not self.controller.operator_templates:
            ttk.Label(
                self.operator_list_frame,
                text="저장된 작업자 템플릿이 없습니다.",
                style="Panel.TLabel",
                wraplength=self.LIST_MAX_WIDTH - 12,
            ).pack(anchor=tk.W, pady=4)
            return

        for template in self.controller.operator_templates:
            row = ttk.Frame(
                self.operator_list_frame,
                padding=(8, 6),
                style="Panel.TFrame",
            )
            row.pack(fill=tk.X, pady=4)
            ttk.Label(
                row,
                text=template.name,
                style="Panel.TLabel",
                font=("Arial", 9, "bold"),
                wraplength=self.LIST_MAX_WIDTH - 20,
            ).pack(anchor=tk.W)
            ttk.Label(
                row,
                text=format_qualification_summary(template.qualified_process_types),
                style="Panel.TLabel",
            ).pack(anchor=tk.W, pady=(1, 4))

            actions = ttk.Frame(row, style="Panel.TFrame")
            actions.pack(fill=tk.X)
            ttk.Button(
                actions,
                text="불러오기",
                command=lambda template_id=template.id: self.controller.load_operator_template(
                    template_id
                ),
            ).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Button(
                actions,
                text="삭제",
                command=lambda template_id=template.id: self.controller.delete_operator_template(
                    template_id
                ),
            ).pack(side=tk.LEFT)

    @classmethod
    def _bounded_list_width(cls, container_width: int, scrollbar_width: int) -> int:
        available_width = container_width - scrollbar_width - cls.SCROLLBAR_MARGIN
        return max(1, min(cls.LIST_MAX_WIDTH, available_width))

    def _text_color_for_button(self, block_type: str) -> str:
        if block_type in {"BENDING", "CUTTING", "PACKING"}:
            return "#111827"
        return "white"


class CanvasView:
    CONNECTION_GAP = 10
    CONNECTION_CONTROL_MIN = 44
    CONNECTION_CONTROL_MAX = 140

    def __init__(self, parent: tk.Widget, controller: App) -> None:
        self.controller = controller
        self.drag_block_id: int | None = None
        self.drag_operator_id: int | None = None
        self.drag_x = 0.0
        self.drag_y = 0.0
        self.current_tokens: list[BundleTokenState] = []
        self._updating_controls = False

        self.frame = ttk.LabelFrame(
            parent,
            text="공정 다이어그램",
            padding=8,
            style="Panel.TLabelframe",
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)

        self.playback_frame = ttk.Frame(self.frame, style="Playback.TFrame")
        self.playback_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.playback_frame.grid_columnconfigure(4, weight=1)

        self.play_button = ttk.Button(
            self.playback_frame,
            text="재생",
            width=8,
            command=self.controller.toggle_playback,
        )
        self.play_button.grid(row=0, column=0, padx=(0, 4))
        ttk.Button(
            self.playback_frame,
            text="정지",
            width=8,
            command=self.controller.stop_playback,
        ).grid(row=0, column=1, padx=(0, 8))

        self.speed_var = tk.StringVar(value="1x")
        speed_box = ttk.Combobox(
            self.playback_frame,
            textvariable=self.speed_var,
            values=("0.5x", "1x", "2x", "5x"),
            width=6,
            state="readonly",
        )
        speed_box.grid(row=0, column=2, padx=(0, 8))
        speed_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.controller.set_playback_speed(self.speed_var.get()),
        )

        self.time_var = tk.StringVar(value="0.0 / 0.0분")
        ttk.Label(self.playback_frame, textvariable=self.time_var, width=18).grid(
            row=0,
            column=3,
            padx=(0, 8),
        )

        self.time_scale_var = tk.DoubleVar(value=0)
        self.time_scale = ttk.Scale(
            self.playback_frame,
            from_=0,
            to=1,
            orient=tk.HORIZONTAL,
            variable=self.time_scale_var,
            command=self._on_seek,
        )
        self.time_scale.grid(row=0, column=4, sticky="ew", padx=(0, 8))

        self.state_var = tk.StringVar(value="시뮬레이션 전")
        ttk.Label(
            self.playback_frame,
            textvariable=self.state_var,
            foreground="#b45309",
            width=16,
        ).grid(row=0, column=5)

        self.canvas = tk.Canvas(
            self.frame,
            bg="#eef3f8",
            cursor="cross",
            highlightthickness=1,
            highlightbackground="#cbd5e1",
        )
        h_scroll = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
            scrollregion=(0, 0, 2000, 2000),
        )

        self.canvas.grid(row=1, column=0, sticky="nsew")
        h_scroll.grid(row=2, column=0, sticky="ew")
        v_scroll.grid(row=1, column=1, sticky="ns")
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)

    def redraw(self) -> None:
        self.canvas.delete("all")
        self.current_tokens = self.controller.animation_display_tokens()
        self.draw_grid()
        for connection in self.controller.scenario.connections:
            self.draw_connection(connection)
        for assignment in self.controller.scenario.operator_assignments:
            self.draw_operator_assignment(assignment)
        for block in self.controller.scenario.blocks:
            self.draw_block(block)
        for operator in self.controller.scenario.operators:
            self.draw_operator(operator)
        self.draw_animation_tokens()

    def draw_block(self, block: ProcessBlock) -> None:
        block_type = BLOCK_TYPES[block.type]
        display_name = self._block_canvas_title(block)
        text_color = self._text_color_for_block(block.type)
        block_tokens = [token for token in self.current_tokens if token.block_id == block.id]
        has_waiting = any(token.state == "waiting" for token in block_tokens)
        processing = [token for token in block_tokens if token.state == "processing"]
        is_bottleneck = (
            self.controller.last_result is not None
            and self.controller.last_result.bottleneck_id == block.id
        )
        outline = "#ffffff"
        outline_width = 3
        if has_waiting:
            outline = "#f59e0b"
            outline_width = 4
        if processing:
            outline = "#22c55e"
            outline_width = 4
        if is_bottleneck:
            outline = "#dc2626"
            outline_width = 5

        self.canvas.create_rectangle(
            block.x + 4,
            block.y + 4,
            block.x + block.width + 4,
            block.y + block.height + 4,
            fill="#cbd5e1",
            outline="",
            tags=f"block_{block.id}",
        )
        self.canvas.create_rectangle(
            block.x,
            block.y,
            block.x + block.width,
            block.y + block.height,
            fill=block_type.color,
            outline=outline,
            width=outline_width,
            tags=f"block_{block.id}",
        )
        if processing:
            progress = max(token.progress for token in processing)
            self.canvas.create_rectangle(
                block.x + 6,
                block.y + block.height - 10,
                block.x + block.width - 6,
                block.y + block.height - 4,
                fill="#dbeafe",
                outline="",
                tags=f"block_{block.id}",
            )
            self.canvas.create_rectangle(
                block.x + 6,
                block.y + block.height - 10,
                block.x + 6 + (block.width - 12) * progress,
                block.y + block.height - 4,
                fill="#22c55e",
                outline="",
                tags=f"block_{block.id}",
            )
        self.canvas.create_text(
            block.x + 20,
            block.y + 20,
            text=block_type.icon,
            font=("Arial", 20),
            fill=text_color,
            tags=f"block_{block.id}",
        )
        if is_bottleneck:
            self.canvas.create_rectangle(
                block.x + block.width - 50,
                block.y - 12,
                block.x + block.width + 2,
                block.y + 10,
                fill="#dc2626",
                outline="white",
                width=1,
                tags=f"block_{block.id}",
            )
            self.canvas.create_text(
                block.x + block.width - 24,
                block.y - 1,
                text="병목",
                font=("Arial", 8, "bold"),
                fill="white",
                tags=f"block_{block.id}",
            )
        self.canvas.create_text(
            block.x + 75,
            block.y + 20,
            text=display_name,
            font=("Arial", 9, "bold"),
            fill=text_color,
            width=88,
            tags=f"block_{block.id}",
        )
        line1, line2 = self._block_metric_lines(block)
        self.canvas.create_text(
            block.x + 75,
            block.y + 45,
            text=line1,
            font=("Arial", 8),
            fill=text_color,
            tags=f"block_{block.id}",
        )
        self.canvas.create_text(
            block.x + 75,
            block.y + 60,
            text=line2,
            font=("Arial", 8),
            fill=text_color,
            tags=f"block_{block.id}",
        )

    def draw_operator(self, operator: Operator) -> None:
        self.canvas.create_rectangle(
            operator.x + 4,
            operator.y + 4,
            operator.x + operator.width + 4,
            operator.y + operator.height + 4,
            fill="#cbd5e1",
            outline="",
            tags=f"operator_{operator.id}",
        )
        self.canvas.create_rectangle(
            operator.x,
            operator.y,
            operator.x + operator.width,
            operator.y + operator.height,
            fill="#f8fafc",
            outline="#7c3aed",
            width=3,
            tags=f"operator_{operator.id}",
        )
        self.canvas.create_oval(
            operator.x + 10,
            operator.y + 12,
            operator.x + 34,
            operator.y + 36,
            fill="#7c3aed",
            outline="",
            tags=f"operator_{operator.id}",
        )
        self.canvas.create_text(
            operator.x + 22,
            operator.y + 24,
            text="OP",
            font=("Arial", 8, "bold"),
            fill="white",
            tags=f"operator_{operator.id}",
        )
        self.canvas.create_text(
            operator.x + 76,
            operator.y + 20,
            text=operator.name,
            font=("Arial", 9, "bold"),
            fill="#111827",
            width=78,
            tags=f"operator_{operator.id}",
        )
        self.canvas.create_text(
            operator.x + 76,
            operator.y + 44,
            text=format_operator_qualification_summary(operator),
            font=("Arial", 8),
            fill="#475569",
            tags=f"operator_{operator.id}",
        )

    def draw_operator_assignment(self, assignment: OperatorAssignment) -> None:
        operator = self.controller.find_operator(assignment.operator_id)
        block = self.controller.find_block(assignment.block_id)
        if operator is None or block is None:
            return

        line_points, delete_position = self._connection_path(operator, block)
        self.canvas.create_line(
            *line_points,
            fill="#7c3aed",
            width=3,
            smooth=True,
            dash=(6, 4),
            tags=f"opassign_{assignment.id}",
        )

        mid_x, mid_y = delete_position
        self.canvas.create_oval(
            mid_x - 8,
            mid_y - 8,
            mid_x + 8,
            mid_y + 8,
            fill="#7c3aed",
            outline="white",
            width=2,
            tags=f"opassign_{assignment.id}_delete",
        )
        self.canvas.create_text(
            mid_x,
            mid_y,
            text="x",
            font=("Arial", 10, "bold"),
            fill="white",
            tags=f"opassign_{assignment.id}_delete",
        )

    def _block_canvas_title(self, block: ProcessBlock) -> str:
        if block.type == "INPUT":
            return BLOCK_TYPES[block.type].label
        return self.controller.block_display_name(block)

    def _text_color_for_block(self, block_type: str) -> str:
        if block_type in {"BENDING", "CUTTING", "PACKING"}:
            return "#111827"
        return "white"

    def _block_metric_lines(self, block: ProcessBlock) -> tuple[str, str]:
        if block.type == "INPUT":
            return (
                f"수량: {block.input_quantity} EA",
                f"투입: {block.input_time:g}분",
            )
        if block.type == "HOIST":
            return (
                f"운반: {block.transport_capacity} EA/회",
                f"이동: {block.transport_time:g}분/회",
            )
        return (
            f"처리: {block.process_time_per_ea:g}분/EA",
            f"동시: {block.concurrent_capacity} EA",
        )

    def draw_connection(self, connection: ProcessConnection) -> None:
        from_block = self.controller.find_block(connection.from_block)
        to_block = self.controller.find_block(connection.to_block)
        if not from_block or not to_block:
            return

        line_points, delete_position = self._connection_path(from_block, to_block)

        self.canvas.create_line(
            *line_points,
            arrow=tk.LAST,
            fill="#475569",
            width=3,
            smooth=True,
            tags=f"conn_{connection.id}",
        )

        mid_x, mid_y = delete_position
        self.canvas.create_oval(
            mid_x - 8,
            mid_y - 8,
            mid_x + 8,
            mid_y + 8,
            fill="#ef4444",
            outline="white",
            width=2,
            tags=f"conn_{connection.id}_delete",
        )
        self.canvas.create_text(
            mid_x,
            mid_y,
            text="×",
            font=("Arial", 12, "bold"),
            fill="white",
            tags=f"conn_{connection.id}_delete",
        )

    def _connection_path(
        self,
        from_block: ProcessBlock,
        to_block: ProcessBlock,
    ) -> tuple[tuple[float, ...], tuple[float, float]]:
        from_side, to_side = self._connection_sides(from_block, to_block)
        x1, y1, dx1, dy1 = self._connection_anchor(from_block, from_side)
        x2, y2, dx2, dy2 = self._connection_anchor(to_block, to_side)

        distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        control_distance = min(
            self.CONNECTION_CONTROL_MAX,
            max(self.CONNECTION_CONTROL_MIN, distance * 0.35),
        )
        control1 = (x1 + dx1 * control_distance, y1 + dy1 * control_distance)
        control2 = (x2 + dx2 * control_distance, y2 + dy2 * control_distance)
        line_points = (
            x1,
            y1,
            control1[0],
            control1[1],
            control2[0],
            control2[1],
            x2,
            y2,
        )
        delete_position = self._cubic_point((x1, y1), control1, control2, (x2, y2), 0.5)
        return line_points, delete_position

    def _connection_sides(
        self,
        from_block: ProcessBlock,
        to_block: ProcessBlock,
    ) -> tuple[str, str]:
        from_center_x = from_block.x + from_block.width / 2
        from_center_y = from_block.y + from_block.height / 2
        to_center_x = to_block.x + to_block.width / 2
        to_center_y = to_block.y + to_block.height / 2
        delta_x = to_center_x - from_center_x
        delta_y = to_center_y - from_center_y

        if abs(delta_x) >= abs(delta_y):
            if delta_x >= 0:
                return "right", "left"
            return "left", "right"
        if delta_y >= 0:
            return "bottom", "top"
        return "top", "bottom"

    def _connection_anchor(
        self,
        block: ProcessBlock,
        side: str,
    ) -> tuple[float, float, int, int]:
        center_x = block.x + block.width / 2
        center_y = block.y + block.height / 2
        gap = self.CONNECTION_GAP
        if side == "left":
            return block.x - gap, center_y, -1, 0
        if side == "right":
            return block.x + block.width + gap, center_y, 1, 0
        if side == "top":
            return center_x, block.y - gap, 0, -1
        return center_x, block.y + block.height + gap, 0, 1

    def _cubic_point(
        self,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        inverse = 1 - t
        x = (
            inverse**3 * p0[0]
            + 3 * inverse**2 * t * p1[0]
            + 3 * inverse * t**2 * p2[0]
            + t**3 * p3[0]
        )
        y = (
            inverse**3 * p0[1]
            + 3 * inverse**2 * t * p1[1]
            + 3 * inverse * t**2 * p2[1]
            + t**3 * p3[1]
        )
        return x, y

    def draw_grid(self) -> None:
        for position in range(0, 2001, 40):
            self.canvas.create_line(
                position,
                0,
                position,
                2000,
                fill="#e5e7eb",
                width=1,
                tags="grid",
            )
            self.canvas.create_line(
                0,
                position,
                2000,
                position,
                fill="#e5e7eb",
                width=1,
                tags="grid",
            )

    def draw_animation_tokens(self) -> None:
        stack_index: dict[tuple[int, str], int] = {}
        selected_id = self.controller.animation.state.selected_token_id
        for token in self.current_tokens:
            block = self.controller.find_block(token.block_id)
            if block is None:
                continue
            key = (token.block_id, token.state)
            index = stack_index.get(key, 0)
            stack_index[key] = index + 1
            x, y = self._token_position(token, block, index)
            self._draw_token(token, x, y, selected_id)

    def _token_position(
        self,
        token: BundleTokenState,
        block: ProcessBlock,
        index: int,
    ) -> tuple[float, float]:
        if token.state == "waiting":
            return block.x - 105, block.y + 8 + index * 30
        if token.state == "complete":
            return block.x + block.width + 12, block.y + 38 + index * 30
        return block.x + block.width + 12, block.y + 8 + index * 30

    def _token_size(self, token: BundleTokenState) -> tuple[int, int]:
        return (96 if token.is_aggregate else 58, 24)

    def _draw_token(
        self,
        token: BundleTokenState,
        x: float,
        y: float,
        selected_id: str | None,
    ) -> None:
        width, height = self._token_size(token)
        color = self.controller.animation.product_color(token.product_name)
        selected = token.token_id == selected_id
        outline = "#111827" if selected else "#ffffff"
        label = f"{token.product_name}/{token.material_name} {token.quantity}EA"
        if token.is_aggregate:
            label = f"{token.product_name}/{token.material_name} {token.quantity}EA · {token.bundle_count}개"

        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill=color,
            outline=outline,
            width=3 if selected else 1,
            tags=("animation_token", f"token_{token.token_id}"),
        )
        self.canvas.create_text(
            x + width / 2,
            y + height / 2,
            text=label,
            font=("Arial", 7, "bold"),
            fill="white",
            width=width - 6,
            tags=("animation_token", f"token_{token.token_id}"),
        )

    def show_connection_start(self, kind: str, target_id: int) -> None:
        target = (
            self.controller.find_operator(target_id)
            if kind == "operator"
            else self.controller.find_block(target_id)
        )
        if not target:
            return
        self.canvas.config(cursor="tcross", bg="#fff7ed")
        self.canvas.delete("connection_highlight")
        self.canvas.create_rectangle(
            target.x - 5,
            target.y - 5,
            target.x + target.width + 5,
            target.y + target.height + 5,
            outline="#ef4444",
            width=4,
            dash=(5, 5),
            tags="connection_highlight",
        )

    def end_connection_mode(self) -> None:
        self.canvas.config(cursor="cross", bg="#eef3f8")
        self.canvas.delete("connection_highlight")

    def on_click(self, event: tk.Event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        connection_id = self._connection_delete_at(x, y)
        if connection_id is not None:
            self.controller.delete_connection(connection_id)
            return

        assignment_id = self._operator_assignment_delete_at(x, y)
        if assignment_id is not None:
            self.controller.delete_operator_assignment(assignment_id)
            return

        token_id = self._animation_token_at(x, y)
        if token_id is not None:
            self.controller.select_animation_token(token_id)
            return

        block_id = self._block_at(x, y)
        operator_id = self._operator_at(x, y)
        if event.state & 0x0001:
            if block_id is not None:
                self.controller.start_or_finish_connection(block_id)
            elif operator_id is not None:
                self.controller.start_or_finish_operator_connection(operator_id)
            return

        if block_id is not None:
            self.drag_block_id = block_id
            self.drag_operator_id = None
            self.drag_x = x
            self.drag_y = y
            return

        if operator_id is not None:
            self.drag_operator_id = operator_id
            self.drag_block_id = None
            self.drag_x = x
            self.drag_y = y
            return

        self.drag_block_id = None
        self.drag_operator_id = None
        self.controller.select_animation_token(None)

    def on_drag(self, event: tk.Event) -> None:
        if self.drag_block_id is None and self.drag_operator_id is None:
            return

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dx = x - self.drag_x
        dy = y - self.drag_y

        if self.drag_block_id is not None:
            self.controller.move_block(self.drag_block_id, dx, dy)
        elif self.drag_operator_id is not None:
            self.controller.move_operator(self.drag_operator_id, dx, dy)
        self.drag_x = x
        self.drag_y = y

    def on_release(self, _event: tk.Event) -> None:
        self.drag_block_id = None
        self.drag_operator_id = None

    def on_double_click(self, event: tk.Event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        block_id = self._block_at(x, y)
        if block_id is not None:
            self.controller.edit_block_parameters(block_id)
            return
        operator_id = self._operator_at(x, y)
        if operator_id is not None:
            self.controller.edit_operator(operator_id)

    def on_right_click(self, event: tk.Event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        block_id = self._block_at(x, y)
        operator_id = self._operator_at(x, y)
        if block_id is None and operator_id is None:
            return

        menu = tk.Menu(self.controller.root, tearoff=0)
        if block_id is not None:
            menu.add_command(
                label="설정",
                command=lambda: self.controller.edit_block_parameters(block_id),
            )
            menu.add_separator()
            menu.add_command(
                label="삭제",
                command=lambda: self.controller.delete_block(block_id),
            )
        elif operator_id is not None:
            menu.add_command(
                label="설정",
                command=lambda: self.controller.edit_operator(operator_id),
            )
            menu.add_command(
                label="자주 쓰는 작업자로 저장",
                command=lambda: self.controller.save_operator_to_library(operator_id),
            )
            menu.add_separator()
            menu.add_command(
                label="삭제",
                command=lambda: self.controller.delete_operator(operator_id),
            )
        menu.post(event.x_root, event.y_root)

    def on_mousewheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            self.canvas.yview_scroll(1, "units")

    def _block_at(self, x: float, y: float) -> int | None:
        clicked = self.canvas.find_overlapping(x, y, x, y)
        for item in clicked:
            for tag in self.canvas.gettags(item):
                if tag.startswith("block_"):
                    return int(tag.split("_")[1])
        return None

    def _operator_at(self, x: float, y: float) -> int | None:
        clicked = self.canvas.find_overlapping(x, y, x, y)
        for item in clicked:
            for tag in self.canvas.gettags(item):
                if tag.startswith("operator_"):
                    return int(tag.split("_")[1])
        return None

    def _connection_delete_at(self, x: float, y: float) -> int | None:
        clicked = self.canvas.find_overlapping(x, y, x, y)
        for item in clicked:
            for tag in self.canvas.gettags(item):
                if tag.startswith("conn_") and tag.endswith("_delete"):
                    return int(tag.split("_")[1])
        return None

    def _operator_assignment_delete_at(self, x: float, y: float) -> int | None:
        clicked = self.canvas.find_overlapping(x, y, x, y)
        for item in clicked:
            for tag in self.canvas.gettags(item):
                if tag.startswith("opassign_") and tag.endswith("_delete"):
                    return int(tag.split("_")[1])
        return None

    def _animation_token_at(self, x: float, y: float) -> str | None:
        clicked = self.canvas.find_overlapping(x, y, x, y)
        for item in clicked:
            for tag in self.canvas.gettags(item):
                if tag.startswith("token_"):
                    return tag.removeprefix("token_")
        return None

    def _on_seek(self, value: str) -> None:
        if self._updating_controls:
            return
        self.controller.seek_playhead(float(value))

    def update_playback_controls(self) -> None:
        result = self.controller.last_result
        state = self.controller.animation.state
        total_time = result.total_time if result else 0.0

        self._updating_controls = True
        self.time_scale.configure(to=max(total_time, 1.0))
        self.time_scale_var.set(state.current_time)
        self._updating_controls = False

        self.play_button.configure(text="일시정지" if state.is_playing else "재생")
        self.time_var.set(f"{state.current_time:.1f} / {total_time:.1f}분")
        if state.is_stale:
            self.state_var.set("재실행 필요")
        elif result and state.is_compact:
            self.state_var.set("축약 표시 중")
        elif result:
            self.state_var.set("결과 최신")
        else:
            self.state_var.set("시뮬레이션 전")


class ResultView:
    def __init__(self, parent: tk.Widget, controller: App) -> None:
        self.controller = controller
        self.frame = ttk.LabelFrame(
            parent,
            text="시뮬레이션 결과",
            padding=10,
            style="Panel.TLabelframe",
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)

        animation_frame = ttk.LabelFrame(
            self.frame,
            text="현재 시점",
            padding=8,
            style="Panel.TLabelframe",
        )
        animation_frame.pack(fill=tk.X, pady=(0, 8))
        self.animation_summary_var = tk.StringVar(value="시뮬레이션 전")
        self.animation_selection_var = tk.StringVar(value="선택 묶음 없음")
        ttk.Label(
            animation_frame,
            textvariable=self.animation_summary_var,
            justify=tk.LEFT,
            anchor=tk.W,
            style="Panel.TLabel",
        ).pack(fill=tk.X)
        ttk.Label(
            animation_frame,
            textvariable=self.animation_selection_var,
            justify=tk.LEFT,
            anchor=tk.W,
            style="Panel.TLabel",
        ).pack(fill=tk.X, pady=(4, 0))

        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        summary_frame = ttk.Frame(notebook, style="Panel.TFrame", padding=6)
        timeline_frame = ttk.Frame(notebook, style="Panel.TFrame", padding=6)
        analysis_frame = ttk.Frame(notebook, style="Panel.TFrame", padding=6)
        notebook.add(summary_frame, text="요약")
        notebook.add(timeline_frame, text="타임라인")
        notebook.add(analysis_frame, text="분석")

        self.summary_text = tk.Text(
            summary_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            bg="#ffffff",
            fg="#1f2937",
            relief=tk.FLAT,
            padx=8,
            pady=8,
            spacing1=2,
            spacing3=4,
            width=40,
            height=12,
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True)

        self.timeline_canvas = tk.Canvas(
            timeline_frame,
            bg="#ffffff",
            width=380,
            height=300,
            highlightthickness=1,
            highlightbackground="#e2e8f0",
        )
        timeline_scroll = ttk.Scrollbar(
            timeline_frame,
            orient=tk.VERTICAL,
            command=self.timeline_canvas.yview,
        )
        self.timeline_canvas.configure(yscrollcommand=timeline_scroll.set)
        self.timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        timeline_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.analysis_text = tk.Text(
            analysis_frame,
            wrap=tk.WORD,
            font=("Arial", 9),
            bg="#ffffff",
            fg="#1f2937",
            relief=tk.FLAT,
            padx=8,
            pady=8,
            spacing1=2,
            spacing3=4,
            width=40,
            height=20,
        )
        analysis_scroll = ttk.Scrollbar(
            analysis_frame,
            orient=tk.VERTICAL,
            command=self.analysis_text.yview,
        )
        self.analysis_text.configure(yscrollcommand=analysis_scroll.set)
        self.analysis_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        analysis_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def clear(self) -> None:
        self.summary_text.delete(1.0, tk.END)
        self.timeline_canvas.delete("all")
        self.analysis_text.delete(1.0, tk.END)
        self.animation_summary_var.set("시뮬레이션 전")
        self.animation_selection_var.set("선택 묶음 없음")

    def display(self, result: SimulationResult) -> None:
        self.clear()
        bottleneck_name = self._bottleneck_name(result)
        bottleneck_reason = self.controller.bottleneck_reason(result)
        bottleneck_impact = self.controller.bottleneck_impact(result)

        self.summary_text.insert(tk.END, "=" * 40 + "\n")
        self.summary_text.insert(tk.END, "   묶음 기반 시뮬레이션 결과\n")
        self.summary_text.insert(tk.END, "=" * 40 + "\n\n")
        self.summary_text.insert(tk.END, f"총 소요 시간: {result.total_time:.1f}분\n")
        self.summary_text.insert(tk.END, f"전체 투입 수량: {result.total_input_quantity} EA\n")
        self.summary_text.insert(tk.END, f"최종 output 수량: {result.final_output_quantity} EA\n\n")
        self.summary_text.insert(
            tk.END,
            f"제품 추적 라벨 수: {result.unique_product_count}개\n",
        )
        self.summary_text.insert(
            tk.END,
            "제품 라벨별 투입 EA: "
            f"{self._format_product_quantities(result.input_quantity_by_product)}\n",
        )
        self.summary_text.insert(
            tk.END,
            "제품 라벨별 최종 output EA: "
            f"{self._format_product_quantities(result.final_output_quantity_by_product)}\n\n",
        )
        self.summary_text.insert(tk.END, f"병목 공정: {bottleneck_name}\n")
        self.summary_text.insert(tk.END, f"   이유: {bottleneck_reason}\n")
        self.summary_text.insert(tk.END, f"   영향: {bottleneck_impact}\n\n")
        self.summary_text.insert(tk.END, f"공정 수: {len(result.timeline)}개\n")

        avg_cycle = (
            result.total_time / result.final_output_quantity
            if result.final_output_quantity > 0
            else 0
        )
        self.summary_text.insert(tk.END, f"평균 소요 시간: {avg_cycle:.1f}분/EA\n")

        self._draw_timeline(result)
        self._write_analysis(result, bottleneck_name, bottleneck_reason, bottleneck_impact)
        self.update_animation_panel()

    def set_stale(self, is_stale: bool) -> None:
        if not is_stale:
            self.update_animation_panel()
            return
        if self.controller.last_result is None:
            self.animation_summary_var.set("시뮬레이션 실행이 필요합니다.")
        else:
            self.animation_summary_var.set("결과가 오래되었습니다. 시뮬레이션을 다시 실행해주세요.")

    def update_animation_panel(self) -> None:
        result = self.controller.last_result
        state = self.controller.animation.state
        if result is None:
            self.animation_summary_var.set(
                "시뮬레이션 실행이 필요합니다." if state.is_stale else "시뮬레이션 전"
            )
            self.animation_selection_var.set("선택 묶음 없음")
            return
        if state.is_stale:
            self.animation_summary_var.set(
                f"결과 오래됨 · 마지막 총 소요 시간 {result.total_time:.1f}분"
            )
            self.animation_selection_var.set("시뮬레이션 재실행 후 묶음 선택 가능")
            return

        tokens = self.controller.animation_display_tokens()
        summary = self.controller.animation.current_summary(tokens)
        summary_text = (
            f"현재 {state.current_time:.1f} / {result.total_time:.1f}분 · "
            f"대기 {summary.get('waiting', 0)}개 · "
            f"처리 {summary.get('processing', 0)}개 · "
            f"완료 {summary.get('complete', 0)}개"
        )
        if state.is_compact:
            summary_text += " · 축약 표시 중"
        self.animation_summary_var.set(summary_text)

        selected = self.controller.animation.selected_token(result)
        if selected is None:
            self.animation_selection_var.set("선택 묶음 없음")
            return

        block_name = self.controller.block_display_name(
            self.controller.find_block(selected.block_id)
        )
        state_label = TOKEN_STATE_LABELS.get(selected.state, selected.state)
        if selected.is_aggregate:
            self.animation_selection_var.set(
                f"선택 집계: {selected.product_name}/{selected.material_name} · "
                f"{selected.quantity}EA · 묶음 {selected.bundle_count}개 · "
                f"{state_label} · {block_name}"
            )
            return

        self.animation_selection_var.set(
            f"선택 묶음 #{selected.bundle_id}: "
            f"{selected.product_name}/{selected.material_name} {selected.quantity}EA · "
            f"{state_label} · {block_name} · "
            f"{selected.arrival_time:.1f}/{selected.start_time:.1f}/"
            f"{selected.completion_time:.1f}분"
        )

    def _format_product_quantities(self, quantities: dict[str, int]) -> str:
        if not quantities:
            return "없음"
        return ", ".join(
            f"{product_name} {quantity}EA"
            for product_name, quantity in sorted(quantities.items())
        )

    def _draw_timeline(self, result: SimulationResult) -> None:
        y_offset = 30
        self.timeline_canvas.create_text(
            10,
            y_offset,
            text="공정별 성능",
            anchor=tk.W,
            font=("Arial", 11, "bold"),
        )
        y_offset += 30

        finite_throughputs = [
            item.throughput
            for item in result.timeline
            if item.throughput != float("inf")
        ]
        max_throughput = max(finite_throughputs, default=0)
        for idx, item in enumerate(result.timeline):
            block = self.controller.find_block(item.block_id)
            block_type = BLOCK_TYPES[block.type] if block else BLOCK_TYPES["FREE"]
            item_name = self.controller.block_result_display_name(item)

            self.timeline_canvas.create_text(
                10,
                y_offset,
                text=f"{idx + 1}. {block_type.icon} {item_name}",
                anchor=tk.W,
                font=("Arial", 9, "bold"),
            )
            self.timeline_canvas.create_text(
                10,
                y_offset + 15,
                text=self._timeline_metric_text(item, block),
                anchor=tk.W,
                font=("Arial", 8),
                fill="gray",
            )
            if item.avg_waiting > 0.1:
                self.timeline_canvas.create_text(
                    10,
                    y_offset + 30,
                    text=f"평균 대기: {item.avg_waiting:.1f}분",
                    anchor=tk.W,
                    font=("Arial", 8),
                    fill="#ef4444",
                )
                route_y = y_offset + 45
            else:
                route_y = y_offset + 30

            self.timeline_canvas.create_text(
                10,
                route_y,
                text=self._route_text(item.block_id),
                anchor=tk.W,
                font=("Arial", 8),
                fill="#475569",
            )

            bar_x = 210
            bar_width = 120
            bar_height = 20
            bar_length = (
                (item.throughput / max_throughput) * bar_width
                if max_throughput and item.throughput != float("inf")
                else 0
            )
            is_bottleneck = item.block_id == result.bottleneck_id

            self.timeline_canvas.create_rectangle(
                bar_x,
                y_offset,
                bar_x + bar_width,
                y_offset + bar_height,
                fill="#e5e7eb",
                outline="#d1d5db",
            )
            self.timeline_canvas.create_rectangle(
                bar_x,
                y_offset,
                bar_x + bar_length,
                y_offset + bar_height,
                fill="#ef4444" if is_bottleneck else block_type.color,
                outline="white",
                width=2,
            )
            if is_bottleneck:
                self.timeline_canvas.create_text(
                    bar_x + bar_width + 10,
                    y_offset + bar_height / 2,
                    text="병목",
                    anchor=tk.W,
                    font=("Arial", 9, "bold"),
                    fill="red",
                )

            y_offset += 85 if item.avg_waiting > 0.1 else 70

        self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))

    def _write_analysis(
        self,
        result: SimulationResult,
        bottleneck_name: str,
        bottleneck_reason: str,
        bottleneck_impact: str,
    ) -> None:
        self.analysis_text.insert(tk.END, "=" * 70 + "\n")
        self.analysis_text.insert(tk.END, "              묶음 기반 시뮬레이션 상세 분석\n")
        self.analysis_text.insert(tk.END, "=" * 70 + "\n\n")

        self.analysis_text.insert(tk.END, "공정 흐름\n")
        self.analysis_text.insert(tk.END, "-" * 70 + "\n")
        flow_diagram = format_flow_diagram(
            process_flow=result.process_flow,
            connections=self.controller.scenario.connections,
            block_label=self._block_name,
            block_icon=self._block_icon,
        )
        self.analysis_text.insert(tk.END, f"{flow_diagram}\n\n")

        self.analysis_text.insert(tk.END, "공정별 상세 분석\n")
        self.analysis_text.insert(tk.END, "-" * 70 + "\n")
        for idx, item in enumerate(result.timeline, 1):
            item_name = self.controller.block_result_display_name(item)
            self.analysis_text.insert(
                tk.END,
                f"\n{idx}. {self._block_icon(item.block_id)} {item_name}\n",
            )
            block = self.controller.find_block(item.block_id)
            self.analysis_text.insert(tk.END, "   기본 정보:\n")
            self._write_block_operation_details(item, block)
            self.analysis_text.insert(
                tk.END,
                f"   • 처리 제품 라벨 수: {item.unique_product_count}개\n",
            )
            self.analysis_text.insert(
                tk.END,
                f"   • 처리 원자재 수: {item.unique_material_count}개\n",
            )
            self.analysis_text.insert(tk.END, f"   • 실제 처리 수량: {item.total_processed} EA\n")
            self.analysis_text.insert(
                tk.END,
                f"   • 처리 묶음 수: {item.processed_bundle_count}개\n",
            )
            if item.transport_trips:
                self.analysis_text.insert(
                    tk.END,
                    f"   • 호이스트 이동 횟수: {item.transport_trips}회\n",
                )
            self.analysis_text.insert(tk.END, "\n   성능 지표:\n")
            self.analysis_text.insert(tk.END, f"   • 평균 대기 시간: {item.avg_waiting:.1f}분\n")

            if item.block_id == result.bottleneck_id:
                self.analysis_text.insert(tk.END, "\n   병목 공정\n")
                self.analysis_text.insert(tk.END, f"   → {bottleneck_reason}\n")
                self.analysis_text.insert(tk.END, "   → 전체 공정의 처리 속도를 제한하는 구간입니다.\n")

            if item.bundles:
                self.analysis_text.insert(tk.END, "\n   묶음별 타임라인 (처음 5개):\n")
                for bundle in item.bundles[:5]:
                    self.analysis_text.insert(
                        tk.END,
                        f"   {bundle.product_name}/{bundle.material_name} "
                        f"{bundle.quantity}EA: "
                        f"{bundle.start_time:.1f}분 → {bundle.completion_time:.1f}분 "
                        f"({bundle.completion_time - bundle.start_time:.1f}분)\n",
                    )

        self.analysis_text.insert(tk.END, "\n\n병목 분석 및 개선 제안\n")
        self.analysis_text.insert(tk.END, "=" * 70 + "\n")
        self.analysis_text.insert(tk.END, f"\n병목 공정: {bottleneck_name}\n")
        self.analysis_text.insert(tk.END, f"   • {bottleneck_reason}\n")
        self.analysis_text.insert(tk.END, f"   • {bottleneck_impact}\n\n")
        self.analysis_text.insert(tk.END, "개선 방안:\n")
        self.analysis_text.insert(tk.END, "1. 병목 공정의 처리 시간 단축\n")
        self.analysis_text.insert(tk.END, "   - 공정 자동화 검토\n")
        self.analysis_text.insert(tk.END, "   - 작업 방법 개선\n\n")
        self.analysis_text.insert(tk.END, "2. 병목 공정의 동시 가공 수량 증대\n")
        self.analysis_text.insert(tk.END, "   - 설비 대수 증설\n")
        self.analysis_text.insert(tk.END, "   - 병렬 처리 라인 구축\n")

    def _write_block_operation_details(
        self,
        item: BlockResult,
        block: ProcessBlock | None,
    ) -> None:
        if block and block.type == "INPUT":
            self.analysis_text.insert(
                tk.END,
                f"   • 제품명: {block.product_name}\n",
            )
            self.analysis_text.insert(tk.END, f"   • 원자재명: {block.material_name}\n")
            self.analysis_text.insert(tk.END, f"   • 투입 원자재 수: {block.input_quantity} EA\n")
            self.analysis_text.insert(tk.END, f"   • 투입 시간: {block.input_time:g}분\n")
            return
        if block and block.type == "HOIST":
            self.analysis_text.insert(tk.END, f"   • 1회 운반 수량: {block.transport_capacity} EA\n")
            self.analysis_text.insert(tk.END, f"   • 1회 이동 시간: {block.transport_time:g}분\n")
            self.analysis_text.insert(tk.END, f"   • 이론 운반율: {item.throughput:.3f} EA/분\n")
            return

        if block:
            self.analysis_text.insert(
                tk.END,
                f"   • 처리 시간: {block.process_time_per_ea:g}분/EA\n",
            )
            self.analysis_text.insert(
                tk.END,
                f"   • 동시 가공 수량: {block.concurrent_capacity} EA\n",
            )
        self.analysis_text.insert(tk.END, f"   • 이론 처리율: {item.throughput:.3f} EA/분\n")

    def _block_icon(self, block_id: int) -> str:
        block = self.controller.find_block(block_id)
        if not block:
            return ""
        return BLOCK_TYPES[block.type].icon

    def _block_name(self, block_id: int) -> str:
        return self.controller.block_display_name(self.controller.find_block(block_id))

    def _timeline_metric_text(
        self,
        item: BlockResult,
        block: ProcessBlock | None,
    ) -> str:
        if block and block.type == "INPUT":
            return (
                f"투입 {item.total_processed} EA | 묶음 {item.processed_bundle_count}개 | "
                f"투입 시간 {block.input_time:g}분"
            )
        if block and block.type == "HOIST":
            return (
                f"운반 {item.total_processed} EA | 묶음 {item.processed_bundle_count}개 | "
                f"이동 {item.transport_trips}회"
            )
        return (
            f"처리 {item.total_processed} EA | 묶음 {item.processed_bundle_count}개 | "
            f"이론 처리율 {item.throughput:.3f} EA/분"
        )

    def _route_text(self, block_id: int) -> str:
        outgoing = [
            connection
            for connection in self.controller.scenario.connections
            if connection.from_block == block_id
        ]
        if not outgoing:
            return "다음: 종료 공정"

        names = [
            self.controller.block_display_name(
                self.controller.find_block(connection.to_block)
            )
            for connection in outgoing
        ]
        return f"다음: {', '.join(names)}"

    def _bottleneck_name(self, result: SimulationResult) -> str:
        if result.bottleneck_id is None:
            return "없음"
        return self.controller.block_display_name(self.controller.find_block(result.bottleneck_id))
