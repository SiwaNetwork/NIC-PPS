# TimeNIC Manager Usage Guide

## Table of Contents
1. [Installation](#installation)
2. [CLI Usage](#cli-usage)
3. [GUI Usage](#gui-usage)
4. [Web Interface](#web-interface)
5. [Common Tasks](#common-tasks)
6. [Troubleshooting](#troubleshooting)

## Installation

### Quick Install
```bash
git clone https://github.com/your-repo/timenic-manager.git
cd timenic-manager
chmod +x install.sh
./install.sh
```

### Manual Installation
1. Install dependencies:
   ```bash
   ./scripts/install_dependencies.sh
   ```

2. Build testptp:
   ```bash
   ./scripts/build_testptp.sh
   ```

3. Install driver (requires root):
   ```bash
   sudo ./scripts/install_driver.sh
   # Reboot after installation
   ```

## CLI Usage

### Basic Commands

#### Check Status
```bash
timenic-cli status
```

#### Quick Setup
```bash
timenic-cli quick-setup
```

#### Enable PPS Output
```bash
# Default 1 Hz
timenic-cli enable-pps-output

# Custom frequency (10 Hz)
timenic-cli enable-pps-output --frequency 10
```

#### Enable PPS Input
```bash
timenic-cli enable-pps-input
```

#### Read PPS Events
```bash
# Read 5 events (default)
timenic-cli read-pps-events

# Read 10 events
timenic-cli read-pps-events --count 10
```

#### Synchronize to External PPS
```bash
# Start synchronization
timenic-cli sync-external-pps

# Start with monitoring
timenic-cli sync-external-pps --monitor

# Use different pin
timenic-cli sync-external-pps --pin-index 2
```

#### Enable PTM
```bash
# Find PCI address
lspci | grep Ethernet

# Enable PTM
timenic-cli enable-ptm --pci-address 0000:03:00.0
```

#### Export/Import Configuration
```bash
# Export
timenic-cli export-config -o config.json

# View current config
timenic-cli export-config
```

### Advanced Options

#### Specify Interface
```bash
timenic-cli --interface enp1s0 status
```

#### Specify PTP Device
```bash
timenic-cli --device /dev/ptp1 status
```

## GUI Usage

### Starting the GUI
```bash
timenic-gui
```

### GUI Features

1. **Status Tab**
   - Real-time device status
   - PHC time display
   - Connection indicators

2. **Control Tab**
   - PPS output control with frequency selection
   - PPS input control and event reading
   - PTM configuration

3. **Synchronization Tab**
   - Start/stop synchronization
   - Real-time sync status
   - Synchronization graphs

4. **Configuration Tab**
   - Device selection
   - Driver management
   - Configuration import/export

5. **Logs Tab**
   - Real-time operation logs
   - Log filtering and export

## Web Interface

### Starting the Web Interface
```bash
# Start
timenic-web start

# Stop
timenic-web stop

# Check status
timenic-web status

# Enable at boot
timenic-web enable
```

### Accessing the Interface
Open your browser and navigate to: `http://localhost:8000`

### Web Features

1. **Dashboard**
   - Overview of all components
   - Quick status indicators
   - PHC time display

2. **Control Panel**
   - PPS output/input control
   - PTM management
   - Quick setup wizard

3. **Synchronization**
   - Real-time sync monitoring
   - Interactive graphs
   - Sync statistics

4. **Configuration**
   - Device settings
   - Driver installation
   - Config management

### API Endpoints

The web interface provides a REST API:

- `GET /api/status` - Get current status
- `POST /api/pps/output/enable` - Enable PPS output
- `POST /api/pps/input/enable` - Enable PPS input
- `GET /api/pps/events` - Read PPS events
- `POST /api/sync/start` - Start synchronization
- `POST /api/sync/stop` - Stop synchronization
- `POST /api/ptm/enable` - Enable PTM
- `POST /api/quick-setup` - Run quick setup

WebSocket endpoint for real-time updates: `ws://localhost:8000/ws`

## Common Tasks

### Initial Setup
1. Check device status:
   ```bash
   timenic-cli status
   ```

2. Run quick setup:
   ```bash
   timenic-cli quick-setup
   ```

3. Verify PPS output:
   - Connect oscilloscope to SMA1
   - Should see 1 Hz square wave

### Synchronizing to GPS
1. Connect GPS PPS to SMA2
2. Enable PPS input:
   ```bash
   timenic-cli enable-pps-input
   ```

3. Start synchronization:
   ```bash
   timenic-cli sync-external-pps --monitor
   ```

### Automatic Startup
1. Install systemd service:
   ```bash
   sudo cp config/ptp-nic-setup.service /etc/systemd/system/
   sudo systemctl enable ptp-nic-setup
   sudo systemctl start ptp-nic-setup
   ```

2. Enable web interface at boot:
   ```bash
   timenic-web enable
   ```

## Troubleshooting

### Device Not Found
- Check interface name: `ip a`
- Verify driver: `ethtool -i <interface>`
- Check PTP support: `ethtool -T <interface>`

### PPS Not Working
- Verify driver installation: `modinfo igc | grep filename`
- Check pin configuration: `sudo testptp -d /dev/ptp0 -L`
- Monitor kernel messages: `dmesg | grep ptp`

### Synchronization Issues
- Check PPS input signal quality
- Verify cable connections
- Monitor sync logs: `journalctl -u ptp4l -f`

### Permission Errors
- Most operations require sudo
- Add user to appropriate groups:
  ```bash
  sudo usermod -a -G dialout $USER
  ```

### Web Interface Issues
- Check if port 8000 is available: `sudo lsof -i :8000`
- Verify service status: `timenic-web status`
- Check logs: `journalctl -u timenic-web -f`

## Support

For additional help:
- Check the logs in the GUI or CLI
- Visit the project repository
- Consult the TimeNIC hardware documentation