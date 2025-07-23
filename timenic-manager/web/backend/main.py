#!/usr/bin/env python3
"""
TimeNIC Web API - FastAPI backend for TimeNIC management
"""

import sys
import os
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import json

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from common.timenic_core import TimeNICManager, PTMStatus


# Pydantic models
class DeviceConfig(BaseModel):
    interface: str = "enp3s0"
    ptp_device: str = "/dev/ptp0"


class PPSConfig(BaseModel):
    frequency: int = 1  # Hz


class PTMConfig(BaseModel):
    pci_address: str


class SyncConfig(BaseModel):
    pin_index: int = 1


class StatusResponse(BaseModel):
    device: Optional[Dict]
    pps_output: Dict
    pps_input: Dict
    sync_status: Optional[Dict]
    ptm_status: str
    phc_time: Optional[float]


class OperationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


# Create FastAPI app
app = FastAPI(
    title="TimeNIC API",
    description="Web API for TimeNIC PCIe card management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global manager instance
manager = TimeNICManager()

# WebSocket connections for real-time updates
websocket_connections: List[WebSocket] = []

# Background tasks
sync_process = None
sync_task = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "TimeNIC Web API", "version": "1.0.0"}


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current TimeNIC status"""
    try:
        status = manager.get_status()
        return StatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/device/configure", response_model=OperationResponse)
async def configure_device(config: DeviceConfig):
    """Configure device interface and PTP device"""
    global manager
    try:
        manager = TimeNICManager(config.interface, config.ptp_device)
        device = manager.check_device()
        
        if device:
            return OperationResponse(
                success=True,
                message=f"Device configured: {config.interface} → {config.ptp_device}",
                data={
                    "interface": device.interface,
                    "ptp_device": device.device,
                    "clock_index": device.clock_index
                }
            )
        else:
            return OperationResponse(
                success=False,
                message="Device not found or not accessible"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pps/output/enable", response_model=OperationResponse)
async def enable_pps_output(config: PPSConfig):
    """Enable PPS output on SMA1"""
    try:
        period_ns = int(1e9 / config.frequency)
        success = manager.enable_pps_output(period_ns)
        
        if success:
            await broadcast_status_update()
            return OperationResponse(
                success=True,
                message=f"PPS output enabled at {config.frequency} Hz"
            )
        else:
            return OperationResponse(
                success=False,
                message="Failed to enable PPS output"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pps/input/enable", response_model=OperationResponse)
async def enable_pps_input():
    """Enable PPS input on SMA2"""
    try:
        success = manager.enable_pps_input()
        
        if success:
            await broadcast_status_update()
            return OperationResponse(
                success=True,
                message="PPS input enabled on SMA2"
            )
        else:
            return OperationResponse(
                success=False,
                message="Failed to enable PPS input"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pps/events")
async def read_pps_events(count: int = 5):
    """Read PPS input events"""
    try:
        timestamps = manager.read_pps_events(count)
        
        events = []
        for i, ts in enumerate(timestamps):
            events.append({
                "index": i + 1,
                "timestamp": ts,
                "time": datetime.fromtimestamp(ts).isoformat()
            })
            
        return {
            "success": True,
            "count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ptm/enable", response_model=OperationResponse)
async def enable_ptm(config: PTMConfig):
    """Enable PTM for specified PCI device"""
    try:
        # Check current status first
        ptm_status = manager.check_ptm_support()
        
        if ptm_status == PTMStatus.NOT_SUPPORTED:
            return OperationResponse(
                success=False,
                message="PTM is not supported on this system"
            )
        elif ptm_status == PTMStatus.ENABLED:
            return OperationResponse(
                success=True,
                message="PTM is already enabled"
            )
        
        # Try to enable
        success = manager.enable_ptm(config.pci_address)
        
        if success:
            await broadcast_status_update()
            return OperationResponse(
                success=True,
                message=f"PTM enabled for device {config.pci_address}"
            )
        else:
            return OperationResponse(
                success=False,
                message="Failed to enable PTM"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync/start", response_model=OperationResponse)
async def start_sync(config: SyncConfig):
    """Start synchronization to external PPS"""
    global sync_process, sync_task
    
    try:
        # Stop existing sync if running
        if sync_process:
            sync_process.terminate()
            sync_process = None
            
        if sync_task:
            sync_task.cancel()
            
        # Enable PPS input first
        manager.enable_pps_input()
        
        # Start sync process
        sync_process = manager.sync_to_external_pps(config.pin_index)
        
        # Start monitoring task
        sync_task = asyncio.create_task(monitor_sync())
        
        return OperationResponse(
            success=True,
            message=f"Synchronization started on pin {config.pin_index}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync/stop", response_model=OperationResponse)
async def stop_sync():
    """Stop synchronization"""
    global sync_process, sync_task
    
    try:
        if sync_process:
            sync_process.terminate()
            sync_process = None
            
        if sync_task:
            sync_task.cancel()
            sync_task = None
            
        await broadcast_sync_status(None)
        
        return OperationResponse(
            success=True,
            message="Synchronization stopped"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/status")
async def get_sync_status():
    """Get current synchronization status"""
    global sync_process
    
    if not sync_process or sync_process.poll() is not None:
        return {
            "running": False,
            "status": None
        }
    
    return {
        "running": True,
        "status": "Check WebSocket for real-time updates"
    }


@app.post("/api/driver/install", response_model=OperationResponse)
async def install_driver():
    """Install patched igc driver"""
    try:
        # Check if running as root
        if os.geteuid() != 0:
            return OperationResponse(
                success=False,
                message="Driver installation requires root privileges"
            )
            
        success = manager.install_driver()
        
        if success:
            return OperationResponse(
                success=True,
                message="Driver installed successfully. System reboot required."
            )
        else:
            return OperationResponse(
                success=False,
                message="Driver installation failed"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quick-setup", response_model=OperationResponse)
async def quick_setup():
    """Run quick setup wizard"""
    try:
        results = []
        
        # Check device
        device = manager.check_device()
        if not device:
            return OperationResponse(
                success=False,
                message="PTP device not found"
            )
        results.append("Device found")
        
        # Enable PPS output
        if manager.enable_pps_output():
            results.append("PPS output enabled")
        
        # Enable PPS input
        if manager.enable_pps_input():
            results.append("PPS input enabled")
            
        # Check PTM
        ptm_status = manager.check_ptm_support()
        results.append(f"PTM status: {ptm_status.name}")
        
        await broadcast_status_update()
        
        return OperationResponse(
            success=True,
            message="Quick setup completed",
            data={"steps": results}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export-config")
async def export_config():
    """Export current configuration"""
    try:
        config = {
            "interface": manager.interface,
            "ptp_device": manager.ptp_device,
            "status": manager.get_status(),
            "timestamp": datetime.now().isoformat()
        }
        
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import-config")
async def import_config(config: Dict):
    """Import configuration"""
    global manager
    
    try:
        interface = config.get("interface", "enp3s0")
        ptp_device = config.get("ptp_device", "/dev/ptp0")
        
        manager = TimeNICManager(interface, ptp_device)
        
        return OperationResponse(
            success=True,
            message="Configuration imported successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial status
        status = manager.get_status()
        await websocket.send_json({
            "type": "status",
            "data": status
        })
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)


async def broadcast_status_update():
    """Broadcast status update to all WebSocket connections"""
    if not websocket_connections:
        return
        
    status = manager.get_status()
    message = {
        "type": "status",
        "data": status
    }
    
    # Send to all connections
    disconnected = []
    for ws in websocket_connections:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)
            
    # Remove disconnected
    for ws in disconnected:
        websocket_connections.remove(ws)


async def broadcast_sync_status(status: Optional[Dict]):
    """Broadcast sync status to all WebSocket connections"""
    if not websocket_connections:
        return
        
    message = {
        "type": "sync_status",
        "data": status
    }
    
    # Send to all connections
    disconnected = []
    for ws in websocket_connections:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)
            
    # Remove disconnected
    for ws in disconnected:
        websocket_connections.remove(ws)


async def monitor_sync():
    """Monitor synchronization process and broadcast updates"""
    global sync_process
    
    while sync_process and sync_process.poll() is None:
        try:
            # Read output with timeout
            output = await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(sync_process.stdout.readline)
                ),
                timeout=1.0
            )
            
            if output:
                sync_status = manager.get_sync_status(output)
                if sync_status:
                    await broadcast_sync_status({
                        "is_synced": sync_status.is_synced,
                        "offset_ns": sync_status.offset_ns,
                        "frequency_ppb": sync_status.frequency_ppb,
                        "rms_ns": sync_status.rms_ns,
                        "timestamp": sync_status.last_update
                    })
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"Sync monitor error: {e}")
            break
            
    # Process ended
    await broadcast_sync_status(None)


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )