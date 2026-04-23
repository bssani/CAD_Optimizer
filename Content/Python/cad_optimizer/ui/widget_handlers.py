import unreal


_MAIN_PANEL_PATH = "/CAD_Optimizer/EditorWidgets/EUW_MainPanel"


def open_main_panel() -> None:
    widget_blueprint = unreal.load_asset(_MAIN_PANEL_PATH)
    if widget_blueprint is None:
        unreal.log_error(f"EUW not found at {_MAIN_PANEL_PATH}")
        return
    subsystem = unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem)
    subsystem.spawn_and_register_tab(widget_blueprint)
