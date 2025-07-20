# Ubuntu 24.04 Setup and Usage Guide

This document provides comprehensive setup and usage instructions for Intel NIC PPS configuration on Ubuntu 24.04 fresh install.

## Pre-setup Steps

### A. Install linuxptp and utilities

```bash
sudo apt install linuxptp
sudo apt install gcc
```

### B. Download testptp

```bash
cd ~
mkdir testptp
cd testptp

wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/tools/testing/selftests/ptp/testptp.c
wget https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/include/uapi/linux/ptp_clock.h

sudo cp ptp_clock.h /usr/include/linux/ptp_clock.h
```

### C. Compile testptp

```bash
gcc -Wall -lrt testptp.c -o testptp
```

### D. Install testptp

```bash
sudo cp testptp /usr/bin/
```

### E. Figure out which ptp interface maps to the NIC

Use `ethtool -T` to determine which PTP Hardware Clock corresponds to your NIC:

```bash
ethtool -T enp1s0
```

**Example output:**
```
Time stamping parameters for enp1s0:
Capabilities:
    hardware-transmit
    software-transmit
    hardware-receive
    software-receive
    software-system-clock
    hardware-raw-clock
PTP Hardware Clock: 0
Hardware Transmit Timestamp Modes:
    off
    on
Hardware Receive Filter Modes:
    none
    all
```

On this system, the NIC is `enp1s0`, and the PTP Hardware Clock is number 0, which corresponds to `/dev/ptp0`.

### F. Verify testptp works

```bash
sudo testptp -d /dev/ptp0 -l
```

**Expected output:**
```
name SDP0 index 0 func 0 chan 0
name SDP1 index 1 func 0 chan 0
name SDP2 index 2 func 0 chan 0
name SDP3 index 3 func 0 chan 0
```

## PPS Configuration

### Configure 1PPS Output

Setup SDP0 (SMA1, furthest from PCIe fingers, above RJ45) as periodic output:

```bash
sudo testptp -d /dev/ptp0 -L0,2
sudo testptp -d /dev/ptp0 -p 1000000000
```

### Read 1PPS SMA Input

#### A. Setup SDP1 (SMA2, furthest from HAT header, below RJ45) as timestamp input

```bash
sudo testptp -d /dev/ptp0 -L1,1
```

#### B. Read timestamps

Use `-1` to read forever and `Ctrl+C` to stop, or use a number like `5` for demo:

```bash
sudo testptp -d /dev/ptp0 -e 5
```

**Note:** I226 driver passes both edges to Linux, so both rising and falling edges will be listed. A fix for this is listed below, requires patching and building kernel.

### Discipline to 1PPS SMA Input

#### A. Verify PPS input on SMA2 using the testptp steps above

#### B. Set NIC PHC based on system time to get Time-Of-Day

```bash
sudo phc_ctl enp1s0 "set;" adj 37
```

#### C. Use ts2phc to discipline NIC from 1PPS

```bash
sudo ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7
```

## Advanced Configuration

### Fix 1PPS input to only use rising edge (Advanced)

**Work in Progress instructions Method 0**

This requires kernel patching and rebuilding to filter out falling edges from the I226 driver.

## Integration with Intel NIC PPS Tool

### Automatic Detection

The Intel NIC PPS Configuration and Monitoring Tool can automatically detect PTP interfaces and integrate with the linuxptp setup:

```bash
# Check if PTP interfaces are detected
python run.py --cli list-ptp

# Configure PPS through the tool
python run.py --cli set-pps enp1s0 --mode input --ptp-device /dev/ptp0

# Monitor PTP synchronization
python run.py --cli monitor-ptp enp1s0 --interval 1
```

### Web Interface Integration

The web interface can display PTP synchronization status and allow configuration through the browser:

```bash
python run.py --web
```

Navigate to the PTP Configuration section in the web interface.

### GUI Integration

The GUI interface provides visual configuration of PTP settings:

```bash
python run.py --gui
```

## Troubleshooting

### Common Issues

#### 1. testptp not found
```bash
# Check if testptp is installed
which testptp

# If not found, reinstall
cd ~/testptp
sudo cp testptp /usr/bin/
```

#### 2. Permission denied on /dev/ptp0
```bash
# Check permissions
ls -la /dev/ptp0

# Fix permissions
sudo chmod 666 /dev/ptp0
```

#### 3. PTP Hardware Clock not detected
```bash
# Check available PTP devices
ls -la /dev/ptp*

# Check ethtool output
ethtool -T enp1s0
```

#### 4. ts2phc not found
```bash
# Install ts2phc
sudo apt install linuxptp

# Verify installation
which ts2phc
```

### Debugging Commands

```bash
# Check PTP clock status
sudo testptp -d /dev/ptp0 -i

# Check PTP clock capabilities
sudo testptp -d /dev/ptp0 -c

# Monitor PTP clock
sudo testptp -d /dev/ptp0 -m
```

## Performance Monitoring

### PTP Synchronization Quality

Monitor the quality of PTP synchronization:

```bash
# Check offset and delay
sudo phc2sys -s /dev/ptp0 -c CLOCK_REALTIME -O 0 -m

# Monitor with ts2phc
sudo ts2phc -c /dev/ptp0 -s generic --ts2phc.pin_index 1 -m -l 7
```

### Integration with Monitoring Tools

The Intel NIC PPS Tool can integrate with these PTP monitoring capabilities:

```bash
# Start comprehensive monitoring
python run.py --cli monitor-all --ptp --pps --temperature --interval 1
```

## Security Considerations

### Running with Elevated Privileges

Many PTP operations require root privileges. Consider using sudo with specific commands:

```bash
# Create a specific sudo rule for PTP operations
sudo visudo

# Add line for specific user
username ALL=(ALL) NOPASSWD: /usr/bin/testptp, /usr/bin/phc_ctl, /usr/bin/ts2phc
```

### Network Security

When using PTP over network:

```bash
# Configure firewall for PTP traffic
sudo ufw allow 319/udp  # PTP event messages
sudo ufw allow 320/udp  # PTP general messages
```

## References

- [Linux PTP Documentation](https://linuxptp.sourceforge.net/)
- [Intel I226 Datasheet](https://www.intel.com/content/www/us/en/products/docs/ethernet/i226/i226-datasheet.html)
- [PTP IEEE 1588 Standard](https://standards.ieee.org/standard/1588-2019.html)

## Version History

- **v1.0**: Initial Ubuntu 24.04 setup guide
- **v1.1**: Added integration with Intel NIC PPS Tool
- **v1.2**: Added troubleshooting and security sections