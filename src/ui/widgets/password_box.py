import gi
import threading
import subprocess

from ...utils.nmcli import get_active_password

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib  # noqa: E402


class PasswordBox(Gtk.Box):
    """Widget for displaying and managing network passwords"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.setup_layout()
        self.setup_password_entry()

        # Start a thread to load the password
        threading.Thread(target=self.load_password, daemon=True).start()

        # Auto-refresh every 15 seconds
        GLib.timeout_add_seconds(15, self.refresh_password)

    def setup_layout(self):
        """Configure base layout and containers"""
        self.set_spacing(5)
        self.set_homogeneous(False)
        self.set_vexpand(False)
        self.set_hexpand(True)
        self.set_margin_top(10)
        self.set_margin_end(10)
        self.set_valign(Gtk.Align.END)

        # Create header label
        self.header_label = Gtk.Label()
        self.header_label.set_markup("<span size='x-large'>Password</span>")
        self.header_label.set_halign(Gtk.Align.START)
        self.header_label.set_hexpand(True)

        # Create entry box container
        self.entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.entry_box.set_homogeneous(False)
        self.entry_box.set_hexpand(True)
        self.entry_box.set_valign(Gtk.Align.START)

        # Add containers to main box
        self.append(self.header_label)
        self.append(self.entry_box)

    def setup_password_entry(self):
        """Create and configure password entry and visibility toggle"""
        # Create password entry
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_hexpand(True)
        self.password_entry.set_editable(False)
        self.entry_box.append(self.password_entry)

        # Create visibility toggle button
        self.visibility_button = Gtk.ToggleButton.new()
        self.visibility_button_icon = Gtk.Image.new_from_icon_name(
            "view-reveal-symbolic"
        )
        self.visibility_button.set_child(self.visibility_button_icon)
        self.visibility_button.set_tooltip_text("Show Password")
        self.visibility_button.set_margin_start(10)
        self.visibility_button.set_halign(Gtk.Align.END)
        self.visibility_button.set_valign(Gtk.Align.CENTER)
        self.visibility_button.add_css_class("flat")
        self.visibility_button.connect("toggled", self.on_visibility_button_toggled)
        self.entry_box.append(self.visibility_button)

    def on_visibility_button_toggled(self, button):
        """Handle password visibility toggle button clicks"""
        if button.get_active():
            # Try to authenticate using pkexec
            try:
                result = subprocess.run(
                    ["pkexec", "/bin/true"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                if result.returncode == 0:
                    # Authentication successful
                    self.password_entry.set_visibility(True)
                    self.visibility_button_icon.set_from_icon_name(
                        "view-conceal-symbolic"
                    )
                    self.visibility_button.set_tooltip_text("Hide Password")
                else:
                    # Authentication failed or cancelled
                    button.set_active(False)

            except subprocess.SubprocessError:
                # Handle authentication error
                button.set_active(False)

        else:
            # Hide password
            self.password_entry.set_visibility(False)
            self.visibility_button_icon.set_from_icon_name("view-reveal-symbolic")
            self.visibility_button.set_tooltip_text("Show Password")

    def load_password(self):
        """Load password in background thread"""
        password = get_active_password()
        GLib.idle_add(self.update_password, password)

    def update_password(self, password):
        """Update password entry text and state"""
        if password and password.strip():
            self.password_entry.set_text(
                password.split(":")[1] if ":" in password else password
            )
            self.password_entry.set_editable(False)
        else:
            self.password_entry.set_text("")
            self.password_entry.set_editable(True)

    def refresh_password(self):
        """Manually trigger password refresh"""
        threading.Thread(target=self.load_password, daemon=True).start()
