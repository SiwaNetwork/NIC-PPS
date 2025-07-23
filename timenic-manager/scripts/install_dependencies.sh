#!/bin/bash
#
# Install system dependencies for TimeNIC Manager
#

set -e

echo "Installing TimeNIC Manager dependencies..."

# Update package list
sudo apt update

# Install system packages
sudo apt install -y \
    openssh-server \
    net-tools \
    gcc \
    vim \
    dkms \
    linuxptp \
    linux-headers-$(uname -r) \
    libgpiod-dev \
    pkg-config \
    build-essential \
    git \
    python3-pip \
    python3-venv \
    python3-dev \
    pps-tools \
    ethtool \
    wget \
    unzip

# Install Node.js for React frontend
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

echo "System dependencies installed successfully!"

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment and install Python packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Python dependencies installed successfully!"

# Install React dependencies
echo "Installing React dependencies..."
cd web/frontend
npm install
cd ../..

echo "All dependencies installed successfully!"
echo ""
echo "To activate the Python virtual environment, run:"
echo "  source venv/bin/activate"