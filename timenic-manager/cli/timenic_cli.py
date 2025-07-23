#!/usr/bin/env python3
"""
TimeNIC CLI - Command Line Interface for TimeNIC Management
"""

import click
import json
import sys
import os
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.timenic_core import TimeNICManager, PTMStatus

console = Console()


@click.group()
@click.option('--interface', '-i', default='enp3s0', help='Network interface name')
@click.option('--device', '-d', default='/dev/ptp0', help='PTP device path')
@click.pass_context
def cli(ctx, interface, device):
    """TimeNIC CLI - Manage TimeNIC PCIe card with Intel I226"""
    ctx.ensure_object(dict)
    ctx.obj['manager'] = TimeNICManager(interface, device)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current TimeNIC status"""
    manager = ctx.obj['manager']
    
    with console.status("[bold green]Checking TimeNIC status...") as status:
        status_data = manager.get_status()
    
    # Create status table
    table = Table(title="TimeNIC Status", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Device info
    if status_data['device']:
        device = status_data['device']
        table.add_row(
            "PTP Device",
            "✓ Available",
            f"{device['interface']} → {device['ptp_device']}"
        )
        table.add_row(
            "Clock Index",
            str(device['clock_index']),
            f"Capabilities: {', '.join(device['capabilities'])}"
        )
    else:
        table.add_row("PTP Device", "✗ Not Found", "Check interface name")
    
    # PPS Output
    table.add_row(
        "PPS Output (SMA1)",
        "✓ Enabled" if status_data['pps_output']['enabled'] else "✗ Disabled",
        "1 Hz on SDP0"
    )
    
    # PPS Input
    table.add_row(
        "PPS Input (SMA2)",
        "✓ Enabled" if status_data['pps_input']['enabled'] else "✗ Disabled",
        "External on SDP1"
    )
    
    # PTM Status
    ptm_icon = {
        "NOT_SUPPORTED": "✗",
        "DISABLED": "○",
        "ENABLED": "✓"
    }.get(status_data['ptm_status'], "?")
    
    table.add_row(
        "PTM Support",
        f"{ptm_icon} {status_data['ptm_status']}",
        "PCIe Time Management"
    )
    
    # PHC Time
    if status_data['phc_time']:
        phc_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status_data['phc_time']))
        table.add_row("PHC Time", phc_time, f"{status_data['phc_time']:.9f}")
    
    console.print(table)


@cli.command()
@click.pass_context
def install_driver(ctx):
    """Install patched igc driver for PPS support"""
    manager = ctx.obj['manager']
    
    # Check if running as root
    if os.geteuid() != 0:
        console.print("[red]Error: Driver installation requires root privileges[/red]")
        console.print("Please run with sudo: [yellow]sudo timenic-cli install-driver[/yellow]")
        sys.exit(1)
    
    console.print(Panel.fit(
        "[bold yellow]Driver Installation[/bold yellow]\n"
        "This will install the patched igc driver with PPS support.\n"
        "[red]System will require reboot after installation.[/red]",
        border_style="yellow"
    ))
    
    if not click.confirm("Continue with driver installation?"):
        console.print("[yellow]Installation cancelled[/yellow]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Installing driver...", total=None)
        
        if manager.install_driver():
            progress.update(task, description="[green]Driver installed successfully![/green]")
            console.print("\n[bold green]✓ Driver installation completed[/bold green]")
            console.print("[yellow]Please reboot your system to apply changes[/yellow]")
        else:
            progress.update(task, description="[red]Installation failed[/red]")
            console.print("\n[bold red]✗ Driver installation failed[/bold red]")
            console.print("Check the logs for more details")


@cli.command()
@click.option('--frequency', '-f', default=1.0, help='Output frequency in Hz')
@click.pass_context
def enable_pps_output(ctx, frequency):
    """Enable PPS output on SMA1"""
    manager = ctx.obj['manager']
    
    # Convert Hz to nanoseconds period
    period_ns = int(1e9 / frequency)
    
    console.print(f"[cyan]Enabling PPS output at {frequency} Hz...[/cyan]")
    
    if manager.enable_pps_output(period_ns):
        console.print(f"[green]✓ PPS output enabled on SMA1 at {frequency} Hz[/green]")
    else:
        console.print("[red]✗ Failed to enable PPS output[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def enable_pps_input(ctx):
    """Enable PPS input on SMA2"""
    manager = ctx.obj['manager']
    
    console.print("[cyan]Enabling PPS input...[/cyan]")
    
    if manager.enable_pps_input():
        console.print("[green]✓ PPS input enabled on SMA2[/green]")
    else:
        console.print("[red]✗ Failed to enable PPS input[/red]")
        sys.exit(1)


@cli.command()
@click.option('--count', '-n', default=5, help='Number of events to read')
@click.pass_context
def read_pps_events(ctx, count):
    """Read PPS input events from SMA2"""
    manager = ctx.obj['manager']
    
    console.print(f"[cyan]Reading {count} PPS events...[/cyan]")
    
    timestamps = manager.read_pps_events(count)
    
    if timestamps:
        table = Table(title="PPS Events", show_header=True, header_style="bold magenta")
        table.add_column("Event #", style="cyan", no_wrap=True)
        table.add_column("Timestamp", style="green")
        table.add_column("Time", style="yellow")
        
        for i, ts in enumerate(timestamps):
            time_str = time.strftime('%H:%M:%S', time.localtime(ts))
            table.add_row(str(i+1), f"{ts:.9f}", time_str)
        
        console.print(table)
    else:
        console.print("[red]✗ No PPS events received[/red]")
        console.print("[yellow]Make sure external PPS is connected to SMA2[/yellow]")


@cli.command()
@click.option('--pin-index', '-p', default=1, help='Pin index for PPS input')
@click.option('--monitor', '-m', is_flag=True, help='Monitor sync status')
@click.pass_context
def sync_external_pps(ctx, pin_index, monitor):
    """Synchronize PHC to external PPS signal"""
    manager = ctx.obj['manager']
    
    console.print(f"[cyan]Starting synchronization to external PPS on pin {pin_index}...[/cyan]")
    
    # Enable PPS input first
    manager.enable_pps_input()
    
    # Start synchronization
    process = manager.sync_to_external_pps(pin_index)
    
    if not monitor:
        console.print("[green]✓ Synchronization started[/green]")
        console.print("[yellow]Run with --monitor to see live status[/yellow]")
        return
    
    # Monitor synchronization status
    console.print("[green]Monitoring synchronization status (Ctrl+C to stop)...[/green]\n")
    
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                # Read ts2phc output
                output = process.stdout.readline()
                if output:
                    sync_status = manager.get_sync_status(output)
                    if sync_status:
                        # Create status panel
                        status_text = f"""[bold cyan]Synchronization Status[/bold cyan]
                        
