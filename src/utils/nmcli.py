from typing import List

import gi
from loguru import logger

from .dialog import show_error_dialog, show_password_dialog

gi.require_version("NM", "1.0")
gi.require_version("Gtk", "4.0")

from gi.repository import NM, GLib  # noqa: E402

# Initialize the NetworkManager client
client = NM.Client.new(None)


# Function to get the list of available network SSIDs
def get_network_names() -> List[str]:
    """Get list of available network SSIDs"""
    logger.debug("Entered get_network_names()")

    try:
        # Get all devices
        logger.info("Forcing network rescan and fetching available SSIDs")
        devices = client.get_devices()

        # Filter for Wi-Fi devices
        logger.debug(f"Found devices: {devices}")
        wifi_devices = [dev for dev in devices if isinstance(dev, NM.DeviceWifi)]

        logger.debug(f"Filtered Wi-Fi devices: {wifi_devices}")

        # Set to store unique network names
        networks = set()

        # Iterate over Wi-Fi devices
        for dev in wifi_devices:
            logger.info(f"Requesting network scan on device: {dev.get_iface()}")

            # Force a network rescan
            dev.request_scan(None)

            # Get access points after rescan
            access_points = dev.get_access_points()
            logger.debug(f"Found access points: {access_points}")

            # Iterate over access points and get SSID
            for ap in access_points:
                # Get SSID as GBytes and decode to string
                ssid_gbytes = ap.get_ssid()

                if ssid_gbytes is not None:
                    try:
                        # Decode SSID and add to set
                        ssid = ssid_gbytes.get_data().decode("utf-8")
                        # logger.debug(f"Found SSID: {ssid}")
                        networks.add(ssid)

                    # Handle decoding errors
                    except UnicodeDecodeError as ude:
                        logger.warning(f"Failed to decode SSID for access point: {ude}")

                else:
                    logger.warning("Access point with no SSID encountered")

        # Convert set to list and return
        logger.info(f"Found {len(networks)} networks after rescan")
        return list(networks)

    # Handle exceptions
    except Exception as e:
        logger.exception(f"Error getting network names: {e}")
        return []

    # Cleanup
    finally:
        logger.debug("Exiting get_network_names()")


# Function to get the currently active network SSID
def get_active_network() -> str:
    """Get currently active network SSID"""
    logger.debug("Entered get_active_network()")

    try:
        # Get active connections
        logger.info("Fetching active network")
        active_connections = client.get_active_connections()
        logger.debug(f"Active connections: {active_connections}")

        # Iterate over active connections
        for active_conn in active_connections:
            # Check if connection is Wi-Fi
            if active_conn.get_connection_type() == NM.SETTING_WIRELESS_SETTING_NAME:
                logger.debug(
                    f"Processing Wi-Fi active connection: {active_conn.get_id()}"
                )

                # Get devices in active connection
                devices = active_conn.get_devices()
                logger.debug(f"Devices in active connection: {devices}")

                # Iterate over devices
                for dev in devices:
                    # Check if device is Wi-Fi
                    if isinstance(dev, NM.DeviceWifi):
                        # Get active access point
                        ap = dev.get_active_access_point()

                        # Get SSID from access point
                        if ap:
                            # Get SSID as GBytes and decode to string
                            ssid_gbytes = ap.get_ssid()

                            if ssid_gbytes is not None:
                                try:
                                    # Decode SSID and return
                                    ssid = ssid_gbytes.get_data().decode("utf-8")

                                    logger.info(f"Active network SSID: {ssid}")
                                    return ssid

                                # Handle decoding errors
                                except UnicodeDecodeError as ude:
                                    logger.warning(
                                        f"Failed to decode active SSID: {ude}"
                                    )

                            # Handle access points with no SSID
                            else:
                                logger.debug("No SSID found for active access point")

                        # Handle no active access point
                        else:
                            logger.debug("No active access point found")

        logger.info("No active Wi-Fi network")
        return ""

    # Handle exceptions
    except Exception as e:
        logger.exception(f"Error getting active network: {e}")
        return ""

    # Cleanup
    finally:
        logger.debug("Exiting get_active_network()")


