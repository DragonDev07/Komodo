from typing import List, Optional

import gi
from loguru import logger

from .dialog import show_error_dialog, show_password_dialog

gi.require_version("NM", "1.0")
gi.require_version("Gtk", "4.0")
from gi.repository import NM, Gtk  # noqa: E402

# Initialize the NetworkManager client
client = NM.Client.new(None)


def get_network_names() -> List[str]:
    """Get list of available network SSIDs"""
    logger.debug("Entered get_network_names()")
    try:
        logger.info("Forcing network rescan and fetching available SSIDs")
        devices = client.get_devices()
        logger.debug(f"Found devices: {devices}")
        wifi_devices = [dev for dev in devices if isinstance(dev, NM.DeviceWifi)]
        logger.debug(f"Filtered Wi-Fi devices: {wifi_devices}")
        networks = set()
        for dev in wifi_devices:
            logger.info(f"Requesting network scan on device: {dev.get_iface()}")
            # Force a network rescan
            dev.request_scan(None)
            # Get access points after rescan
            access_points = dev.get_access_points()
            logger.debug(f"Found access points: {access_points}")
            for ap in access_points:
                ssid_gbytes = ap.get_ssid()
                if ssid_gbytes is not None:
                    try:
                        ssid = ssid_gbytes.get_data().decode("utf-8")
                        logger.debug(f"Found SSID: {ssid}")
                        networks.add(ssid)
                    except UnicodeDecodeError as ude:
                        logger.warning(f"Failed to decode SSID for access point: {ude}")
                else:
                    logger.warning("Access point with no SSID encountered")
        logger.info(f"Found {len(networks)} networks after rescan")
        return list(networks)
    except Exception as e:
        logger.exception(f"Error getting network names: {e}")
        return []
    finally:
        logger.debug("Exiting get_network_names()")


def get_active_network() -> str:
    """Get currently active network SSID"""
    logger.debug("Entered get_active_network()")
    try:
        logger.info("Fetching active network")
        active_connections = client.get_active_connections()
        logger.debug(f"Active connections: {active_connections}")
        for active_conn in active_connections:
            if active_conn.get_connection_type() == NM.SETTING_WIRELESS_SETTING_NAME:
                logger.debug(
                    f"Processing Wi-Fi active connection: {active_conn.get_id()}"
                )
                devices = active_conn.get_devices()
                logger.debug(f"Devices in active connection: {devices}")
                for dev in devices:
                    if isinstance(dev, NM.DeviceWifi):
                        ap = dev.get_active_access_point()
                        if ap:
                            ssid_gbytes = ap.get_ssid()
                            if ssid_gbytes is not None:
                                try:
                                    ssid = ssid_gbytes.get_data().decode("utf-8")
                                    logger.info(f"Active network SSID: {ssid}")
                                    return ssid
                                except UnicodeDecodeError as ude:
                                    logger.warning(
                                        f"Failed to decode active SSID: {ude}"
                                    )
                            else:
                                logger.debug("No SSID found for active access point")
                        else:
                            logger.debug("No active access point found")
        logger.info("No active Wi-Fi network")
        return ""
    except Exception as e:
        logger.exception(f"Error getting active network: {e}")
        return ""
    finally:
        logger.debug("Exiting get_active_network()")


