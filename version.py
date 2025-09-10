"""
Версия проекта SHIWA NIC-PPS Configuration and Monitoring Tool
"""

__version__ = "1.2.0"
__version_info__ = (1, 2, 0)
__build_date__ = "2025-09-10"
__description__ = "SHIWA NIC-PPS Configuration and Monitoring Tool - Modern web interface with monitoring and metrics"

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
