import gi
from .pages import AdvancedPage, BasicPage

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402


class Header(Gtk.Box):
    """Header component with view switcher for navigation"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        # Configure base layout
        self.set_spacing(0)
        self.set_valign(Gtk.Align.START)
        self.set_halign(Gtk.Align.FILL)
        self.set_homogeneous(True)

        # Create the primary HeaderBar
        self.header_bar = Adw.HeaderBar()
        self.header_bar.set_show_end_title_buttons(True)
        self.header_bar.set_show_title(True)

        # Create the ViewSwitcher for navigation
        self.view_switcher = Adw.ViewSwitcher()
        self.view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        self.view_switcher.set_hexpand(True)

        # Create ViewStack to hold pages
        self.view_stack = Adw.ViewStack()

        # Create and add pages
        self.basic_page = BasicPage()
        self.advanced_page = AdvancedPage()

        self.view_stack.add_titled_with_icon(
            self.basic_page, "basic", "Basic", "network"
        )
        self.view_stack.add_titled_with_icon(
            self.advanced_page, "advanced", "Advanced", "settings"
        )

        # Connect ViewStack to ViewSwitcher
        self.view_switcher.set_stack(self.view_stack)

        # Set ViewSwitcher as HeaderBar title
        self.header_bar.set_title_widget(self.view_switcher)

        # Add HeaderBar to main container
        self.append(self.header_bar)
