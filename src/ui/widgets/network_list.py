import threading

import gi
from loguru import logger

from ...utils.dialog import show_error_dialog
from ...utils.nmcli import (
    connect_to_network,
    disconnect_from_network,
    get_active_network,
    get_network_names,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402


class NetworkList(Gtk.Box):
    """Widget displaying and managing the list of available networks"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        logger.debug("Initializing NetworkList")
        self.setup_layout()
        self.setup_styles()
        self.setup_signals()
        self.start_network_monitoring()

    def setup_layout(self):
        """Configure base layout and widgets"""
        # Base widget configuration
        self.set_spacing(5)
        self.set_homogeneous(False)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_margin_bottom(10)
        self.set_margin_end(10)

        # Create header box
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.header_box.set_spacing(5)
        self.header_box.set_homogeneous(False)
        self.header_box.set_hexpand(True)
        self.header_box.set_valign(Gtk.Align.START)

        # Create header label
        self.header_label = Gtk.Label()
        self.header_label.set_markup("<span size='x-large'>Network Name (SSID)</span>")
        self.header_label.set_halign(Gtk.Align.START)
        self.header_label.set_hexpand(True)
        self.header_box.append(self.header_label)

        # Create reload button
        self.reload_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.reload_button.set_tooltip_text("Reload Network List")
        self.reload_button.set_halign(Gtk.Align.END)
        self.reload_button.set_valign(Gtk.Align.CENTER)
        self.reload_button.add_css_class("flat")
        self.header_box.append(self.reload_button)

        # Create network list box
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(False)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_vexpand(True)

        # Create scrolled window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.scrolled_window.set_vexpand(True)
        self.scrolled_window.add_css_class("card")
        self.scrolled_window.set_child(self.list_box)

        self.connecting = False

        # Add main widgets
        self.append(self.header_box)
        self.append(self.scrolled_window)

    def setup_styles(self):
        """Setup custom CSS styles"""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .active-network {
                background: alpha(@accent_bg_color, 0.1);
                font-weight: bold;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def setup_signals(self):
        """Connect widget signals"""
        self.reload_button.connect("clicked", self.on_reload_button_clicked)
        self.list_box.connect("row-selected", self.on_network_selected)
        self.list_box.connect("row-activated", self.on_network_activated)

    def start_network_monitoring(self):
        """Start network monitoring and auto-refresh"""
        threading.Thread(target=self.load_networks, daemon=True).start()
        # Store the timer ID so we can remove it later
        self.refresh_source_id = GLib.timeout_add_seconds(
            5, self.on_reload_button_clicked, self.reload_button
        )

    def pause_monitoring(self):
        """Pause network monitoring"""
        if self.refresh_source_id:
            GLib.source_remove(self.refresh_source_id)
            self.refresh_source_id = None

    def resume_monitoring(self):
        """Resume network monitoring"""
        if not self.refresh_source_id:
            self.refresh_source_id = GLib.timeout_add_seconds(
                5, self.on_reload_button_clicked, self.reload_button
            )

    def on_reload_button_clicked(self, button):
        """Handle reload button clicks"""
        self.list_box.remove_all()
        threading.Thread(target=self.load_networks, daemon=True).start()
        threading.Thread(target=self._update_password_box, daemon=True).start()
        return True

    def on_network_selected(self, list_box, row):
        """Handle network selection"""
        if row is not None:
            ssid = self._get_ssid_from_row(row)
            self._update_network_details(ssid)

    def on_network_activated(self, list_box, row):
        """Handle network activation (double-click/Enter)"""
        if row is not None and not self.connecting:
            self.connecting = True
            self.pause_monitoring()  # Pause monitoring while connecting
            ssid = self._get_ssid_from_row(row)
            threading.Thread(
                target=self._handle_network_activation_with_resume,
                args=(ssid,),
                daemon=True,
            ).start()

    def _handle_network_activation_with_resume(self, ssid):
        """Wrapper to handle network activation and resume monitoring"""
        try:
            self._handle_network_activation(ssid)
        finally:
            self.connecting = False
            GLib.idle_add(self.resume_monitoring)  # Resume monitoring when done

    def load_networks(self):
        """Load network list in background thread"""
        network_names = get_network_names()
        unique_network_names = set(network_names)
        active_network = get_active_network()
        GLib.idle_add(self.update_list_box, unique_network_names, active_network)

    def update_list_box(self, unique_network_names, active_network):
        """Update network list UI"""
        network_list = list(unique_network_names)
        if active_network in network_list:
            network_list.remove(active_network)
            network_list.insert(0, active_network)

        active_network_row = None
        for name in network_list:
            if name:
                row = self._create_network_row(name, name == active_network)
                if name == active_network:
                    active_network_row = row

        if active_network_row:
            self.list_box.select_row(active_network_row)

    def _create_network_row(self, name, is_active):
        """Create a network list row"""
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(6)

        label = Gtk.Label(label=name)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)

        if is_active:
            icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            icon.set_margin_start(6)
            box.append(icon)
            row.add_css_class("active-network")

        box.append(label)
        row.set_child(box)
        self.list_box.append(row)
        return row

    def _get_ssid_from_row(self, row):
        """Extract SSID from list box row"""
        box = row.get_child()
        label = box.get_last_child()
        return label.get_text()

    def _update_network_details(self, ssid):
        """Update network details panel"""
        parent = self.get_root()
        if parent:
            basic_page = (
                parent.get_content()
                .get_last_child()
                .get_first_child()
                .get_first_child()
            )
            details_box = basic_page.right_box
            details_box.update_network_info(ssid)

    def _update_password_box(self):
        """Update password box"""
        parent = self.get_root()
        if parent:
            basic_page = (
                parent.get_content()
                .get_last_child()
                .get_first_child()
                .get_first_child()
            )
            password_box = basic_page.password_entry
            password_box.refresh_password()

    def _handle_network_activation(self, ssid):
        """Handle network activation/deactivation"""
        try:
            active_network = get_active_network()

            if ssid == active_network:
                if not disconnect_from_network(ssid):
                    return
            else:
                if not connect_to_network(ssid):
                    return
        except Exception as e:
            GLib.idle_add(show_error_dialog, self.get_root(), str(e))
        finally:
            GLib.idle_add(self._refresh_ui)

    def _refresh_ui(self):
        """Refresh network list and password box"""
        self.on_reload_button_clicked(self.reload_button)
        parent = self.get_root()
        if parent:
            basic_page = (
                parent.get_content()
                .get_last_child()
                .get_first_child()
                .get_first_child()
            )
            password_box = basic_page.password_entry
            password_box.refresh_password()
        return False
