import gi

from ..widgets import DetailsBox, NetworkList, PasswordBox

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk  # noqa: E402


class BasicPage(Gtk.Box):
    """Basic network management page with network list, password and details"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.setup_layout()

    def setup_layout(self):
        # Configure base layout
        self.set_spacing(5)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_homogeneous(False)

        # Create horizontal split box
        self.split_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.split_box.set_homogeneous(True)
        self.split_box.set_spacing(5)

        # Create left and right boxes
        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.left_box.set_spacing(5)
        self.left_box.set_vexpand(True)
        self.left_box.set_homogeneous(False)

        self.right_box = DetailsBox()

        # Create network list and password widgets
        self.network_list = NetworkList()
        self.password_entry = PasswordBox()

        # Add widgets to left container
        self.left_box.append(self.network_list)
        self.left_box.append(self.password_entry)

        # Add boxes to split container
        self.split_box.append(self.left_box)
        self.split_box.append(self.right_box)

        # Add split box to main container
        self.append(self.split_box)
