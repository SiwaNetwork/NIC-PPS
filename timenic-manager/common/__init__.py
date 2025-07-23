"""
TimeNIC Common Module
Shared functionality for all interfaces
"""

from .timenic_core import (
    TimeNICManager,
    PinFunction,
    PTMStatus,
    PTPDevice,
    PPSStatus,
    SyncStatus
)

__all__ = [
    'TimeNICManager',
    'PinFunction',
    'PTMStatus',
    'PTPDevice',
    'PPSStatus',
    'SyncStatus'
]

__version__ = '1.0.0'