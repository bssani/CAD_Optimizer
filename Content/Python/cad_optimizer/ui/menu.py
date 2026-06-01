"""Tools menu entries for CAD Optimizer.

사용자 친화 메뉴 6개로 압축. 진단/측정 단일 entry (Generate Report) 가
F2/F3/F4/F6 통합 측정 + 박제 수행. F4 multi-preset (Small/Medium),
Merge Dry Run, Organize ISM Holders, Cull High only 등 보조 동작은
``cad_optimizer.ui.panel`` 함수로 Python Console에서 호출 가능
(``run_detect_small_parts(threshold_cm=1.0)`` 등).
"""
import unreal

_MENU_SCRIPTS: list = []


@unreal.uclass()
class CADOptimizerOpenMainCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.widget_handlers import open_main_panel

        open_main_panel()


@unreal.uclass()
class CADOptimizerIntegratedReportCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_integrated_report

        run_integrated_report()


@unreal.uclass()
class CADOptimizerApplyMetadataTagsCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_apply_metadata_tags

        run_apply_metadata_tags()


@unreal.uclass()
class CADOptimizerMergeActorsApplyCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_merge_actors_apply

        run_merge_actors_apply()


@unreal.uclass()
class CADOptimizerCullHighMidCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import (
            run_apply_visibility_culling_high_mid,
        )

        run_apply_visibility_culling_high_mid()


@unreal.uclass()
class CADOptimizerRestoreP3VisibilityCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_restore_p3_visibility

        run_restore_p3_visibility()


def _register(script: unreal.ToolMenuEntryScript, name: str, label: str, tool_tip: str) -> None:
    script.init_entry(
        owner_name="CADOptimizer",
        menu="LevelEditor.MainMenu.Tools",
        section="CADOptimizer",
        name=name,
        label=label,
        tool_tip=tool_tip,
    )
    script.register_menu_entry()
    _MENU_SCRIPTS.append(script)


def register_menu() -> None:
    _register(
        CADOptimizerOpenMainCommand(),
        name="CADOptimizer.OpenMain",
        label="CAD Optimizer",
        tool_tip="GMTCK PCVR mesh optimization tool",
    )
    _register(
        CADOptimizerIntegratedReportCommand(),
        name="CADOptimizer.GenerateReport",
        label="📊 Generate Report",
        tool_tip="측정 보고서 생성 (mesh stats + 머지/cull 후보 + 예상 감소량). "
                 "Level 변경 없음. markdown + CSV 박제.",
    )
    _register(
        CADOptimizerApplyMetadataTagsCommand(),
        name="CADOptimizer.TagSmallParts",
        label="🏷️ Tag Small Parts",
        tool_tip="작은 부품을 cull tier로 분류 + tag 부여. "
                 "다음 단계 (Merge / Cull) 입력. Level dirty.",
    )
    _register(
        CADOptimizerMergeActorsApplyCommand(),
        name="CADOptimizer.MergeActors",
        label="🔗 Merge Actors",
        tool_tip="중복 mesh actor들을 ISM 1개로 합쳐 drawcall 감소. "
                 "Level dirty — save 필요. Undo로 revert 가능.",
    )
    _register(
        CADOptimizerCullHighMidCommand(),
        name="CADOptimizer.CullSmallParts",
        label="🙈 Cull Small Parts",
        tool_tip="Tag된 작은 부품들을 hidden 처리 (rendering 제외). "
                 "Level dirty. Restore로 revert 가능.",
    )
    _register(
        CADOptimizerRestoreP3VisibilityCommand(),
        name="CADOptimizer.RestoreHidden",
        label="👁️ Restore Hidden",
        tool_tip="Cull로 hidden 처리한 actor 일괄 복원. "
                 "잘못 cull 됐을 때 안전망.",
    )

    unreal.ToolMenus.get().refresh_all_widgets()
