# TimeNIC PPS Commands Documentation

## Overview

The TimeNIC PPS (Pulse Per Second) commands allow you to configure the PPS functionality on Intel I226 TimeNIC cards. These cards have two SMA connectors:
- **SMA1 (SDP0)**: PPS output
- **SMA2 (SDP1)**: PPS input

## Available Commands

### 1. Enable Input PPS (SMA2)
```bash
python run.py --cli timenic set-pps enp3s0 --mode input
```
This command configures SMA2 to receive external PPS signals. Use this when you want to synchronize the TimeNIC card with an external time source.

### 2. Enable Output PPS (SMA1)
```bash
python run.py --cli timenic set-pps enp3s0 --mode output
```
This command configures SMA1 to generate PPS signals at 1Hz. The card will output a pulse every second.

### 3. Enable Both Input and Output
```bash
python run.py --cli timenic set-pps enp3s0 --mode both
```
This enables both PPS input on SMA2 and PPS output on SMA1 simultaneously.

### 4. Disable PPS
```bash
python run.py --cli timenic set-pps enp3s0 --mode disabled
```
This disables all PPS functionality on both SMA connectors.

## Command Syntax

```bash
python run.py --cli timenic set-pps <interface> --mode <mode>
```

**Parameters:**
- `<interface>`: Network interface name (e.g., enp3s0, enp4s0)
- `<mode>`: PPS mode - one of: `disabled`, `input`, `output`, `both`

## Requirements

1. **Root privileges**: Most PPS operations require sudo
2. **TimeNIC card**: Intel I226 NIC with igc driver
3. **PTP device**: The card must have an associated PTP device (e.g., /dev/ptp0)
4. **Dependencies**: Install with `pip install -r requirements.txt`

## Examples

### Example 1: Configure PPS Input for External Time Source
```bash
# Enable PPS input on SMA2
sudo python run.py --cli timenic set-pps enp3s0 --mode input

# Read PPS events from external source
sudo python run.py --cli timenic read-pps /dev/ptp0 --count 5
```

### Example 2: Configure PPS Output for Time Distribution
```bash
# Enable PPS output on SMA1 (1Hz)
sudo python run.py --cli timenic set-pps enp3s0 --mode output

# Change PPS frequency (e.g., 10Hz)
sudo python run.py --cli timenic set-period /dev/ptp0 --period 100000000
```

### Example 3: Full TimeNIC Setup
```bash
# 1. List available TimeNIC cards
python run.py --cli timenic list-timenics

# 2. Get detailed info about a card
python run.py --cli timenic info enp3s0

# 3. Enable both PPS input and output
sudo python run.py --cli timenic set-pps enp3s0 --mode both

# 4. Monitor the card
python run.py --cli timenic monitor enp3s0 --interval 1
```

## Troubleshooting

### PTP Device Not Found
If you get "PTP device not found" error:
1. Check if igc driver is loaded: `lsmod | grep igc`
2. Verify PTP support: `ethtool -T enp3s0`
3. List PTP devices: `ls /dev/ptp*`

### Permission Denied
Run commands with sudo: `sudo python run.py --cli timenic set-pps enp3s0 --mode input`

### TimeNIC Card Not Found
1. List all network interfaces: `ip link show`
2. Check if card uses igc driver: `ethtool -i enp3s0`
3. Verify card is Intel I226: `lspci | grep I226`

## Technical Details

The PPS commands use the `testptp` utility internally:
- **Output mode**: Uses `testptp -L0,2` (periodic output on SDP0)
- **Input mode**: Uses `testptp -L1,1` (external timestamp on SDP1)
- **Period setting**: Uses `testptp -p <nanoseconds>`

The default output frequency is 1Hz (1,000,000,000 nanoseconds period).