def connect_to_network(
    ssid: str, parent: Gtk.Window, password: Optional[str] = None
) -> bool:
    """
    Connect to a network with an optional password.
    If password is not provided for a secured network, prompt the user.
    """
    logger.debug(f"Entered connect_to_network() with SSID: {ssid}")
    try:
        logger.info(f"Attempting to connect to network: {ssid}")
        devices = client.get_devices()
        logger.debug(f"Found devices: {devices}")
        wifi_devices = [dev for dev in devices if isinstance(dev, NM.DeviceWifi)]
        logger.debug(f"Wi-Fi devices: {wifi_devices}")
        if not wifi_devices:
            logger.error("No Wi-Fi devices found")
            show_error_dialog(parent, "No Wi-Fi devices available.")
            return False
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
            show_error_dialog(parent, f"Access point '{ssid}' not found.")
            return False

        logger.debug("Creating Wi-Fi connection settings")
        settings = NM.SimpleConnection.new()
        s_con = NM.SettingConnection.new()
        s_con.set_property(NM.SETTING_CONNECTION_ID, ssid)
        s_con.set_property(NM.SETTING_CONNECTION_TYPE, NM.SETTING_WIRELESS_SETTING_NAME)
        settings.add_setting(s_con)

        s_wifi = NM.SettingWireless.new()
        s_wifi.set_property(NM.SETTING_WIRELESS_SSID, target_ap.get_ssid())
        s_wifi.set_property(NM.SETTING_WIRELESS_MODE, "infrastructure")
        settings.add_setting(s_wifi)

        flags = target_ap.get_flags()
        NM_80211ApFlags = getattr(NM, "80211ApFlags", None)
        NM_80211ApSecurityFlags = getattr(NM, "80211ApSecurityFlags", None)

        if NM_80211ApFlags is None or NM_80211ApSecurityFlags is None:
            logger.error(
                "Failed to retrieve 80211ApFlags or 80211ApSecurityFlags from NM"
            )
            show_error_dialog(
                parent, "Internal error: Unable to retrieve security flags."
            )
            return False

        if flags & NM_80211ApFlags.PRIVACY:
            logger.debug("Access point requires authentication")
            if not password:
                logger.info("Password not provided, prompting user")
                password = show_password_dialog(parent, ssid)
                if password is None:
                    logger.warning("Password prompt cancelled by user")
                    return False

            if not password:
                logger.error("Password is required for secured network")
                show_error_dialog(parent, "Password is required for secured network.")
                return False

            s_wsec = NM.SettingWirelessSecurity.new()
            s_wsec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, "wpa-psk")
            s_wsec.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, password)
            settings.add_setting(s_wsec)

        logger.info("Adding and activating the connection")
        client.add_and_activate_connection(settings, wifi_device, target_ap)
        logger.info(f"Successfully connected to {ssid}")
        return True
    except Exception as e:
        logger.exception(f"Error connecting to network {ssid}: {e}")
        show_error_dialog(parent, f"Error connecting to network {ssid}: {e}")
        return False
    finally:
        logger.debug("Exiting connect_to_network()")


def disconnect_from_network(ssid: str) -> bool:
    """Disconnect from network"""
    logger.debug(f"Entered disconnect_from_network() with SSID: {ssid}")
    try:
        logger.info(f"Attempting to disconnect from network: {ssid}")
        active_connections = client.get_active_connections()
        logger.debug(f"Active connections: {active_connections}")
        for active_conn in active_connections:
            if active_conn.get_connection_type() == NM.SETTING_WIRELESS_SETTING_NAME:
                devices = active_conn.get_devices()
                logger.debug(f"Devices in active connection: {devices}")
                for dev in devices:
                    if isinstance(dev, NM.DeviceWifi):
                        ap = dev.get_active_access_point()
                        if ap:
                            ssid_gbytes = ap.get_ssid()
                            if ssid_gbytes is not None:
                                try:
                                    ap_ssid = ssid_gbytes.get_data().decode("utf-8")
                                    logger.debug(f"Active connection SSID: {ap_ssid}")
                                except UnicodeDecodeError as ude:
                                    logger.warning(
                                        f"Failed to decode SSID for active connection: {ude}"
                                    )
                                    continue
                                if ap_ssid == ssid:
                                    client.deactivate_connection(active_conn)
                                    logger.info(
                                        f"Successfully disconnected from {ssid}"
                                    )
                                    return True
                            else:
                                logger.warning("Active access point with no SSID")
        logger.error(f"Network {ssid} is not connected")
        return False
    except Exception as e:
        logger.exception(f"Error disconnecting from network {ssid}: {e}")
        return False
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
