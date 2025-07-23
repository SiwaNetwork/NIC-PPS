#!/usr/bin/env python3
"""
TimeNIC Core Module
Provides core functionality for TimeNIC management
"""

import subprocess
import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PinFunction(Enum):
    """SDP Pin Functions"""
    NONE = 0
    EXTTS = 1  # External timestamp (input)
    PERIODIC = 2  # Periodic output


class PTMStatus(Enum):
    """PTM Status"""
    NOT_SUPPORTED = 0
    DISABLED = 1
    ENABLED = 2


@dataclass
class PTPDevice:
    """PTP Device Information"""
    device: str
    interface: str
    clock_index: int
    capabilities: List[str]


@dataclass
class PPSStatus:
    """PPS Status Information"""
    enabled: bool
    frequency: int
    pin_index: int
    direction: str  # "input" or "output"


@dataclass
class SyncStatus:
    """Synchronization Status"""
    is_synced: bool
    offset_ns: float
    frequency_ppb: float
    rms_ns: float
    last_update: float


class TimeNICManager:
    """Main class for managing TimeNIC operations"""
    
    def __init__(self, interface: str = "enp3s0", ptp_device: str = "/dev/ptp0"):
        self.interface = interface
        self.ptp_device = ptp_device
        self.testptp_path = "/usr/bin/testptp"
        self.ts2phc_path = "/usr/sbin/ts2phc"
        self.phc_ctl_path = "/usr/sbin/phc_ctl"
        
    def _run_command(self, cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return -1, "", str(e)
    
    def check_device(self) -> Optional[PTPDevice]:
        """Check if PTP device is available"""
        cmd = ["ethtool", "-T", self.interface]
        code, stdout, stderr = self._run_command(cmd)
        
        if code != 0:
            logger.error(f"Failed to check device: {stderr}")
            return None
            
        # Parse PTP Hardware Clock index
        match = re.search(r"PTP Hardware Clock:\s*(\d+)", stdout)
        if match:
            clock_index = int(match.group(1))
            
            # Parse capabilities
            capabilities = []
            if "Hardware Transmit Timestamp Modes" in stdout:
                capabilities.append("hardware_transmit")
            if "Hardware Receive Filter Modes" in stdout:
                capabilities.append("hardware_receive")
            if "Software Transmit Timestamp Modes" in stdout:
                capabilities.append("software_transmit")
                
            return PTPDevice(
                device=self.ptp_device,
                interface=self.interface,
                clock_index=clock_index,
                capabilities=capabilities
            )
        return None
    
    def install_driver(self) -> bool:
        """Install patched igc driver"""
        logger.info("Installing patched igc driver...")
        
        # Check if running as root
        if os.geteuid() != 0:
            logger.error("Driver installation requires root privileges")
            return False
            
        # Download and extract driver
        commands = [
            ["wget", "-q", "https://github.com/Time-Appliances-Project/Products/raw/main/TimeNIC/intel-igc-ppsfix_ubuntu.zip", "-O", "/tmp/intel-igc-ppsfix_ubuntu.zip"],
            ["unzip", "-q", "-o", "/tmp/intel-igc-ppsfix_ubuntu.zip", "-d", "/tmp/"],
        ]
        
        for cmd in commands:
            code, _, stderr = self._run_command(cmd)
            if code != 0:
                logger.error(f"Failed to download/extract driver: {stderr}")
                return False
                
        # Install with DKMS
        os.chdir("/tmp/intel-igc-ppsfix")
        
        # Remove old driver
        self._run_command(["dkms", "remove", "igc", "-v", "5.4.0-7642.46"], check=False)
        
        # Add and build new driver
        commands = [
            ["dkms", "add", "."],
            ["dkms", "build", "--force", "igc", "-v", "5.4.0-7642.46"],
            ["dkms", "install", "--force", "igc", "-v", "5.4.0-7642.46"]
        ]
        
        for cmd in commands:
            code, _, stderr = self._run_command(cmd)
            if code != 0:
                logger.error(f"DKMS operation failed: {stderr}")
                return False
                
        # Update kernel module
        kernel_version = os.uname().release
        src = f"/lib/modules/{kernel_version}/updates/dkms/igc.ko.zst"
        dst = f"/lib/modules/{kernel_version}/kernel/drivers/net/ethernet/intel/igc/igc.ko.zst"
        
        if os.path.exists(src):
            # Backup original
            if os.path.exists(dst):
                self._run_command(["cp", dst, f"{dst}.bak"])
            # Copy new module
            self._run_command(["cp", src, dst])
            
        # Update module dependencies
        self._run_command(["depmod", "-a"])
        self._run_command(["update-initramfs", "-u"])
        
        logger.info("Driver installation completed. Reboot required.")
        return True
    
    def enable_pps_output(self, frequency: int = 1000000000) -> bool:
        """Enable PPS output on SDP0 (SMA1)"""
        logger.info(f"Enabling PPS output at {frequency/1e9} Hz")
        
        # Set SDP0 as periodic output
        cmd = [self.testptp_path, "-d", self.ptp_device, "-L0,2"]
        code, _, stderr = self._run_command(cmd)
        if code != 0:
            logger.error(f"Failed to set pin function: {stderr}")
            return False
            
        # Set frequency (period in nanoseconds)
        cmd = [self.testptp_path, "-d", self.ptp_device, "-p", str(frequency)]
        code, _, stderr = self._run_command(cmd)
        if code != 0:
            logger.error(f"Failed to set frequency: {stderr}")
            return False
            
        logger.info("PPS output enabled successfully")
        return True
    
    def enable_pps_input(self) -> bool:
        """Enable PPS input on SDP1 (SMA2)"""
        logger.info("Enabling PPS input")
        
        # Set SDP1 as external timestamp input
        cmd = [self.testptp_path, "-d", self.ptp_device, "-L1,1"]
        code, _, stderr = self._run_command(cmd)
        if code != 0:
            logger.error(f"Failed to set pin function: {stderr}")
            return False
            
        logger.info("PPS input enabled successfully")
        return True
    
    def read_pps_events(self, count: int = 5) -> List[float]:
        """Read PPS input events"""
        logger.info(f"Reading {count} PPS events...")
        
        cmd = [self.testptp_path, "-d", self.ptp_device, "-e", str(count)]
        code, stdout, stderr = self._run_command(cmd)
        
        if code != 0:
            logger.error(f"Failed to read events: {stderr}")
            return []
            
        # Parse timestamps from output
        timestamps = []
        for line in stdout.split('\n'):
            match = re.search(r"event index \d+ at (\d+)\.(\d+)", line)
            if match:
                sec = int(match.group(1))
                nsec = int(match.group(2))
                timestamps.append(sec + nsec / 1e9)
                
        return timestamps
    
    def sync_to_external_pps(self, pin_index: int = 1) -> subprocess.Popen:
        """Start synchronization to external PPS signal"""
        logger.info(f"Starting synchronization to external PPS on pin {pin_index}")
        
        # First, set system time to PHC
        cmd = [self.phc_ctl_path, self.interface, "set;", "adj", "37"]
        self._run_command(cmd)
        
        # Start ts2phc in background
        cmd = [
            self.ts2phc_path,
            "-c", self.ptp_device,
            "-s", "generic",
            f"--ts2phc.pin_index", str(pin_index),
            "-m",
            "-l", "7"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info("ts2phc started successfully")
        return process
    
    def get_sync_status(self, ts2phc_output: str) -> Optional[SyncStatus]:
        """Parse ts2phc output to get sync status"""
        # Look for the latest status line
        lines = ts2phc_output.strip().split('\n')
        for line in reversed(lines):
            # Parse ts2phc output format
            match = re.search(r"offset\s+([-\d]+)\s+s(\d+)\s+freq\s+([-+\d]+)", line)
            if match:
                offset = float(match.group(1))
                freq = float(match.group(3))
                
                # Look for rms value
                rms_match = re.search(r"rms\s+([\d.]+)", line)
                rms = float(rms_match.group(1)) if rms_match else 0.0
                
                return SyncStatus(
                    is_synced=abs(offset) < 1000,  # Consider synced if offset < 1us
                    offset_ns=offset,
                    frequency_ppb=freq,
                    rms_ns=rms,
                    last_update=time.time()
                )
        return None
    
    def check_ptm_support(self) -> PTMStatus:
        """Check PTM support status"""
        cmd = ["lspci", "-vvv"]
        code, stdout, _ = self._run_command(cmd)
        
        if code != 0:
            return PTMStatus.NOT_SUPPORTED
            
        if "Precision Time Measurement" in stdout:
            # Check if enabled
            # Look for PTM capability in sysfs
            pci_devices = os.listdir("/sys/bus/pci/devices/")
            for device in pci_devices:
                ptm_file = f"/sys/bus/pci/devices/{device}/enable_ptm"
                if os.path.exists(ptm_file):
                    try:
                        with open(ptm_file, 'r') as f:
                            if f.read().strip() == "1":
                                return PTMStatus.ENABLED
                    except:
                        pass
            return PTMStatus.DISABLED
        
        return PTMStatus.NOT_SUPPORTED
    
    def enable_ptm(self, pci_address: str) -> bool:
        """Enable PTM for a specific PCI device"""
        ptm_file = f"/sys/bus/pci/devices/{pci_address}/enable_ptm"
        
        if not os.path.exists(ptm_file):
            logger.error(f"PTM not available for device {pci_address}")
            return False
            
        try:
            with open(ptm_file, 'w') as f:
                f.write("1")
            logger.info(f"PTM enabled for {pci_address}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable PTM: {e}")
            return False
    
    def get_phc_time(self) -> Optional[float]:
        """Get current PHC time"""
        cmd = [self.phc_ctl_path, self.ptp_device, "get"]
        code, stdout, _ = self._run_command(cmd)
        
        if code != 0:
            return None
            
        # Parse PHC time
        match = re.search(r"clock time is (\d+)\.(\d+)", stdout)
        if match:
            sec = int(match.group(1))
            nsec = int(match.group(2))
            return sec + nsec / 1e9
            
        return None
    
    def get_status(self) -> Dict:
        """Get comprehensive status of TimeNIC"""
        status = {
            "device": None,
            "pps_output": {"enabled": False},
            "pps_input": {"enabled": False},
            "sync_status": None,
            "ptm_status": self.check_ptm_support().name,
            "phc_time": self.get_phc_time()
        }
        
        # Check device
        device = self.check_device()
        if device:
            status["device"] = {
                "interface": device.interface,
                "ptp_device": device.device,
                "clock_index": device.clock_index,
                "capabilities": device.capabilities
            }
            
        return status