# Komodo

A (probably not) lightweight and (definitely not) fast network manager for Linux, using GTK4 & Libadwaita.

## Installation

## Features

- Simple GTK4 & Libadwaita interface for managing network connections
- Real-time network scanning and monitoring
- View available WiFi networks with signal strength indicators
- Connect/disconnect from wireless networks
- View detailed network information:
  - SSID (Network name)
  - Signal strength
  - Security type (WPA2, etc.)
  - IPv4 and IPv6 addresses
  - MAC address
- Password management for secured networks
- Auto-refresh of network status every 5 seconds
- Basic and Advanced views (Advanced mode currently directs to terminal usage)

## Building from Source

1. Install dependencies:

```sh
pip install build
```

1. Clone the repository:

```sh
git clone https://github.com/FurthestDrop/komodo.git
cd komodo
```

2. Build the project:

```sh
python -m build
```

3. Install the package:

```sh
# System-wide
sudo pip install .

# User
pip install --user .
```

4. Run the application!
