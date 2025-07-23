"""
CLI интерфейс для TimeNIC карт
Поддержка PPS, PTP, SMA, TCXO и PTM
"""

import click
import subprocess
import json
import sys
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

from core.timenic_manager import TimeNICManager, PPSMode, PTMStatus


console = Console()


@click.group()
def timenic():
    """TimeNIC CLI - управление TimeNIC картами (Intel I226 NIC, SMA, TCXO)"""
    pass


@timenic.command()
def list_timenics():
    """Список всех TimeNIC карт"""
    try:
        manager = TimeNICManager()
        timenics = manager.get_all_timenics()
        
        if not timenics:
            console.print("[yellow]TimeNIC карты не обнаружены[/yellow]")
            return
        
        table = Table(title="TimeNIC Карты")
        table.add_column("Интерфейс", style="cyan")
        table.add_column("MAC", style="green")
        table.add_column("IP", style="blue")
        table.add_column("Статус", style="yellow")
        table.add_column("Скорость", style="magenta")
        table.add_column("PPS Режим", style="red")
        table.add_column("TCXO", style="green")
        table.add_column("PTM", style="blue")
        table.add_column("SMA1", style="cyan")
        table.add_column("SMA2", style="cyan")
        
        for timenic in timenics:
            table.add_row(
                timenic.name,
                timenic.mac_address,
                timenic.ip_address,
                timenic.status,
                timenic.speed,
                timenic.pps_mode.value,
                "✓" if timenic.tcxo_enabled else "✗",
                timenic.ptm_status.value,
                timenic.sma1_status,
                timenic.sma2_status
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('interface')
def info(interface):
    """Подробная информация о TimeNIC карте"""
    try:
        manager = TimeNICManager()
        timenic = manager.get_timenic_by_name(interface)
        
        if not timenic:
            console.print(f"[red]TimeNIC карта {interface} не найдена[/red]")
            return
        
        # Создаем панель с информацией
        info_text = f"""
Интерфейс: {timenic.name}
MAC адрес: {timenic.mac_address}
IP адрес: {timenic.ip_address}
Статус: {timenic.status}
Скорость: {timenic.speed}
Дуплекс: {timenic.duplex}

PPS режим: {timenic.pps_mode.value}
TCXO включен: {'Да' if timenic.tcxo_enabled else 'Нет'}
PTM статус: {timenic.ptm_status.value}

PTP устройство: {timenic.ptp_device or 'Не найдено'}
PHC offset: {timenic.phc_offset or 'Неизвестно'}
PHC frequency: {timenic.phc_frequency or 'Неизвестно'}

SMA1 (SDP0) - выход PPS: {timenic.sma1_status}
SMA2 (SDP1) - вход PPS: {timenic.sma2_status}

Температура: {f'{timenic.temperature:.1f}°C' if timenic.temperature else 'Неизвестно'}
        """
        
        panel = Panel(info_text, title=f"TimeNIC: {interface}", border_style="blue")
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('interface')
@click.option('--mode', type=click.Choice(['disabled', 'input', 'output', 'both']), 
              required=True, help='Режим PPS')
def set_pps(interface, mode):
    """Установка режима PPS для TimeNIC"""
    try:
        manager = TimeNICManager()
        
        # Конвертируем строку в enum
        pps_mode = PPSMode(mode)
        
        with console.status(f"Установка PPS режима {mode} для {interface}..."):
            success = manager.set_pps_mode(interface, pps_mode)
        
        if success:
            console.print(f"[green]✓ PPS режим {mode} успешно установлен для {interface}[/green]")
        else:
            console.print(f"[red]✗ Ошибка при установке PPS режима {mode} для {interface}[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('interface')
@click.option('--enable/--disable', default=True, help='Включить/выключить TCXO')
def set_tcxo(interface, enable):
    """Управление TCXO для TimeNIC"""
    try:
        manager = TimeNICManager()
        
        with console.status(f"{'Включение' if enable else 'Выключение'} TCXO для {interface}..."):
            success = manager.set_tcxo_enabled(interface, enable)
        
        if success:
            console.print(f"[green]✓ TCXO {'включен' if enable else 'выключен'} для {interface}[/green]")
        else:
            console.print(f"[red]✗ Ошибка при управлении TCXO для {interface}[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('interface')
def start_phc_sync(interface):
    """Запуск синхронизации PHC по внешнему PPS"""
    try:
        manager = TimeNICManager()
        
        with console.status(f"Запуск синхронизации PHC для {interface}..."):
            success = manager.start_phc_synchronization(interface)
        
        if success:
            console.print(f"[green]✓ Синхронизация PHC запущена для {interface}[/green]")
            console.print("[yellow]Используйте Ctrl+C для остановки[/yellow]")
        else:
            console.print(f"[red]✗ Ошибка при запуске синхронизации PHC для {interface}[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('interface')
def enable_ptm(interface):
    """Включение PTM для TimeNIC"""
    try:
        manager = TimeNICManager()
        
        with console.status(f"Включение PTM для {interface}..."):
            success = manager.enable_ptm(interface)
        
        if success:
            console.print(f"[green]✓ PTM включен для {interface}[/green]")
        else:
            console.print(f"[red]✗ Ошибка при включении PTM для {interface}[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
def list_ptp():
    """Список всех PTP устройств"""
    try:
        manager = TimeNICManager()
        ptp_devices = manager.get_all_ptp_devices()
        
        if not ptp_devices:
            console.print("[yellow]PTP устройства не обнаружены[/yellow]")
            return
        
        table = Table(title="PTP Устройства")
        table.add_column("Устройство", style="cyan")
        table.add_column("Индекс", style="green")
        table.add_column("Имя", style="blue")
        table.add_column("Max Adj", style="yellow")
        table.add_column("Ext TS", style="magenta")
        table.add_column("Per Out", style="red")
        table.add_column("PPS", style="green")
        
        for ptp in ptp_devices:
            table.add_row(
                ptp.device,
                str(ptp.index),
                ptp.name,
                str(ptp.max_adj),
                str(ptp.n_ext_ts),
                str(ptp.n_per_out),
                "✓" if ptp.pps else "✗"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('ptp_device')
@click.option('--count', '-c', default=5, help='Количество событий для чтения')
def read_pps(ptp_device, count):
    """Чтение PPS событий с внешнего источника
    
    Пример: timenic read-pps /dev/ptp0 --count 10
    """
    try:
        manager = TimeNICManager()
        
        console.print(f"[cyan]Чтение {count} PPS событий с {ptp_device}...[/cyan]")
        console.print("[yellow]Ожидание событий (подключите внешний PPS к SMA2)...[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Чтение PPS событий...", total=count)
            
            events = manager.read_pps_events(ptp_device, count)
            
            progress.update(task, completed=count)
        
        if not events:
            console.print("[red]События не получены. Проверьте подключение PPS к SMA2[/red]")
            return
        
        table = Table(title=f"PPS События с {ptp_device}")
        table.add_column("Индекс", style="cyan")
        table.add_column("Временная метка", style="green")
        
        for event in events:
            table.add_row(
                str(event['index']),
                event['timestamp']
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('ptp_device')
@click.option('--period', '-p', default=1000000000, help='Период в наносекундах (1000000000 = 1 Гц)')
def set_period(ptp_device, period):
    """Установка периода PPS сигнала
    
    Примеры:
    - 1 Гц: timenic set-period /dev/ptp0 --period 1000000000
    - 10 Гц: timenic set-period /dev/ptp0 --period 100000000
    """
    try:
        manager = TimeNICManager()
        
        # Вычисляем частоту
        if period > 0:
            frequency = 1e9 / period
            console.print(f"[cyan]Установка периода {period} нс ({frequency:.2f} Гц) на {ptp_device}...[/cyan]")
        else:
            console.print(f"[red]Неверный период: {period}[/red]")
            return
        
        if manager.set_pps_period(ptp_device, period):
            console.print(f"[green]✓ Период успешно установлен: {period} нс ({frequency:.2f} Гц)[/green]")
        else:
            console.print(f"[red]✗ Ошибка при установке периода[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('interface')
def sync_phc(interface):
    """Синхронизация PHC с системным временем
    
    Пример: timenic sync-phc enp3s0
    """
    try:
        manager = TimeNICManager()
        
        console.print(f"[cyan]Синхронизация PHC с системным временем на {interface}...[/cyan]")
        
        if manager.sync_phc_to_system_time(interface):
            console.print(f"[green]✓ PHC успешно синхронизирован[/green]")
        else:
            console.print(f"[red]✗ Ошибка при синхронизации PHC[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.argument('interface')
@click.option('--interval', default=1, help='Интервал обновления в секундах')
def monitor(interface, interval):
    """Мониторинг TimeNIC карты в реальном времени"""
    try:
        manager = TimeNICManager()
        
        def generate_table():
            timenic = manager.get_timenic_by_name(interface)
            if not timenic:
                return Table(title=f"TimeNIC {interface} - Не найдена")
            
            stats = manager.get_statistics(interface)
            
            table = Table(title=f"TimeNIC {interface} - Мониторинг")
            table.add_column("Параметр", style="cyan")
            table.add_column("Значение", style="green")
            
            table.add_row("Статус", timenic.status)
            table.add_row("Скорость", timenic.speed)
            table.add_row("PPS режим", timenic.pps_mode.value)
            table.add_row("TCXO", "Включен" if timenic.tcxo_enabled else "Выключен")
            table.add_row("PTM", timenic.ptm_status.value)
            table.add_row("SMA1", timenic.sma1_status)
            table.add_row("SMA2", timenic.sma2_status)
            table.add_row("Температура", f"{timenic.temperature:.1f}°C" if timenic.temperature else "Неизвестно")
            table.add_row("PHC Offset", str(timenic.phc_offset) if timenic.phc_offset else "Неизвестно")
            table.add_row("PHC Frequency", str(timenic.phc_frequency) if timenic.phc_frequency else "Неизвестно")
            
            if 'rx_bytes' in stats:
                table.add_row("RX Bytes", f"{stats['rx_bytes']:,}")
            if 'tx_bytes' in stats:
                table.add_row("TX Bytes", f"{stats['tx_bytes']:,}")
            if 'rx_speed' in stats:
                rx_mbps = stats['rx_speed'] * 8 / 1_000_000  # Конвертируем в Mbps
                table.add_row("RX Speed", f"{rx_mbps:.2f} Mbps")
            if 'tx_speed' in stats:
                tx_mbps = stats['tx_speed'] * 8 / 1_000_000  # Конвертируем в Mbps
                table.add_row("TX Speed", f"{tx_mbps:.2f} Mbps")
            if 'rx_pps' in stats:
                table.add_row("RX PPS", f"{stats['rx_pps']:.0f}")
            if 'tx_pps' in stats:
                table.add_row("TX PPS", f"{stats['tx_pps']:.0f}")
            if 'rx_errors' in stats:
                table.add_row("RX Errors", f"{stats['rx_errors']:,}")
            if 'tx_errors' in stats:
                table.add_row("TX Errors", f"{stats['tx_errors']:,}")
            
            return table
        
        # Используем новый метод monitor_traffic
        def update_display(stats):
            timenic = manager.get_timenic_by_name(interface)
            if not timenic:
                return
                
            table = Table(title=f"TimeNIC {interface} - Мониторинг")
            table.add_column("Параметр", style="cyan")
            table.add_column("Значение", style="green")
            
            table.add_row("Статус", stats.get('status', 'unknown'))
            table.add_row("Скорость", stats.get('speed', 'unknown'))
            table.add_row("PPS режим", stats.get('pps_mode', 'disabled'))
            table.add_row("TCXO", "Включен" if stats.get('tcxo_enabled', False) else "Выключен")
            table.add_row("PTM", stats.get('ptm_status', 'unsupported'))
            table.add_row("SMA1", stats.get('sma1_status', 'disabled'))
            table.add_row("SMA2", stats.get('sma2_status', 'disabled'))
            
            if 'temperature' in stats and stats['temperature']:
                table.add_row("Температура", f"{stats['temperature']:.1f}°C")
            if 'phc_offset' in stats and stats['phc_offset']:
                table.add_row("PHC Offset", str(stats['phc_offset']))
            if 'phc_frequency' in stats and stats['phc_frequency']:
                table.add_row("PHC Frequency", str(stats['phc_frequency']))
            
            # Статистика трафика
            if 'rx_bytes' in stats:
                table.add_row("RX Bytes", f"{stats['rx_bytes']:,}")
            if 'tx_bytes' in stats:
                table.add_row("TX Bytes", f"{stats['tx_bytes']:,}")
            if 'rx_speed' in stats:
                rx_mbps = stats['rx_speed'] * 8 / 1_000_000
                table.add_row("RX Speed", f"{rx_mbps:.2f} Mbps")
            if 'tx_speed' in stats:
                tx_mbps = stats['tx_speed'] * 8 / 1_000_000
                table.add_row("TX Speed", f"{tx_mbps:.2f} Mbps")
            if 'rx_pps' in stats:
                table.add_row("RX PPS", f"{stats['rx_pps']:.0f}")
            if 'tx_pps' in stats:
                table.add_row("TX PPS", f"{stats['tx_pps']:.0f}")
            if 'rx_errors' in stats:
                table.add_row("RX Errors", f"{stats['rx_errors']:,}")
            if 'tx_errors' in stats:
                table.add_row("TX Errors", f"{stats['tx_errors']:,}")
                
            console.clear()
            console.print(table)
        
        try:
            # Запускаем мониторинг с callback функцией
            manager.monitor_traffic(interface, callback=update_display, interval=interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Мониторинг остановлен[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
def install_driver():
    """Установка драйвера TimeNIC с патчем для PPS"""
    try:
        manager = TimeNICManager()
        
        console.print("[yellow]Внимание: Установка драйвера требует прав root[/yellow]")
        console.print("[yellow]Система будет перезагружена после установки[/yellow]")
        
        if not click.confirm("Продолжить установку драйвера?"):
            return
        
        with console.status("Установка драйвера TimeNIC..."):
            success = manager.install_timenic_driver()
        
        if success:
            console.print("[green]✓ Драйвер TimeNIC успешно установлен[/green]")
            console.print("[yellow]Перезагрузите систему для применения изменений[/yellow]")
        else:
            console.print("[red]✗ Ошибка при установке драйвера TimeNIC[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
def create_service():
    """Создание systemd сервиса для автозапуска TimeNIC"""
    try:
        # Запускаем скрипт создания сервиса
        result = subprocess.run(
            [sys.executable, "scripts/create_timenic_service.py"],
            check=True
        )
        
        if result.returncode == 0:
            console.print("[green]✓ Systemd сервис успешно создан[/green]")
        else:
            console.print("[red]✗ Ошибка при создании сервиса[/red]")
            
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        console.print("[yellow]Попробуйте запустить с правами root: sudo python run.py --cli timenic create-service[/yellow]")
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
@click.option('--output', help='Файл для сохранения конфигурации')
def config(output):
    """Сохранение/загрузка конфигурации TimeNIC"""
    try:
        manager = TimeNICManager()
        timenics = manager.get_all_timenics()
        
        config_data = []
        for timenic in timenics:
            config_data.append({
                'interface': timenic.name,
                'pps_mode': timenic.pps_mode.value,
                'tcxo_enabled': timenic.tcxo_enabled,
                'ptm_status': timenic.ptm_status.value
            })
        
        if output:
            with open(output, 'w') as f:
                json.dump(config_data, f, indent=2)
            console.print(f"[green]✓ Конфигурация сохранена в {output}[/green]")
        else:
            console.print(json.dumps(config_data, indent=2))
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@timenic.command()
def status():
    """Общий статус TimeNIC системы"""
    try:
        manager = TimeNICManager()
        timenics = manager.get_all_timenics()
        ptp_devices = manager.get_all_ptp_devices()
        
        # Создаем панель со статусом
        status_text = f"""
TimeNIC карты: {len(timenics)}
PTP устройств: {len(ptp_devices)}

Системные утилиты:
- testptp: {'✓' if subprocess.run(['which', 'testptp'], capture_output=True).returncode == 0 else '✗'}
- ts2phc: {'✓' if subprocess.run(['which', 'ts2phc'], capture_output=True).returncode == 0 else '✗'}
- phc_ctl: {'✓' if subprocess.run(['which', 'phc_ctl'], capture_output=True).returncode == 0 else '✗'}
- ethtool: {'✓' if subprocess.run(['which', 'ethtool'], capture_output=True).returncode == 0 else '✗'}

Драйверы:
- igc: {'✓' if subprocess.run(['lsmod'], capture_output=True, text=True).stdout.find('igc') != -1 else '✗'}
        """
        
        panel = Panel(status_text, title="Статус TimeNIC системы", border_style="green")
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


if __name__ == '__main__':
    timenic()