def connect_to_network(ssid: str) -> bool:
    """Connect to a network with the given SSID using NetworkManager API."""
    logger.debug(f"Attempting to connect to network: {ssid}")

    try:
        # Get WiFi device
        devices = client.get_devices()
        wifi_device = next(
            (dev for dev in devices if isinstance(dev, NM.DeviceWifi)), None
        )

        if not wifi_device:
            logger.error("No WiFi device found")
            return False

        # Find matching access point
        ap = None
        for access_point in wifi_device.get_access_points():
            ap_ssid = access_point.get_ssid()
            if ap_ssid and ap_ssid.get_data().decode("utf-8") == ssid:
                ap = access_point
                break

        if not ap:
            logger.error(f"Network {ssid} not found")
            return False

        # Check existing connections
        connections = client.get_connections()
        existing_conn = None
        for conn in connections:
            if (
                conn.get_connection_type() == "802-11-wireless"
                and conn.get_setting_wireless().get_ssid().get_data().decode("utf-8")
                == ssid
            ):
                existing_conn = conn
                break

        if existing_conn:
            logger.info(f"Using existing connection for {ssid}")
            client.activate_connection_async(
                existing_conn, wifi_device, ap.get_path(), None, None
            )
            return True

        # Get raw SSID bytes for new connection
        ssid_bytes = ap.get_ssid().get_data()
        ssid_gbytes = GLib.Bytes.new(ssid_bytes)

        # Create new connection
        connection = NM.SimpleConnection.new()
        s_con = NM.SettingConnection.new()
        s_con.set_property(NM.SETTING_CONNECTION_ID, ssid)
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, "802-11-wireless")

        s_wifi = NM.SettingWireless.new()
        s_wifi.set_property(NM.SETTING_WIRELESS_SSID, ssid_gbytes)
        s_wifi.set_property(NM.SETTING_WIRELESS_MODE, "infrastructure")

        connection.add_setting(s_con)
        connection.add_setting(s_wifi)

        # Check if network is secured
        flags = ap.get_flags()
        NM_80211ApFlags = getattr(NM, "80211ApFlags", None)

        if flags & NM_80211ApFlags.PRIVACY:
            password = show_password_dialog(None, ssid)
            if not password:
                logger.info("Password entry cancelled")
                return False

            s_wsec = NM.SettingWirelessSecurity.new()
            s_wsec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, "wpa-psk")
            s_wsec.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, password)
            connection.add_setting(s_wsec)

        # Add and activate connection
        def on_connection_added(client, result, user_data):
            try:
                new_connection = client.add_connection_finish(result)
                client.activate_connection_async(
                    new_connection, wifi_device, ap.get_path(), None, None
                )
            except Exception as e:
                logger.error(f"Failed to add connection: {e}")
                show_error_dialog(None, "Failed to connect: Invalid password")

        client.add_connection_async(connection, True, None, on_connection_added, None)
        return True

    except Exception as e:
        logger.error(f"Error connecting to network: {e}")
        return False


# Function to disconnect from a network
def disconnect_from_network(ssid: str) -> bool:
    """Disconnect from network"""
    logger.debug(f"Entered disconnect_from_network() with SSID: {ssid}")

    try:
        # Get active connections
        logger.info(f"Attempting to disconnect from network: {ssid}")
        active_connections = client.get_active_connections()
        logger.debug(f"Active connections: {active_connections}")

        # Iterate over active connections
        for active_conn in active_connections:
            # Check if connection is Wi-Fi
            if active_conn.get_connection_type() == NM.SETTING_WIRELESS_SETTING_NAME:
                # Get devices in active connection
                devices = active_conn.get_devices()
                logger.debug(f"Devices in active connection: {devices}")

                # Iterate over devices
                for dev in devices:
                    # Check if device is Wi-Fi
                    if isinstance(dev, NM.DeviceWifi):
                        # Get active access point
                        ap = dev.get_active_access_point()

                        if ap:
                            # Get SSID from access point
                            ssid_gbytes = ap.get_ssid()

                            if ssid_gbytes is not None:
                                try:
                                    # Decode SSID
                                    ap_ssid = ssid_gbytes.get_data().decode("utf-8")
                                    logger.debug(f"Active connection SSID: {ap_ssid}")

                                # Handle decoding errors
                                except UnicodeDecodeError as ude:
                                    logger.warning(
                                        f"Failed to decode SSID for active connection: {ude}"
                                    )
                                    continue

                                # If SSID matches, deactivate connection
                                if ap_ssid == ssid:
                                    client.deactivate_connection(active_conn)
                                    logger.info(
                                        f"Successfully disconnected from {ssid}"
                                    )
                                    return True

                            # Handle access points with no SSID
                            else:
                                logger.warning("Active access point with no SSID")

        logger.error(f"Network {ssid} is not connected")
        return False

    # Handle exceptions
    except Exception as e:
        logger.exception(f"Error disconnecting from network {ssid}: {e}")
        return False

    # Cleanup
    finally:
        logger.debug("Exiting disconnect_from_network()")


def get_security_type(ap):
    """Determine the security type of an access point"""
    logger.debug(f"Entered get_security_type() for AP: {ap}")

    try:
        flags = ap.get_flags()
        wpa_flags = ap.get_wpa_flags()
        rsn_flags = ap.get_rsn_flags()
        NM_80211ApFlags = getattr(NM, "80211ApFlags", None)
        NM_80211ApSecurityFlags = getattr(NM, "80211ApSecurityFlags", None)

        if NM_80211ApFlags is None or NM_80211ApSecurityFlags is None:
            logger.error(
                "Failed to retrieve 80211ApFlags or 80211ApSecurityFlags from NM"
            )
            return "Unknown"

        if flags & NM_80211ApFlags.PRIVACY:
            if rsn_flags != NM_80211ApSecurityFlags.NONE:
                logger.debug("Security type: WPA2")
                return "WPA2"

            elif wpa_flags != NM_80211ApSecurityFlags.NONE:
                logger.debug("Security type: WPA")
                return "WPA"

            else:
                logger.debug("Security type: WEP")
                return "WEP"

        else:
            logger.debug("Security type: Open")
            return "Open"

    finally:
        logger.debug("Exiting get_security_type()")


