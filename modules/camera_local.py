from pathlib import Path
from datetime import datetime
from rich.panel import Panel
from rich.prompt import Prompt,Confirm
def page(console):
    console.clear(); console.print(Panel.fit(
    "[bold green]CAMERA ACCESS / LOCAL RECORDER[/bold green]\n"
    "[green]Only the camera attached to this computer.[/green]\n"
    "[yellow]Explicit approval required.[/yellow]",border_style="green"))
    if not Confirm.ask("[green]Allow local camera recording?[/green]",default=False):
        return
    try: import cv2
    except: console.print("[red]OpenCV missing. Run ./install.sh[/red]"); Prompt.ask("[dim]Enter[/dim]",default=""); return
    try: mins=max(1,min(int(Prompt.ask("[green]Minutes 1-60[/green]",default="1")),60))
    except: mins=1
    cap=cv2.VideoCapture(0)
    if not cap.isOpened(): console.print("[red]Camera unavailable[/red]"); return
    out=Path("recordings"); out.mkdir(exist_ok=True)
    path=out/datetime.now().strftime("blacktiger_%Y%m%d_%H%M%S.avi")
    w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    fps=cap.get(cv2.CAP_PROP_FPS) or 20.0
    if fps<2: fps=20.0
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"XVID"),fps,(w,h))
    import time; end=time.time()+mins*60
    try:
        while time.time()<end:
            ok,frame=cap.read()
            if not ok: break
            writer.write(frame)
    except KeyboardInterrupt: pass
    writer.release(); cap.release()
    console.print(f"[bold green]Saved:[/bold green] {path}")
    Prompt.ask("[dim]Press Enter[/dim]",default="")
