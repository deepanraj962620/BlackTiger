from pathlib import Path
from rich.panel import Panel
from rich.prompt import Prompt
def page(console):
    console.clear(); console.print(Panel.fit("[bold green]REPORT CENTER[/bold green]",border_style="green"))
    p=Path("reports"); p.mkdir(exist_ok=True)
    items=sorted(p.iterdir(),key=lambda x:x.stat().st_mtime,reverse=True)
    for i,x in enumerate(items[:50],1): console.print(f"[green]{i:02}[/green] {x}")
    if not items: console.print("[yellow]No reports yet.[/yellow]")
    Prompt.ask("[dim]Press Enter[/dim]",default="")
