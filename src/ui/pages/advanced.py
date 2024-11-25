import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk  # noqa: E402


class AdvancedPage(Gtk.Box):
    """Advanced network management page (currently just a placeholder)"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.setup_layout()

    def setup_layout(self):
        # Configure base layout
        self.set_spacing(0)
        self.set_homogeneous(True)

        # Create placeholder label
        label = Gtk.Label(label="Use the terminal you moron.")
        self.append(label)