Status: {'[green]SYNCED[/green]' if sync_status.is_synced else '[yellow]SYNCING[/yellow]'}
Offset: {sync_status.offset_ns:.1f} ns
Frequency: {sync_status.frequency_ppb:+.1f} ppb
RMS: {sync_status.rms_ns:.1f} ns
                        """
                        
                        panel = Panel(
                            status_text,
                            border_style="green" if sync_status.is_synced else "yellow"
                        )
                        live.update(panel)
                
                # Check if process is still running
                if process.poll() is not None:
                    console.print("[red]✗ ts2phc process terminated[/red]")
                    break
                    
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping synchronization monitor...[/yellow]")
        process.terminate()


@cli.command()
@click.option('--pci-address', '-p', help='PCI address of device (e.g., 0000:03:00.0)')
@click.pass_context
def enable_ptm(ctx, pci_address):
    """Enable PTM (Precision Time Management)"""
    manager = ctx.obj['manager']
    
    # Check PTM support
    ptm_status = manager.check_ptm_support()
    
    if ptm_status == PTMStatus.NOT_SUPPORTED:
        console.print("[red]✗ PTM is not supported on this system[/red]")
        console.print("[yellow]Check CPU compatibility at:[/yellow]")
        console.print("https://www.opencompute.org/wiki/PTM_Readiness")
        sys.exit(1)
    
    if ptm_status == PTMStatus.ENABLED:
        console.print("[green]✓ PTM is already enabled[/green]")
        return
    
    if not pci_address:
        console.print("[red]Error: PCI address required[/red]")
        console.print("[yellow]Find your device with: lspci | grep Ethernet[/yellow]")
        sys.exit(1)
    
    console.print(f"[cyan]Enabling PTM for device {pci_address}...[/cyan]")
    
    if manager.enable_ptm(pci_address):
        console.print("[green]✓ PTM enabled successfully[/green]")
    else:
        console.print("[red]✗ Failed to enable PTM[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def quick_setup(ctx):
    """Quick setup wizard for TimeNIC"""
    manager = ctx.obj['manager']
    
    console.print(Panel.fit(
        "[bold cyan]TimeNIC Quick Setup Wizard[/bold cyan]\n"
        "This will configure your TimeNIC for basic operation",
        border_style="cyan"
    ))
    
    # Check device
    console.print("\n[yellow]1. Checking PTP device...[/yellow]")
    device = manager.check_device()
    if device:
        console.print(f"[green]✓ Found {device.interface} → {device.device}[/green]")
    else:
        console.print("[red]✗ PTP device not found[/red]")
        sys.exit(1)
    
    # Enable PPS output
    console.print("\n[yellow]2. Enabling PPS output on SMA1...[/yellow]")
    if manager.enable_pps_output():
        console.print("[green]✓ PPS output enabled (1 Hz)[/green]")
    else:
        console.print("[red]✗ Failed to enable PPS output[/red]")
    
    # Enable PPS input
    console.print("\n[yellow]3. Enabling PPS input on SMA2...[/yellow]")
    if manager.enable_pps_input():
        console.print("[green]✓ PPS input enabled[/green]")
    else:
        console.print("[red]✗ Failed to enable PPS input[/red]")
    
    # Check PTM
    console.print("\n[yellow]4. Checking PTM support...[/yellow]")
    ptm_status = manager.check_ptm_support()
    console.print(f"[cyan]PTM Status: {ptm_status.name}[/cyan]")
    
    console.print("\n[bold green]✓ Quick setup completed![/bold green]")
    console.print("\nNext steps:")
    console.print("- Connect external PPS to SMA2")
    console.print("- Run: [yellow]timenic-cli sync-external-pps --monitor[/yellow]")


@cli.command()
@click.option('--output', '-o', type=click.File('w'), help='Output file (JSON)')
@click.pass_context
def export_config(ctx, output):
    """Export current configuration"""
    manager = ctx.obj['manager']
    
    config = {
        "interface": manager.interface,
        "ptp_device": manager.ptp_device,
        "status": manager.get_status()
    }
    
    if output:
        json.dump(config, output, indent=2)
        console.print(f"[green]✓ Configuration exported to {output.name}[/green]")
    else:
        console.print(json.dumps(config, indent=2))


if __name__ == '__main__':
    cli()