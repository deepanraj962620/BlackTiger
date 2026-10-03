import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.prompt import Prompt
from modules.system_info import system_info_page
from modules.camera_portal import camera_portal_page
from modules.ai_security import ai_security_page
from modules.security_health import security_health_page
from modules.web_audit import web_audit_page

for stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

console = Console()
VERSION = "5.5"
AUTHOR = "Deepanraj C"
BANNER = r"""
██████╗ ██╗      █████╗  ██████╗██╗  ██╗████████╗██╗ ██████╗ ███████╗██████╗
██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝╚══██╔══╝██║██╔════╝ ██╔════╝██╔══██╗
██████╔╝██║     ███████║██║     █████╔╝    ██║   ██║██║  ███╗█████╗  ██████╔╝
██╔══██╗██║     ██╔══██║██║     ██╔═██╗    ██║   ██║██║   ██║██╔══╝  ██╔══██╗
██████╔╝███████╗██║  ██║╚██████╗██║  ██╗   ██║   ██║╚██████╔╝███████╗██║  ██║
╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
"""

def header():
    console.clear()
    console.print(BANNER, style="bold green")
    meta = (
        f"[green]Version  : {VERSION}[/green]\n"
        f"[green]Author   : {AUTHOR}[/green]\n"
        "[green]Platform : Windows / Kali / Debian / Ubuntu[/green]\n"
        "[dim green]Authorized testing and local diagnostics only[/dim green]"
    )
    console.print(Align.right(Panel.fit(meta, border_style="green")))

def menu():
    t = Table(show_header=False, border_style="green")
    for a,b in [
        ("[1]","System Information"),
        ("[2]","Camera Access Link / Browser Recorder"),
        ("[3]","AI Security Assistant / Code Generator"),
        ("[4]","Local Security Health: Storage / Suspicious Files / Bugs"),
        ("[5]","Website Security Audit"),
        ("[0]","Exit")]:
        t.add_row(a,b)
    console.print(t)

def main():
    while True:
        header(); menu()
        try:
            c = Prompt.ask("[bold green]blacktiger@local[/bold green]")
            if c == "1": system_info_page(console)
            elif c == "2": camera_portal_page(console)
            elif c == "3": ai_security_page(console)
            elif c == "4": security_health_page(console)
            elif c == "5": web_audit_page(console)
            elif c == "0": return
            else: console.print("[red]Invalid option[/red]")
        except EOFError:
            console.print("\n[yellow]Input closed; BlackTiger exited.[/yellow]")
            return
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Ctrl+C -> BlackTiger closed.[/bold yellow]")
            return

if __name__ == "__main__":
    main()
