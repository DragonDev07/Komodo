import gi
import subprocess
import threading

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib  # noqa: E402


class DetailsBox(Gtk.Box):
    """Widget displaying detailed network information"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.setup_layout()
        self.create_labels()

    def setup_layout(self):
        """Configure base layout and containers"""
        # Base box configuration
        self.set_spacing(5)
        self.set_homogeneous(False)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_margin_start(10)

        # Create header box
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.header_box.set_spacing(5)
        self.header_box.set_homogeneous(False)
        self.header_box.set_hexpand(True)
        self.header_box.set_valign(Gtk.Align.START)

        # Create header label
        self.header_label = Gtk.Label()
        self.header_label.set_margin_top(5)
        self.header_label.set_markup("<span size='x-large'>Details</span>")
        self.header_label.set_halign(Gtk.Align.START)
        self.header_label.set_hexpand(True)
        self.header_box.append(self.header_label)

        # Create info box
        self.info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.info_box.set_spacing(5)
        self.info_box.set_margin_top(5)
        self.info_box.set_homogeneous(False)
        self.info_box.set_vexpand(True)
        self.info_box.set_hexpand(True)
        self.info_box.add_css_class("card")

        # Add containers to main box
        self.append(self.header_box)
        self.append(self.info_box)

    def create_labels(self):
        """Create and configure network information labels"""
        # Create labels for network information
        self.ssid_label = Gtk.Label()
        self.signal_label = Gtk.Label()
        self.security_label = Gtk.Label()
        self.ipv4_label = Gtk.Label()
        self.ipv6_label = Gtk.Label()
        self.mac_label = Gtk.Label()

        # Configure all labels
        for label in [
            self.ssid_label,
            self.signal_label,
            self.security_label,
            self.ipv4_label,
            self.ipv6_label,
            self.mac_label,
        ]:
            label.set_halign(Gtk.Align.START)
            label.set_margin_start(10)
            label.set_margin_end(10)
            label.set_margin_top(10)
            label.set_margin_bottom(10)
            self.info_box.append(label)

    def update_network_info(self, ssid):
        """Update network information display"""
        if not ssid:
            self.clear_info()
            return

        # Start a new thread to fetch network information
        threading.Thread(
            target=self._fetch_network_info, args=(ssid,), daemon=True
        ).start()

    def _fetch_network_info(self, ssid):
        """Fetch network information in background thread"""
        try:
            # Get basic wifi information
            wifi_result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                stdout=subprocess.PIPE,
                text=True,
            )

            # Initialize variables
            signal = "N/A"
            security = "N/A"

            # Parse wifi information
            for line in wifi_result.stdout.splitlines():
                fields = line.split(":")
                if len(fields) >= 3 and fields[0] == ssid:
                    signal = fields[1]
                    security = fields[2] or "None"
                    break

            # Get connection details if this is the active connection
            connection_result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"],
                stdout=subprocess.PIPE,
                text=True,
            )

            is_active = False
            device = None

            for line in connection_result.stdout.splitlines():
                if line.startswith(f"{ssid}:"):
                    is_active = True
                    device = line.split(":")[1]
                    break

            # Update basic information in main thread
            GLib.idle_add(self.ssid_label.set_markup, f"<b>SSID:</b> {ssid}")
            GLib.idle_add(
                self.signal_label.set_markup, f"<b>Signal Strength:</b> {signal}%"
            )
            GLib.idle_add(
                self.security_label.set_markup, f"<b>Security:</b> {security}"
            )

            # If active connection, get more details
            if is_active and device:
                self._fetch_device_info(device)
            else:
                self._show_disconnected_info()

        except subprocess.SubprocessError:
            # Update UI in main thread
            GLib.idle_add(self.clear_info)

    def _fetch_device_info(self, device):
        """Fetch and update device-specific information"""
        device_result = subprocess.run(
            [
                "nmcli",
                "-t",
                "-f",
                "IP4.ADDRESS,IP6.ADDRESS,GENERAL.HWADDR",
                "device",
                "show",
                device,
            ],
            stdout=subprocess.PIPE,
            text=True,
        )

        ipv4 = "Not connected"
        ipv6 = "Not connected"
        mac = "Unknown"

        for line in device_result.stdout.splitlines():
            if line.startswith("IP4.ADDRESS"):
                ipv4 = line.split(":")[1].split("/")[0]
            elif line.startswith("IP6.ADDRESS"):
                ipv6 = line.split(":")[1].split("/")[0]
            elif line.startswith("GENERAL.HWADDR"):
                mac = line.split(":")[1]

        # Update UI in main thread
        GLib.idle_add(self.ipv4_label.set_markup, f"<b>IPv4 Address:</b> {ipv4}")
        GLib.idle_add(self.ipv6_label.set_markup, f"<b>IPv6 Address:</b> {ipv6}")
        GLib.idle_add(self.mac_label.set_markup, f"<b>MAC Address:</b> {mac}")

    def _show_disconnected_info(self):
        """Show disconnected state in UI"""
        GLib.idle_add(self.ipv4_label.set_markup, "<b>IPv4 Address:</b> Not connected")
        GLib.idle_add(self.ipv6_label.set_markup, "<b>IPv6 Address:</b> Not connected")
        GLib.idle_add(self.mac_label.set_markup, "<b>MAC Address:</b> N/A")

    def clear_info(self):
        """Clear all network information labels"""
        for label in [
            self.ssid_label,
            self.signal_label,
            self.security_label,
            self.ipv4_label,
            self.ipv6_label,
            self.mac_label,
        ]:
            label.set_text("")
