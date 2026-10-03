import platform,socket,psutil,os,json
from pathlib import Path
from datetime import datetime
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
def collect():
    vm=psutil.virtual_memory(); d=psutil.disk_usage("/")
    return {"Hostname":socket.gethostname(),"User":os.getenv("USER") or "Unknown",
    "OS":platform.system(),"Platform":platform.platform(),"Kernel":platform.release(),
    "Architecture":platform.machine(),"CPU":platform.processor() or "Unknown",
    "CPU Cores":psutil.cpu_count(logical=True),"RAM Total":f"{vm.total/(1024**3):.2f} GB",
    "RAM Used":f"{vm.used/(1024**3):.2f} GB","Disk Total":f"{d.total/(1024**3):.2f} GB",
    "Disk Used":f"{d.used/(1024**3):.2f} GB","Local IP":socket.gethostbyname(socket.gethostname())}
def page(console):
    console.clear(); console.print(Panel.fit("[bold green]SYSTEM INFORMATION[/bold green]\n[green]This machine only[/green]",border_style="green"))
    data=collect(); t=Table(border_style="green"); t.add_column("Field"); t.add_column("Value")
    for k,v in data.items(): t.add_row(k,str(v))
    console.print(t)
    if Prompt.ask("[green]Save JSON/TXT report? (y/n)[/green]",default="y").lower()=="y":
        p=Path("reports"); p.mkdir(exist_ok=True); ts=datetime.now().strftime("%Y%m%d_%H%M%S")
        (p/f"system_{ts}.json").write_text(json.dumps(data,indent=2))
        (p/f"system_{ts}.txt").write_text("\n".join(f"{k}: {v}" for k,v in data.items()))
        console.print("[bold green]Report saved in reports/[/bold green]")
    console.print("\n[green]Consent portal:[/green] ./run_portal.sh")
    Prompt.ask("[dim]Press Enter[/dim]",default="")
