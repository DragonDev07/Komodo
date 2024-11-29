import os
import sys
import gi
from loguru import logger
from .ui import Window

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("NM", "1.0")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

# Configure loguru
logger.add(
    "Komodo.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
)


class Application(Gtk.Application):
    """Main application class"""

    def __init__(self):
        logger.debug("Entered Application.__init__()")
        try:
            logger.info("Initializing Application")
            super().__init__(
                application_id="dev.furthestdrop.Komodo",
                flags=Gio.ApplicationFlags.FLAGS_NONE,
            )
            logger.debug("Application initialized successfully")
        except Exception as e:
            logger.exception(f"Exception during Application initialization: {e}")
            raise
        finally:
            logger.debug("Exiting Application.__init__()")

    def do_activate(self):
        """Create and present the main application window"""
        logger.debug("Entered Application.do_activate()")
        try:
            logger.info("Activating main window")
            window = Window(self)
            window.present()
            logger.debug("Main window presented")
        except Exception as e:
            logger.exception(f"Exception during main window activation: {e}")
            raise
        finally:
            logger.debug("Exiting Application.do_activate()")


def main():
    """Application entry point"""
    logger.debug("Entered main()")
    try:
        logger.info("Starting application")
        # Initialize Adwaita
        logger.debug("Initializing Adwaita")
        Adw.init()
        logger.debug("Adwaita initialized")

        # Create and run application
        app = Application()
        result = app.run(sys.argv)
        logger.info(f"Application exited with code {result}")
        return result
    except Exception as e:
        logger.exception(f"Unhandled exception in main: {e}")
        return 1
    finally:
        logger.debug("Exiting main()")


if __name__ == "__main__":
    sys.exit(main())
