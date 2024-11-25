# src/utils/dialog.py

import gi
import threading
import queue

from loguru import logger

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib  # noqa: E402


def show_error_dialog(parent, message):
    """Show an error dialog with a given message"""
    logger.error(f"Showing error dialog: {message}")
    dialog = Adw.MessageDialog.new(parent, "Network Connection Error", message)
    dialog.add_response("ok", "OK")
    dialog.set_default_response("ok")
    dialog.present()


def show_error_dialog_with_callback(parent, message, completed_event):
    """Show an error dialog and signal when it's closed"""
    dialog = Adw.MessageDialog.new(parent, "Network Connection Error", message)
    dialog.add_response("ok", "OK")
    dialog.set_default_response("ok")

    def on_response(dialog, response):
        dialog.destroy()
        completed_event.set()

    dialog.connect("response", on_response)
    dialog.present()
    return False


def show_password_dialog(parent, ssid):
    """Show a password dialog for network connection

    Args:
        parent: Parent window
        ssid: Network SSID to connect to

    Returns:
        str: Password entered by user or None if cancelled
    """
    result_queue = queue.Queue()

    def create_dialog():
        dialog = Adw.MessageDialog.new(
            parent,
            f"Enter Password for {ssid}",
            "Please enter the network password to connect.",
        )

        # Add buttons
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("connect", "Connect")
        dialog.set_close_response("cancel")
        dialog.set_default_response("connect")

        # Create password entry
        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)
        password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        password_entry.set_hexpand(True)

        # Create show/hide password toggle
        show_password = Gtk.CheckButton(label="Show Password")
        show_password.connect(
            "toggled", lambda btn: password_entry.set_visibility(btn.get_active())
        )

        # Create container for entry and checkbox
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_spacing(10)
        content_box.append(password_entry)
        content_box.append(show_password)

        # Set custom widget
        dialog.set_extra_child(content_box)

        def on_response(dialog, response):
            if response == "connect":
                result_queue.put(password_entry.get_text())
            else:
                result_queue.put(None)
            dialog.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def dialog_thread():
        GLib.idle_add(create_dialog)

    # Start dialog in separate thread
    threading.Thread(target=dialog_thread, daemon=True).start()

    try:
        # Wait for result with timeout
        return result_queue.get(timeout=300)  # 5-minute timeout
    except queue.Empty:
        return None
