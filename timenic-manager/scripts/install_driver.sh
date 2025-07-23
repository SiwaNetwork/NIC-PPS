#!/bin/bash
#
# Install patched igc driver for TimeNIC
#

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run as root (use sudo)"
    exit 1
fi

echo "Installing patched igc driver for TimeNIC..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Download driver
echo "Downloading driver..."
wget -q https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip

# Extract driver
echo "Extracting driver..."
unzip -q intel-igc-ppsfix_ubuntu.zip
cd intel-igc-ppsfix

# Remove old driver if exists
echo "Removing old driver..."
dkms remove igc -v 5.4.0-7642.46 2>/dev/null || true

# Add new driver
echo "Adding new driver to DKMS..."
dkms add .

# Build driver
echo "Building driver..."
dkms build --force igc -v 5.4.0-7642.46

# Install driver
echo "Installing driver..."
dkms install --force igc -v 5.4.0-7642.46

# Replace kernel module
echo "Updating kernel module..."
KERNEL_VERSION=$(uname -r)
SRC="/lib/modules/$KERNEL_VERSION/updates/dkms/igc.ko.zst"
DST="/lib/modules/$KERNEL_VERSION/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst"

if [ -f "$SRC" ]; then
    # Backup original
    if [ -f "$DST" ]; then
        cp "$DST" "$DST.bak"
    fi
    
    # Copy new module
    cp "$SRC" "$DST"
fi

# Update module dependencies
echo "Updating module dependencies..."
depmod -a
update-initramfs -u

# Cleanup
cd /
rm -rf $TEMP_DIR

echo ""
echo "Driver installation completed successfully!"
echo "IMPORTANT: You must reboot your system for the changes to take effect."
echo ""
echo "After reboot, verify the driver with:"
echo "  modinfo igc | grep filename"
echo "  ethtool -i <interface_name>"