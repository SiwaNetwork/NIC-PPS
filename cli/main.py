"""
CLI интерфейс для конфигурации и мониторинга Intel NIC
"""

import sys
import os
import json
import time
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

# Добавляем путь к core модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.nic_manager import IntelNICManager, PPSMode, NICInfo


console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Intel NIC PPS Configuration and Monitoring Tool - CLI версия"""
    pass


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Файл для сохранения вывода в JSON')
def list_nics(output):
    """Список всех обнаруженных Intel NIC карт"""
    with console.status("[bold green]Обнаружение NIC карт..."):
        nic_manager = IntelNICManager()
        nics = nic_manager.get_all_nics()
    
    if not nics:
        console.print("[red]Intel NIC карты не обнаружены[/red]")
        return
    
    # Создаем таблицу
    table = Table(title="Intel NIC карты")
    table.add_column("Имя", style="cyan")
    table.add_column("MAC адрес", style="magenta")
    table.add_column("IP адрес", style="green")
    table.add_column("Статус", style="yellow")
    table.add_column("Скорость", style="blue")
    table.add_column("PPS режим", style="red")
    table.add_column("TCXO", style="white")
    table.add_column("Температура", style="orange")
    
    for nic in nics:
        status_color = "green" if nic.status == "up" else "red"
        tcxo_text = "✓" if nic.tcxo_enabled else "✗"
        temp_text = f"{nic.temperature:.1f}°C" if nic.temperature else "N/A"
        
        table.add_row(
            nic.name,
            nic.mac_address,
            nic.ip_address,
            f"[{status_color}]{nic.status}[/{status_color}]",
            nic.speed,
            nic.pps_mode.value,
            tcxo_text,
            temp_text
        )
    
    console.print(table)
    
    # Сохраняем в JSON если указан файл
    if output:
        data = []
        for nic in nics:
            data.append({
                'name': nic.name,
                'mac_address': nic.mac_address,
                'ip_address': nic.ip_address,
                'status': nic.status,
                'speed': nic.speed,
                'duplex': nic.duplex,
                'pps_mode': nic.pps_mode.value,
                'tcxo_enabled': nic.tcxo_enabled,
                'temperature': nic.temperature
            })
        
        with open(output, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]Данные сохранены в {output}[/green]")


@cli.command()
@click.argument('interface')
@click.option('--mode', type=click.Choice(['disabled', 'input', 'output', 'both']), 
              required=True, help='Режим PPS')
def set_pps(interface, mode):
    """Установка режима PPS для указанной NIC карты"""
    with console.status(f"[bold green]Настройка PPS для {interface}..."):
        nic_manager = IntelNICManager()
        
        # Проверяем существование карты
        nic = nic_manager.get_nic_by_name(interface)
        if not nic:
            console.print(f"[red]NIC карта {interface} не найдена[/red]")
            return
        
        # Устанавливаем режим
        pps_mode = PPSMode(mode)
        success = nic_manager.set_pps_mode(interface, pps_mode)
        
        if success:
            console.print(f"[green]PPS режим успешно изменен на {mode}[/green]")
        else:
            console.print(f"[red]Ошибка при изменении PPS режима[/red]")


@cli.command()
@click.argument('interface')
@click.option('--enable/--disable', default=True, help='Включить/отключить TCXO')
def set_tcxo(interface, enable):
    """Настройка TCXO для указанной NIC карты"""
    with console.status(f"[bold green]Настройка TCXO для {interface}..."):
        nic_manager = IntelNICManager()
        
        # Проверяем существование карты
        nic = nic_manager.get_nic_by_name(interface)
        if not nic:
            console.print(f"[red]NIC карта {interface} не найдена[/red]")
            return
        
        # Устанавливаем TCXO
        success = nic_manager.set_tcxo_enabled(interface, enable)
        
        if success:
            status = "включен" if enable else "отключен"
            console.print(f"[green]TCXO успешно {status}[/green]")
        else:
            console.print(f"[red]Ошибка при настройке TCXO[/red]")


@cli.command()
@click.argument('interface')
@click.option('--interval', '-i', default=1, help='Интервал обновления в секундах')
@click.option('--duration', '-d', default=0, help='Длительность мониторинга в секундах (0 = бесконечно)')
def monitor(interface, interval, duration):
    """Мониторинг производительности NIC карты"""
    nic_manager = IntelNICManager()
    
    # Проверяем существование карты
    nic = nic_manager.get_nic_by_name(interface)
    if not nic:
        console.print(f"[red]NIC карта {interface} не найдена[/red]")
        return
    
    console.print(f"[bold green]Мониторинг {interface}[/bold green]")
    console.print(f"Интервал: {interval}с, Длительность: {'бесконечно' if duration == 0 else f'{duration}с'}")
    console.print()
    
    start_time = time.time()
    last_stats = None
    
    def create_stats_table(stats, temp):
        """Создание таблицы статистики"""
        table = Table(title=f"Статистика {interface}")
        table.add_column("Метрика", style="cyan")
        table.add_column("Значение", style="green")
        
        if stats:
            # Вычисляем скорости если есть предыдущие данные
            if last_stats:
                rx_speed = stats['rx_bytes'] - last_stats['rx_bytes']
                tx_speed = stats['tx_bytes'] - last_stats['tx_bytes']
                table.add_row("RX скорость", f"{rx_speed:,} байт/с")
                table.add_row("TX скорость", f"{tx_speed:,} байт/с")
            
            table.add_row("RX байт", f"{stats['rx_bytes']:,}")
            table.add_row("TX байт", f"{stats['tx_bytes']:,}")
            table.add_row("RX пакетов", f"{stats['rx_packets']:,}")
            table.add_row("TX пакетов", f"{stats['tx_packets']:,}")
            table.add_row("RX ошибок", f"{stats['rx_errors']:,}")
            table.add_row("TX ошибок", f"{stats['tx_errors']:,}")
            table.add_row("RX отброшено", f"{stats['rx_dropped']:,}")
            table.add_row("TX отброшено", f"{stats['tx_dropped']:,}")
        
        if temp:
            table.add_row("Температура", f"{temp:.1f}°C")
        
        return table
    
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                # Проверяем время выполнения
                if duration > 0 and (time.time() - start_time) > duration:
                    break
                
                # Получаем данные
                stats = nic_manager.get_statistics(interface)
                temp = nic_manager.get_temperature(interface)
                
                # Создаем таблицу
                table = create_stats_table(stats, temp)
                live.update(table)
                
                last_stats = stats
                time.sleep(interval)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Мониторинг остановлен пользователем[/yellow]")


@cli.command()
@click.argument('interface')
def info(interface):
    """Подробная информация о NIC карте"""
    nic_manager = IntelNICManager()
    
    # Получаем информацию о карте
    nic = nic_manager.get_nic_by_name(interface)
    if not nic:
        console.print(f"[red]NIC карта {interface} не найдена[/red]")
        return
    
    # Получаем дополнительную информацию
    stats = nic_manager.get_statistics(interface)
    temp = nic_manager.get_temperature(interface)
    
    # Создаем панель с информацией
    info_text = f"""
