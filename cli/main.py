"""
CLI интерфейс для Intel NIC карт
Поддержка PPS и мониторинга
"""

import click
import subprocess
import json
import sys
import os
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.nic_manager import IntelNICManager

console = Console()


@click.group()
def cli():
    """Intel NIC CLI - управление Intel сетевыми картами"""
    pass


@cli.command()
def list_nics():
    """Список всех Intel NIC карт"""
    try:
        manager = IntelNICManager()
        nics = manager.get_all_nics()
        
        if not nics:
            console.print("[yellow]Intel NIC карты не обнаружены[/yellow]")
            return
        
        table = Table(title="Intel NIC Карты")
        table.add_column("Интерфейс", style="cyan")
        table.add_column("MAC", style="green")
        table.add_column("IP", style="blue")
        table.add_column("Статус", style="yellow")
        table.add_column("Скорость", style="magenta")
        table.add_column("Дуплекс", style="red")
        
        for nic in nics:
            table.add_row(
                nic.name,
                nic.mac_address,
                nic.ip_address,
                nic.status,
                nic.speed,
                nic.duplex
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
@click.argument('interface')
def info(interface):
    """Подробная информация о NIC карте"""
    try:
        manager = IntelNICManager()
        nic = manager.get_nic_by_name(interface)
        
        if not nic:
            console.print(f"[red]NIC карта {interface} не найдена[/red]")
            return
        
        # Создаем панель с информацией
        info_text = f"""
Интерфейс: {nic.name}
MAC адрес: {nic.mac_address}
IP адрес: {nic.ip_address}
Статус: {nic.status}
Скорость: {nic.speed}
Дуплекс: {nic.duplex}
MTU: {nic.mtu}
"""
        
        panel = Panel(info_text, title=f"Информация о {interface}", border_style="blue")
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
@click.argument('interface')
@click.option('--mode', type=click.Choice(['disabled', 'input', 'output', 'both']), 
              required=True, help='Режим PPS')
def set_pps(interface, mode):
    """Установка PPS режима для NIC карты"""
    try:
        manager = IntelNICManager()
        
        # Преобразуем строку в PPSMode
        from core.nic_manager import PPSMode
        pps_mode = PPSMode(mode)
        
        success = manager.set_pps_mode(interface, pps_mode)
        
        if success:
            console.print(f"[green]✓ PPS режим установлен: {interface} -> {mode}[/green]")
        else:
            console.print(f"[red]✗ Ошибка установки PPS режима[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
@click.argument('interface')
@click.option('--interval', default=1, help='Интервал обновления в секундах')
def monitor(interface, interval):
    """Мониторинг NIC карты"""
    try:
        manager = IntelNICManager()
        
        with Live(auto_refresh=False) as live:
            while True:
                try:
                    nic = manager.get_nic_by_name(interface)
                    if not nic:
                        console.print(f"[red]NIC карта {interface} не найдена[/red]")
                        break
                    
                    # Создаем таблицу статистики
                    table = Table(title=f"Мониторинг {interface}")
                    table.add_column("Параметр", style="cyan")
                    table.add_column("Значение", style="green")
                    
                    table.add_row("Статус", nic.status)
                    table.add_row("Скорость", nic.speed)
                    table.add_row("Дуплекс", nic.duplex)
                    table.add_row("IP адрес", nic.ip_address)
                    table.add_row("MAC адрес", nic.mac_address)
                    
                    live.update(table)
                    
                    import time
                    time.sleep(interval)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Мониторинг остановлен[/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]Ошибка мониторинга: {e}[/red]")
                    break
                    
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
def status():
    """Общий статус системы"""
    try:
        manager = IntelNICManager()
        nics = manager.get_all_nics()
        
        if not nics:
            console.print("[yellow]Intel NIC карты не обнаружены[/yellow]")
            return
        
        # Создаем таблицу статуса
        table = Table(title="Статус Intel NIC")
        table.add_column("Интерфейс", style="cyan")
        table.add_column("Статус", style="yellow")
        table.add_column("PPS", style="green")
        table.add_column("TCXO", style="magenta")
        
        for nic in nics:
            status_color = "green" if nic.status == "up" else "red"
            pps_color = "green" if nic.pps_mode.value != "disabled" else "red"
            tcxo_color = "green" if nic.tcxo_enabled else "red"
            
            table.add_row(
                nic.name,
                f"[{status_color}]{nic.status}[/{status_color}]",
                f"[{pps_color}]{nic.pps_mode.value}[/{pps_color}]",
                f"[{tcxo_color}]{'✓' if nic.tcxo_enabled else '✗'}[/{tcxo_color}]"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
@click.argument('source_ptp')
@click.argument('target_ptp')
def start_phc_sync(source_ptp, target_ptp):
    """Запуск PHC2SYS синхронизации между часами"""
    try:
        if source_ptp == target_ptp:
            console.print("[red]Источник и цель не могут быть одинаковыми[/red]")
            return
        
        manager = IntelNICManager()
        success = manager.start_phc_sync(source_ptp, target_ptp)
        
        if success:
            console.print(f"[green]✅ PHC2SYS синхронизация запущена: {source_ptp} -> {target_ptp}[/green]")
        else:
            console.print("[red]❌ Не удалось запустить PHC2SYS синхронизацию[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
def stop_phc_sync():
    """Остановка PHC2SYS синхронизации"""
    try:
        manager = IntelNICManager()
        success = manager.stop_phc_sync()
        
        if success:
            console.print("[green]✅ PHC2SYS синхронизация остановлена[/green]")
        else:
            console.print("[red]❌ Не удалось остановить PHC2SYS синхронизацию[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
@click.argument('interface')
@click.argument('ptp_device')
def start_ts2phc_sync(interface, ptp_device):
    """Запуск TS2PHC синхронизации по внешнему PPS"""
    try:
        manager = IntelNICManager()
        success = manager.start_ts2phc_sync(interface, ptp_device)
        
        if success:
            console.print(f"[green]✅ TS2PHC синхронизация запущена для {interface}[/green]")
        else:
            console.print("[red]❌ Не удалось запустить TS2PHC синхронизацию[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
def stop_ts2phc_sync():
    """Остановка TS2PHC синхронизации"""
    try:
        manager = IntelNICManager()
        success = manager.stop_ts2phc_sync()
        
        if success:
            console.print("[green]✅ TS2PHC синхронизация остановлена[/green]")
        else:
            console.print("[red]❌ Не удалось остановить TS2PHC синхронизацию[/red]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


@cli.command()
def sync_status():
    """Статус синхронизации PHC"""
    try:
        manager = IntelNICManager()
        status = manager.get_sync_status()
        
        console.print("[bold cyan]Статус синхронизации PHC:[/bold cyan]")
        console.print(f"  PHC2SYS запущен: [{'green' if status['phc2sys_running'] else 'red'}]{status['phc2sys_running']}[/{'green' if status['phc2sys_running'] else 'red'}]")
        console.print(f"  TS2PHC запущен: [{'green' if status['ts2phc_running'] else 'red'}]{status['ts2phc_running']}[/{'green' if status['ts2phc_running'] else 'red'}]")
        
        if status['phc2sys_pid']:
            console.print(f"  PHC2SYS PID: [yellow]{status['phc2sys_pid']}[/yellow]")
        if status['ts2phc_pid']:
            console.print(f"  TS2PHC PID: [yellow]{status['ts2phc_pid']}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


if __name__ == '__main__':
    cli() 