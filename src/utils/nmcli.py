import subprocess
from typing import List, Optional
from loguru import logger


def get_network_names() -> List[str]:
    """Get list of available network SSIDs"""
    logger.debug("Fetching available network SSIDs")
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID", "dev", "wifi"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            networks = result.stdout.split("\n")
            logger.debug(f"Found {len(networks)} networks")
            return networks
        else:
            logger.error(f"Failed to get networks: {result.stderr}")
            return []
    except subprocess.SubprocessError as e:
        logger.exception("Error running nmcli command")
        return []


def get_active_network() -> str:
    """Get currently active network SSID"""
    logger.debug("Fetching active network")
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            network = result.stdout.split("\n")[0]
            logger.debug(f"Active network: {network}")
            return network
        else:
            logger.error(f"Failed to get active network: {result.stderr}")
            return ""
    except subprocess.SubprocessError as e:
        logger.exception("Error getting active network")
        return ""


def connect_to_network(ssid: str, password: Optional[str] = None) -> bool:
    """Connect to network with optional password"""
    logger.info(f"Attempting to connect to network: {ssid}")
    try:
        if password:
            logger.debug(f"Connecting to {ssid} with password")
            cmd = ["nmcli", "device", "wifi", "connect", ssid, "password", password]
        else:
            logger.debug(f"Connecting to {ssid} without password")
            cmd = ["nmcli", "connection", "up", ssid]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"Successfully connected to {ssid}")
            return True
        else:
            logger.error(f"Failed to connect to {ssid}: {result.stderr}")
            return False

    except subprocess.SubprocessError as e:
        logger.exception(f"Error connecting to network {ssid}")
        return False


def disconnect_from_network(ssid: str) -> bool:
    """Disconnect from network"""
    logger.info(f"Attempting to disconnect from network: {ssid}")
    try:
        result = subprocess.run(
            ["nmcli", "connection", "down", ssid], capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info(f"Successfully disconnected from {ssid}")
            return True
        else:
            logger.error(f"Failed to disconnect from {ssid}: {result.stderr}")
            return False
    except subprocess.SubprocessError as e:
        logger.exception(f"Error disconnecting from network {ssid}")
        return False
