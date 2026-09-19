"""
Sam Desktop HUD Launcher.
Runs the floating desktop HUD interface with live connection to Sam Core.
"""
from sam_clients.windows_hud.gui import HUDWindow


def main() -> None:
    print("Launching Sam Desktop HUD Interface...")
    hud = HUDWindow()
    root = hud.build_ui()
    # Add title and keep-on-top attribute for floating overlay behavior
    root.attributes("-topmost", True)
    root.mainloop()

if __name__ == "__main__":
    main()
