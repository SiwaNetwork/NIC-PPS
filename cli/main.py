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
        
        console.print(f"[green]✓ Обнаружено Intel NIC карт: {len(nics)}[/green]")
        
        for nic in nics:
            status_color = "green" if nic.status == "up" else "red"
            console.print(f"  - {nic.name}: {nic.status} ({nic.speed})", style=status_color)
            
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


if __name__ == '__main__':
    cli() 