def get_network_info(ssid: str) -> dict:
    """Get detailed network information for a given SSID"""
    logger.debug(f"Entered get_network_info() with SSID: {ssid}")

    try:
        logger.info(f"Fetching network info for SSID: {ssid}")
        devices = client.get_devices()
        logger.debug(f"Found devices: {devices}")

        wifi_devices = [dev for dev in devices if isinstance(dev, NM.DeviceWifi)]
        logger.debug(f"Wi-Fi devices: {wifi_devices}")

        if not wifi_devices:
            logger.error("No Wi-Fi devices found")
            return {}

        wifi_device = wifi_devices[0]
        logger.debug(f"Using Wi-Fi device: {wifi_device.get_iface()}")

        access_points = wifi_device.get_access_points()
        logger.debug(f"Access points: {access_points}")
        target_ap = None

        for ap in access_points:
            ssid_gbytes = ap.get_ssid()
            if ssid_gbytes is not None:
                try:
                    ap_ssid = ssid_gbytes.get_data().decode("utf-8")
                    logger.debug(f"Found access point SSID: {ap_ssid}")
                except UnicodeDecodeError as ude:
                    logger.warning(f"Failed to decode SSID for access point: {ude}")
                    continue

                if ap_ssid == ssid:
                    target_ap = ap
                    logger.info(f"Target access point found: {ap_ssid}")
                    break
            else:
                logger.warning("Access point with no SSID encountered")

        if not target_ap:
            logger.error(f"Access point '{ssid}' not found")
            return {}

        info = {
            "ssid": ssid,
            "signal": target_ap.get_strength(),
            "security": get_security_type(target_ap),
            "is_active": False,
            "device": None,
        }

        active_network = get_active_network()
        if ssid == active_network:
            info["is_active"] = True
            info["device"] = wifi_device.get_iface()
            logger.info(f"Network {ssid} is active on device {info['device']}")
        else:
            logger.info(f"Network {ssid} is not currently active")

        logger.debug(f"Network info for {ssid}: {info}")
        return info

    except Exception as e:
        logger.exception(f"Error getting network info for {ssid}: {e}")
        return {}

    finally:
        logger.debug("Exiting get_network_info()")


def get_device_info(device_name: str) -> dict:
    """Get detailed device information including IP addresses and MAC"""
    logger.debug(f"Entered get_device_info() with device_name: {device_name}")

    try:
        logger.info(f"Fetching device info for: {device_name}")
        device = client.get_device_by_iface(device_name)
        if not device:
            logger.error(f"Device {device_name} not found")
            return {}

        ip4config = device.get_ip4_config()
        ip6config = device.get_ip6_config()
        hw_address = device.get_permanent_hw_address()
        logger.debug(
            f"IP4 Config: {ip4config}, IP6 Config: {ip6config}, MAC: {hw_address}"
        )

        info = {
            "ipv4": ip4config.get_addresses()[0].get_address()
            if ip4config and ip4config.get_addresses()
            else "Not connected",
            "ipv6": ip6config.get_addresses()[0].get_address()
            if ip6config and ip6config.get_addresses()
            else "Not connected",
            "mac": hw_address or "Unknown",
        }

        logger.debug(f"Device info for {device_name}: {info}")
        return info

    except Exception as e:
        logger.exception(f"Error getting device info for {device_name}: {e}")
        return {}

    finally:
        logger.debug("Exiting get_device_info()")


def get_active_password() -> str:
    """Get password for currently active network connection"""
    logger.debug("Entered get_active_password()")

    try:
        logger.info("Fetching password for active network")
        active_connections = client.get_active_connections()
        logger.debug(f"Active connections: {active_connections}")

        for active_conn in active_connections:
            if active_conn.get_connection_type() == NM.SETTING_WIRELESS_SETTING_NAME:
                settings_connection = active_conn.get_connection()
                logger.debug(f"Settings connection: {settings_connection}")

                secrets_variant = settings_connection.get_secrets(
                    NM.SETTING_WIRELESS_SECURITY_SETTING_NAME, None
                )
                logger.debug(f"Secrets variant: {secrets_variant}")

                if secrets_variant is None:
                    logger.error("No secrets found for the connection")
                    continue

                try:
                    secrets = secrets_variant.unpack()
                    logger.debug(f"Unpacked secrets: {secrets}")
                except Exception as ue:
                    logger.error(f"Failed to unpack secrets: {ue}")
                    continue

                wireless_secrets = secrets.get(
                    NM.SETTING_WIRELESS_SECURITY_SETTING_NAME, {}
                )
                password = wireless_secrets.get(NM.SETTING_WIRELESS_SECURITY_PSK)

                if password:
                    logger.info("Successfully retrieved network password")
                    return password

        logger.info("No active Wi-Fi network with password found")
        return ""

    except Exception as e:
        logger.exception(f"Error getting network password: {e}")
        return ""

    finally:
        logger.debug("Exiting get_active_password()")
