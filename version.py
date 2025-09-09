"""
Версия проекта SHIWA NIC-PPS Configuration and Monitoring Tool
"""

__version__ = "1.1.0"
__version_info__ = (1, 1, 0)
__build_date__ = "2025-09-09"
__description__ = "SHIWA NIC-PPS Configuration and Monitoring Tool - Fixed PTP device detection for Intel I210"

def get_version():
    """Получить версию проекта"""
    return __version__

def get_version_info():
    """Получить информацию о версии"""
    return {
        "version": __version__,
        "version_info": __version_info__,
        "build_date": __build_date__,
        "description": __description__
    }
