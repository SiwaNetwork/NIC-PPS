"""
Core модуль для Intel NIC PPS Configuration and Monitoring Tool
Поддержка TimeNIC карт с PTP, PPS, SMA и TCXO
"""

from .nic_manager import IntelNICManager, NICInfo, PPSMode
from .timenic_manager import TimeNICManager, TimeNICInfo, PTPInfo, PTMStatus

__all__ = [
    'IntelNICManager',
    'NICInfo', 
    'PPSMode',
    'TimeNICManager',
    'TimeNICInfo',
    'PTPInfo',
    'PTMStatus'
]