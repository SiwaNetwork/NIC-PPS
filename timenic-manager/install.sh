#!/bin/bash
#
# Main installation script for TimeNIC Manager
#

set -e

echo "======================================"
echo "TimeNIC Manager Installation"
echo "======================================"
echo ""

# Check Ubuntu version
if ! grep -q "Ubuntu 24.04" /etc/os-release; then
    echo "Warning: This script is designed for Ubuntu 24.04"
    echo "Your system: $(lsb_release -d | cut -f2)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Make scripts executable
chmod +x scripts/*.sh

# Step 1: Install dependencies
echo ""
echo "Step 1: Installing dependencies..."
./scripts/install_dependencies.sh

# Step 2: Build testptp
echo ""
echo "Step 2: Building testptp..."
./scripts/build_testptp.sh

# Step 3: Install Python package
echo ""
echo "Step 3: Installing TimeNIC Manager Python package..."
source venv/bin/activate
pip install -e .

# Step 4: Create systemd service
echo ""
echo "Step 4: Creating systemd service..."
sudo tee /etc/systemd/system/timenic-web.service > /dev/null <<EOF
[Unit]
Description=TimeNIC Web Interface
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$(pwd)/venv/bin/python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# Step 5: Create desktop shortcut for GUI
echo ""
echo "Step 5: Creating desktop shortcut..."
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/timenic-manager.desktop <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=TimeNIC Manager
Comment=Manage TimeNIC PCIe card
Exec=$(pwd)/venv/bin/python $(pwd)/gui/timenic_gui.py
Icon=network-wired
Terminal=false
Categories=System;Network;
EOF

# Step 6: Driver installation prompt
echo ""
echo "Step 6: Driver Installation"
echo "The patched igc driver is required for PPS functionality."
read -p "Install patched driver now? (requires root and reboot) (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo ./scripts/install_driver.sh
fi

# Step 7: Create command shortcuts
echo ""
echo "Step 7: Creating command shortcuts..."
sudo tee /usr/local/bin/timenic-cli > /dev/null <<EOF
#!/bin/bash
source $(pwd)/venv/bin/activate
python $(pwd)/cli/timenic_cli.py "\$@"
EOF
sudo chmod +x /usr/local/bin/timenic-cli

sudo tee /usr/local/bin/timenic-gui > /dev/null <<EOF
#!/bin/bash
source $(pwd)/venv/bin/activate
python $(pwd)/gui/timenic_gui.py "\$@"
EOF
sudo chmod +x /usr/local/bin/timenic-gui

sudo tee /usr/local/bin/timenic-web > /dev/null <<EOF
#!/bin/bash
case "\$1" in
    start)
        sudo systemctl start timenic-web
        echo "TimeNIC Web interface started"
        echo "Access it at: http://localhost:8000"
        ;;
    stop)
        sudo systemctl stop timenic-web
        echo "TimeNIC Web interface stopped"
        ;;
    status)
        sudo systemctl status timenic-web
        ;;
    enable)
        sudo systemctl enable timenic-web
        echo "TimeNIC Web interface enabled at boot"
        ;;
    disable)
        sudo systemctl disable timenic-web
        echo "TimeNIC Web interface disabled at boot"
        ;;
    *)
        echo "Usage: timenic-web {start|stop|status|enable|disable}"
        exit 1
        ;;
esac
EOF
sudo chmod +x /usr/local/bin/timenic-web

echo ""
echo "======================================"
echo "Installation completed successfully!"
echo "======================================"
echo ""
echo "Available commands:"
echo "  timenic-cli       - Command line interface"
echo "  timenic-gui       - Graphical user interface"
echo "  timenic-web start - Start web interface"
echo ""
echo "Quick start:"
echo "  1. Run 'timenic-cli status' to check device"
echo "  2. Run 'timenic-cli quick-setup' for basic configuration"
echo "  3. Access web interface at http://localhost:8000"
echo ""
if [ -f /tmp/driver_installed ]; then
    echo "IMPORTANT: Reboot required for driver changes!"
fi