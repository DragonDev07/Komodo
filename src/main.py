import gi
import sys
import os
from loguru import logger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from .ui import Window

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("NM", "1.0")
from gi.repository import Gtk, Adw, Gio  # noqa: E402

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    "network_manager.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
)


class Application(Gtk.Application):
    """Main application class"""

    def __init__(self):
        logger.info("Initializing Application")
        super().__init__(
            application_id="dev.furthestdrop.networkmanager",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        """Create and present the main application window"""
        logger.info("Activating main window")
        window = Window(self)
        window.present()


def main():
    """Application entry point"""
    logger.info("Starting application")
    # Initialize Adwaita
    Adw.init()

    # Create and run application
    app = Application()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
