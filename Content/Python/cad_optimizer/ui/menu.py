import unreal

_MENU_SCRIPTS: list = []


@unreal.uclass()
class CADOptimizerOpenMainCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.widget_handlers import open_main_panel

        open_main_panel()


@unreal.uclass()
class CADOptimizerScanLevelCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_scan_level

        run_scan_level()


@unreal.uclass()
class CADOptimizerDetectInstancesCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_detect_instances

        run_detect_instances()


@unreal.uclass()
class CADOptimizerDetectSmallPartsTinyCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.small_part_detector import PRESETS
        from cad_optimizer.ui.panel import run_detect_small_parts

        run_detect_small_parts(threshold_cm=PRESETS["Tiny"])


@unreal.uclass()
class CADOptimizerDetectSmallPartsSmallCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.small_part_detector import PRESETS
        from cad_optimizer.ui.panel import run_detect_small_parts

        run_detect_small_parts(threshold_cm=PRESETS["Small"])


@unreal.uclass()
class CADOptimizerDetectSmallPartsMediumCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.small_part_detector import PRESETS
        from cad_optimizer.ui.panel import run_detect_small_parts

        run_detect_small_parts(threshold_cm=PRESETS["Medium"])


@unreal.uclass()
class CADOptimizerMaterialInventoryCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_material_inventory

        run_material_inventory()


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
class CADOptimizerMergeActorsDryRunCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_merge_actors_dry_run

        run_merge_actors_dry_run()


@unreal.uclass()
class CADOptimizerMergeActorsApplyCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_merge_actors_apply

        run_merge_actors_apply()


@unreal.uclass()
class CADOptimizerOrganizeISMHoldersCommand(unreal.ToolMenuEntryScript):
    @unreal.ufunction(override=True)
    def execute(self, context) -> None:
        from cad_optimizer.ui.panel import run_organize_ism_holders

        run_organize_ism_holders()


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
        CADOptimizerScanLevelCommand(),
        name="CADOptimizer.ScanLevel",
        label="Scan Level (Mesh Stats)",
        tool_tip="F2: walk level StaticMeshActors, log LOD0 statistics to Output Log",
    )
    _register(
        CADOptimizerDetectInstancesCommand(),
        name="CADOptimizer.DetectInstances",
        label="Detect Instances (F3)",
        tool_tip="F3: group StaticMeshActors by (mesh, materials, mobility); "
                 "emits CSV report + top-10 Output Log summary. Level unchanged.",
    )
    _register(
        CADOptimizerDetectSmallPartsTinyCommand(),
        name="CADOptimizer.DetectSmallParts.Tiny",
        label="Detect Small Parts (F4) — Tiny (< 0.5 cm)",
        tool_tip="F4: report bbox-diagonal < 0.5 cm. Detection-only.",
    )
    _register(
        CADOptimizerDetectSmallPartsSmallCommand(),
        name="CADOptimizer.DetectSmallParts.Small",
        label="Detect Small Parts (F4) — Small (< 1.0 cm)",
        tool_tip="F4: report bbox-diagonal < 1.0 cm. Detection-only.",
    )
    _register(
        CADOptimizerDetectSmallPartsMediumCommand(),
        name="CADOptimizer.DetectSmallParts.Medium",
        label="Detect Small Parts (F4) — Medium (< 5.0 cm)",
        tool_tip="F4: report bbox-diagonal < 5.0 cm. Detection-only.",
    )
    _register(
        CADOptimizerMaterialInventoryCommand(),
        name="CADOptimizer.MaterialInventory",
        label="Material Inventory (F6)",
        tool_tip="F6: walk level for unique material asset inventory; "
                 "emits CSV + Output Log summary. Level unchanged.",
    )
    _register(
        CADOptimizerIntegratedReportCommand(),
        name="CADOptimizer.IntegratedReport",
        label="📊 Generate Integrated Report (F7)",
        tool_tip="F7: orchestrate F2/F3/F4/F6 + emit single integrated "
                 "markdown report (primary) + supporting CSVs. Use at "
                 "측정 박제 시점.",
    )
    _register(
        CADOptimizerApplyMetadataTagsCommand(),
        name="CADOptimizer.ApplyMetadataTags",
        label="🏷️ Apply F8 Metadata Tags",
        tool_tip="F8: 4-tier metadata tag 부여 (CADOpt_F8_Cull_High/Mid/"
                 "Review/Keep). Phase 3 visibility culling 대비. "
                 "Level dirty — save 필요. Idempotent.",
    )
    _register(
        CADOptimizerMergeActorsDryRunCommand(),
        name="CADOptimizer.MergeActors.DryRun",
        label="🔗 Merge Actors (Phase 2) — Dry Run",
        tool_tip="Phase 2: F3 fresh run + plan-only ISM 변환 시뮬레이션. "
                 "Level unchanged. Plan CSV 박제 (예상 drawcall 감소량 포함).",
    )
    _register(
        CADOptimizerMergeActorsApplyCommand(),
        name="CADOptimizer.MergeActors.Apply",
        label="🔗 Merge Actors (Phase 2) — APPLY",
        tool_tip="Phase 2: ISM 변환 실제 적용. BP_ISMHolder spawn + per-instance "
                 "transform 부여 + source actor batch destroy. Level dirty — "
                 "save 필요. Undo로 전체 revert. Dry Run 먼저 권장.",
    )
    _register(
        CADOptimizerOrganizeISMHoldersCommand(),
        name="CADOptimizer.OrganizeISMHolders",
        label="🗂️ Organize ISM Holders (Phase 2)",
        tool_tip="Phase 2: 기존 BP_ISMHolder들을 'ISM_Merged/' outliner folder로 "
                 "일괄 이동. 'CADOpt_P2_Merged_*' tag 보유 actor만 대상. "
                 "Idempotent. 이전 코드 버전으로 머지된 holder 정리용.",
    )

    unreal.ToolMenus.get().refresh_all_widgets()
