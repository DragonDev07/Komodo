import gi

from .header import Header

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402


class Window(Adw.ApplicationWindow):
    """Main application window component"""

    def __init__(self, app):
        super().__init__(application=app)
        self.setup_window()
        self.setup_layout()

    def setup_window(self):
        """Configure basic window properties"""
        self.set_default_size(600, 400)

    def setup_layout(self):
        """Setup the window layout with header and content"""
        # Create header component
        header = Header()

        # Create ViewStack container
        view_stack_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        view_stack_box.append(header.view_stack)

        # Create and setup main container
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_container.append(header)
        main_container.append(view_stack_box)

        # Set window content
        self.set_content(main_container)
