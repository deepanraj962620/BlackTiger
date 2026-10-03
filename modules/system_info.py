import os, platform, socket, psutil, json, time
from pathlib import Path
from datetime import datetime
from rich.panel import Panel
from rich.table import Table

def get_data():
    vm = psutil.virtual_memory()
    d = psutil.disk_usage('/')
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = 'Unknown'
    return {
        'Hostname': socket.gethostname(),
        'User': os.getenv('USER') or os.getenv('USERNAME') or 'Unknown',
        'OS': platform.system(),
        'Platform': platform.platform(),
        'Kernel': platform.release(),
        'Architecture': platform.machine(),
        'CPU': platform.processor() or 'Unknown',
        'CPU Cores': psutil.cpu_count(logical=True),
        'RAM Total': f'{vm.total/(1024**3):.2f} GB',
        'RAM Used': f'{vm.used/(1024**3):.2f} GB',
        'RAM Available': f'{vm.available/(1024**3):.2f} GB',
        'Disk Total': f'{d.total/(1024**3):.2f} GB',
        'Disk Used': f'{d.used/(1024**3):.2f} GB',
        'Disk Free': f'{d.free/(1024**3):.2f} GB',
        'Local IP': ip,
        'Python': platform.python_version(),
    }

def system_info_page(console):
    try:
        while True:
            console.clear()
            console.print(Panel.fit(
                '[bold green]SYSTEM INFORMATION[/bold green]\n'
                '[dim green]Live local diagnostics • Ctrl+C to return[/dim green]',
                border_style='green'))
            data = get_data()
            t = Table(border_style='green')
            t.add_column('Field', style='bold green')
            t.add_column('Value', style='green')
            for k, v in data.items():
                t.add_row(k, str(v))
            console.print(t)
            p = Path('reports')
            p.mkdir(exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            (p / f'system_info_{ts}.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
            console.print('[dim green]Auto-saved JSON report in reports/[/dim green]')
            time.sleep(5)
    except KeyboardInterrupt:
        return
