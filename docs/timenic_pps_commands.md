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

### 5. PHC Synchronization
```bash
# Start PHC2SYS synchronization between clocks
python run.py --cli timenic start-phc-sync /dev/ptp0 /dev/ptp1

# Stop PHC2SYS synchronization
python run.py --cli timenic stop-phc-sync

# Start TS2PHC synchronization (external PPS correction)
python run.py --cli timenic start-ts2phc-sync enp3s0 /dev/ptp0

# Stop TS2PHC synchronization
python run.py --cli timenic stop-ts2phc-sync

# Check synchronization status
python run.py --cli timenic sync-status
```

## Command Syntax

```bash
# PPS Configuration
python run.py --cli timenic set-pps <interface> --mode <mode>

# PHC Synchronization
python run.py --cli timenic start-phc-sync <source_ptp> <target_ptp>
python run.py --cli timenic stop-phc-sync
python run.py --cli timenic start-ts2phc-sync <interface> <ptp_device>
python run.py --cli timenic stop-ts2phc-sync
python run.py --cli timenic sync-status
```

**Parameters:**
- `<interface>`: Network interface name (e.g., enp3s0, enp4s0)
- `<mode>`: PPS mode - one of: `disabled`, `input`, `output`, `both`
- `<source_ptp>`: Source PTP device (e.g., /dev/ptp0)
- `<target_ptp>`: Target PTP device (e.g., /dev/ptp1)
- `<ptp_device>`: PTP device for TS2PHC (e.g., /dev/ptp0)

## Requirements

1. **Root privileges**: Most PPS operations require sudo
2. **TimeNIC card**: Intel I226 NIC with igc driver
3. **PTP device**: The card must have an associated PTP device (e.g., /dev/ptp0)
4. **Dependencies**: Install with `pip install -r requirements.txt`
5. **Sudo configuration**: Configure sudo rights for PPS commands:
   ```bash
   echo 'shiwa-time ALL=(ALL) NOPASSWD: /usr/bin/testptp, /usr/bin/phc_ctl, /usr/bin/ts2phc, /usr/bin/phc2sys' | sudo tee /etc/sudoers.d/nic-pps
   ```

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

### Example 3: PHC Synchronization Setup
```bash
# 1. Start mutual synchronization between PHC clocks
sudo python run.py --cli timenic start-phc-sync /dev/ptp0 /dev/ptp1

# 2. Check synchronization status
python run.py --cli timenic sync-status

# 3. Start external PPS correction
sudo python run.py --cli timenic start-ts2phc-sync enp3s0 /dev/ptp0

# 4. Stop synchronization when done
sudo python run.py --cli timenic stop-phc-sync
sudo python run.py --cli timenic stop-ts2phc-sync
```

### Example 4: Full TimeNIC Setup
```bash
# 1. List available TimeNIC cards
python run.py --cli timenic list-timenics

# 2. Get detailed info about a card
python run.py --cli timenic info enp3s0

# 3. Enable both PPS input and output
sudo python run.py --cli timenic set-pps enp3s0 --mode both

# 4. Start PHC synchronization
sudo python run.py --cli timenic start-phc-sync /dev/ptp0 /dev/ptp1

# 5. Monitor the card
python run.py --cli timenic monitor enp3s0 --interval 1
```

## Troubleshooting

### PTP Device Not Found
If you get "PTP device not found" error:
1. Check if igc driver is loaded: `lsmod | grep igc`
2. Verify PTP support: `ethtool -T enp3s0`
3. List PTP devices: `ls /dev/ptp*`

### Permission Denied
1. Run commands with sudo: `sudo python run.py --cli timenic set-pps enp3s0 --mode input`
2. Check sudo configuration: `sudo -n testptp -d /dev/ptp0 -l`
3. Configure sudo rights if needed (see Requirements section)

### PPS Not Working
1. Check current PPS state: `sudo testptp -d /dev/ptp0 -l`
2. Verify PTP device mapping: `ethtool -T enp3s0`
3. Check for PPS sysfs files: `ls /sys/class/net/enp3s0/pps*`

### PHC Synchronization Issues
1. Check if processes are running: `ps aux | grep -E "(phc2sys|ts2phc)"`
2. Verify PTP devices exist: `ls /dev/ptp*`
3. Check system time: `date`
4. Monitor synchronization: `python run.py --cli timenic sync-status`

### TimeNIC Card Not Found
1. List all network interfaces: `ip link show`
2. Check if card uses igc driver: `ethtool -i enp3s0`
3. Verify card is Intel I226: `lspci | grep I226`

## Technical Details

The PPS commands use the `testptp` utility internally:
- **Output mode**: Uses `testptp -L0,2` (periodic output on SDP0) followed by `testptp -p 1000000000` (1Hz period)
- **Input mode**: Uses `testptp -L1,1` (external timestamp on SDP1)
- **Disable mode**: Uses `testptp -p 0` (disable periodic output), `testptp -L0,0` (reset SDP0), `testptp -L1,0` (reset SDP1), `testptp -e 0` (disable external timestamps)

The PHC synchronization commands use:
- **PHC2SYS**: `phc2sys -s <source> -c <target> -O 0 -R 16 -m` (mutual synchronization)
- **TS2PHC**: `phc_ctl -d <ptp_device> -s` (set system time to PHC) and `ts2phc -s <ptp_device> -c CLOCK_REALTIME -d 1` (correct PHC by external PPS)

The default output frequency is 1Hz (1,000,000,000 nanoseconds period).