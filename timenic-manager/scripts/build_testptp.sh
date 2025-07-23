#!/bin/bash
#
# Build and install testptp utility
#

set -e

echo "Building testptp utility..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Download source files
echo "Downloading source files..."
wget -q https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/tools/testing/selftests/ptp/testptp.c
wget -q https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/include/uapi/linux/ptp_clock.h

# Copy header to system include directory
echo "Installing PTP header..."
sudo cp ptp_clock.h /usr/include/linux/

# Compile testptp
echo "Compiling testptp..."
gcc -Wall -lrt testptp.c -o testptp

# Install testptp
echo "Installing testptp..."
sudo cp testptp /usr/bin/
sudo chmod +x /usr/bin/testptp

# Cleanup
cd /
rm -rf $TEMP_DIR

echo "testptp installed successfully!"
echo ""
echo "You can now use testptp with commands like:"
echo "  sudo testptp -d /dev/ptp0 -L0,2"
echo "  sudo testptp -d /dev/ptp0 -p 1000000000"