[bold]Основная информация:[/bold]
Имя: {nic.name}
MAC адрес: {nic.mac_address}
IP адрес: {nic.ip_address}
Статус: {nic.status}
Скорость: {nic.speed}
Дуплекс: {nic.duplex}

[bold]PPS и TCXO:[/bold]
PPS режим: {nic.pps_mode.value}
TCXO: {'Включен' if nic.tcxo_enabled else 'Отключен'}

[bold]Мониторинг:[/bold]
Температура: {f'{temp:.1f}°C' if temp else 'N/A'}
"""
    
    if stats:
        info_text += f"""
[bold]Статистика:[/bold]
Принято байт: {stats.get('rx_bytes', 0):,}
Отправлено байт: {stats.get('tx_bytes', 0):,}
Принято пакетов: {stats.get('rx_packets', 0):,}
Отправлено пакетов: {stats.get('tx_packets', 0):,}
Ошибки приема: {stats.get('rx_errors', 0):,}
Ошибки отправки: {stats.get('tx_errors', 0):,}
"""
    
    panel = Panel(info_text.strip(), title=f"Информация о {interface}", border_style="blue")
    console.print(panel)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), help='Файл конфигурации JSON')
@click.option('--output', '-o', type=click.Path(), help='Файл для сохранения конфигурации')
def config(config, output):
    """Управление конфигурацией NIC карт"""
    nic_manager = IntelNICManager()
    
    if config:
        # Загружаем конфигурацию из файла
        try:
            with open(config, 'r') as f:
                config_data = json.load(f)
            
            console.print(f"[green]Загружена конфигурация из {config}[/green]")
            
            # Применяем конфигурацию
            for nic_config in config_data:
                interface = nic_config.get('interface')
                if not interface:
                    continue
                
                # Проверяем существование карты
                nic = nic_manager.get_nic_by_name(interface)
                if not nic:
                    console.print(f"[yellow]NIC карта {interface} не найдена, пропускаем[/yellow]")
                    continue
                
                # Применяем PPS настройки
                if 'pps_mode' in nic_config:
                    mode = PPSMode(nic_config['pps_mode'])
                    success = nic_manager.set_pps_mode(interface, mode)
                    if success:
                        console.print(f"[green]PPS режим для {interface}: {mode.value}[/green]")
                    else:
                        console.print(f"[red]Ошибка установки PPS для {interface}[/red]")
                
                # Применяем TCXO настройки
                if 'tcxo_enabled' in nic_config:
                    enabled = nic_config['tcxo_enabled']
                    success = nic_manager.set_tcxo_enabled(interface, enabled)
                    if success:
                        status = "включен" if enabled else "отключен"
                        console.print(f"[green]TCXO для {interface}: {status}[/green]")
                    else:
                        console.print(f"[red]Ошибка установки TCXO для {interface}[/red]")
        
        except Exception as e:
            console.print(f"[red]Ошибка загрузки конфигурации: {e}[/red]")
    
    if output:
        # Сохраняем текущую конфигурацию
        nics = nic_manager.get_all_nics()
        config_data = []
        
        for nic in nics:
            config_data.append({
                'interface': nic.name,
                'pps_mode': nic.pps_mode.value,
                'tcxo_enabled': nic.tcxo_enabled
            })
        
        with open(output, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        console.print(f"[green]Конфигурация сохранена в {output}[/green]")


@cli.command()
def status():
    """Общий статус всех NIC карт"""
    nic_manager = IntelNICManager()
    nics = nic_manager.get_all_nics()
    
    if not nics:
        console.print("[red]Intel NIC карты не обнаружены[/red]")
        return
    
    # Создаем layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body")
    )
    
    # Заголовок
    layout["header"].update(Panel(
        f"Обнаружено Intel NIC карт: {len(nics)}",
        title="Статус системы",
        border_style="green"
    ))
    
    # Тело с информацией о картах
    body_content = ""
    for nic in nics:
        status_icon = "🟢" if nic.status == "up" else "🔴"
        tcxo_icon = "✓" if nic.tcxo_enabled else "✗"
        temp_text = f"{nic.temperature:.1f}°C" if nic.temperature else "N/A"
        
        body_content += f"""
{status_icon} [bold]{nic.name}[/bold]
   MAC: {nic.mac_address}
   IP: {nic.ip_address}
   Скорость: {nic.speed}
   PPS: {nic.pps_mode.value}
   TCXO: {tcxo_icon}
   Температура: {temp_text}
"""
    
    layout["body"].update(Panel(body_content.strip(), border_style="blue"))
    console.print(layout)


if __name__ == "__main__":
    cli()