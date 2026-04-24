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

    unreal.ToolMenus.get().refresh_all_widgets()
