import unreal


def _register_menu() -> None:
    menus = unreal.ToolMenus.get()
    tools_menu = menus.extend_menu("LevelEditor.MainMenu.Tools")

    entry = unreal.ToolMenuEntry(
        name="CADOptimizer.OpenMain",
        type=unreal.MultiBlockType.MENU_ENTRY,
    )
    entry.set_label("CAD Optimizer")
    entry.set_tool_tip("GMTCK PCVR mesh optimization tool")
    entry.set_string_command(
        type=unreal.ToolMenuStringCommandType.PYTHON,
        custom_type="",
        string='unreal.log("CAD Optimizer menu clicked")',
    )

    tools_menu.add_menu_entry("CADOptimizer", entry)
    menus.refresh_all_widgets()


unreal.log("CAD_Optimizer plugin loaded")
_register_menu()
