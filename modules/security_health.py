import hashlib
import math
import os
import shutil
import stat
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import psutil
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

RISK_EXTS = {'.exe','.dll','.scr','.bat','.cmd','.ps1','.vbs','.js','.jar','.apk','.elf','.bin','.com','.msi'}
ARCHIVE_EXTS = {'.zip','.rar','.7z','.tar','.gz','.bz2','.xz'}
WORDS = {'keylogger','stealer','rat','ransom','payload','backdoor','miner','crypt','inject','shell','exploit'}
MAX_HASH_BYTES = 512 * 1024 * 1024


def gb(n):
    return f"{n/(1024**3):.2f} GB"


def sha256_file(path: Path):
    try:
        if path.stat().st_size > MAX_HASH_BYTES:
            return 'skipped (>512 MB)'
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f'error: {e}'


def entropy_sample(path: Path):
    try:
        with path.open('rb') as f:
            data = f.read(256 * 1024)
        if not data:
            return 0.0
        counts = Counter(data)
        total = len(data)
        return -sum((c/total) * math.log2(c/total) for c in counts.values())
    except Exception:
        return 0.0


def indicators(path: Path):
    reasons = []
    low = path.name.lower()
    ext = path.suffix.lower()
    try:
        mode = path.stat().st_mode
        size = path.stat().st_size
    except Exception:
        return ['unreadable metadata']

    if ext in RISK_EXTS:
        reasons.append('executable/script file type')
    if ext in ARCHIVE_EXTS:
        reasons.append('archive; inspect contents before opening')
    if any(w in low for w in WORDS):
        reasons.append('security-risk keyword in filename')
    if low.startswith('.') and ext in RISK_EXTS:
        reasons.append('hidden executable/script')
    if os.name != 'nt' and (mode & stat.S_IXUSR) and ext not in {'.sh','.py'}:
        reasons.append('executable permission set')
    ent = entropy_sample(path)
    if size > 4096 and ent >= 7.75 and ext in RISK_EXTS:
        reasons.append(f'high entropy ({ent:.2f})')
    return reasons


def clamav_scan(root: Path):
    scanner = shutil.which('clamscan')
    if not scanner:
        return None, 'ClamAV not installed; heuristic scan only.'
    try:
        r = subprocess.run(
            [scanner, '-r', '--infected', '--no-summary', str(root)],
            capture_output=True, text=True, timeout=600
        )
        infected = []
        for line in (r.stdout or '').splitlines():
            if line.endswith(' FOUND'):
                infected.append(line[:-6])
        return infected, f'ClamAV completed with {len(infected)} detection(s).'
    except Exception as e:
        return [], f'ClamAV error: {e}'


def deep_scan(root: Path, console):
    hits = []
    scanned = 0
    errors = 0
    for p in root.rglob('*'):
        try:
            if not p.is_file():
                continue
            if any(part in {'.git','.venv','node_modules','__pycache__'} for part in p.parts):
                continue
            scanned += 1
            rs = indicators(p)
            if rs:
                hits.append({
                    'path': p,
                    'reason': '; '.join(rs),
                    'size': p.stat().st_size,
                    'sha256': sha256_file(p),
                })
        except (PermissionError, OSError):
            errors += 1
        if scanned % 250 == 0:
            console.print(f"[dim green]Scanned {scanned} files...[/dim green]")
    return scanned, errors, hits


def quarantine_or_delete(console, root: Path, hits):
    if not hits:
        return
    console.print('\n[yellow]Indicators are not proof of malware. Review paths/hashes before any action.[/yellow]')
    if not Confirm.ask('Do you want file actions for the flagged items?', default=False):
        return

    quarantine = root / '.blacktiger_quarantine'
    quarantine.mkdir(exist_ok=True)
    for i, item in enumerate(hits, 1):
        p = item['path']
        if not p.exists():
            continue
        console.print(f"\n[bold]{i}. {p}[/bold]\nReason: {item['reason']}\nSHA256: {item['sha256']}")
        action = Prompt.ask('Action', choices=['skip','quarantine','delete'], default='skip')
        if action == 'quarantine':
            try:
                dest = quarantine / f"{int(time.time())}_{p.name}"
                shutil.move(str(p), str(dest))
                console.print(f"[green]Moved to quarantine: {dest}[/green]")
            except Exception as e:
                console.print(f"[red]Quarantine failed: {e}[/red]")
        elif action == 'delete':
            if Confirm.ask(f'Permanently delete {p}?', default=False):
                try:
                    p.unlink()
                    console.print('[green]Deleted after confirmation.[/green]')
                except Exception as e:
                    console.print(f"[red]Delete failed: {e}[/red]")


def storage_table(console):
    st = Table(title='Storage / Mount Health', border_style='green')
    for x in ['Mount','Total','Used','Free','Used %']:
        st.add_column(x)
    seen = set()
    for part in psutil.disk_partitions(all=False):
        if part.mountpoint in seen:
            continue
        seen.add(part.mountpoint)
        try:
            u = shutil.disk_usage(part.mountpoint)
            pct = (u.used/u.total*100) if u.total else 0
            st.add_row(part.mountpoint, gb(u.total), gb(u.used), gb(u.free), f'{pct:.1f}%')
        except Exception:
            pass
    console.print(st)


def python_bug_check(console, root: Path):
    bt = Table(title='Python Project Bug / Syntax Check', border_style='green')
    bt.add_column('Status'); bt.add_column('Details')
    ok = 0; errs = []
    for p in root.rglob('*.py'):
        if any(part in {'.venv','__pycache__'} for part in p.parts):
            continue
        try:
            r = subprocess.run([sys.executable,'-m','py_compile',str(p)],capture_output=True,text=True,timeout=15)
            if r.returncode == 0:
                ok += 1
            else:
                errs.append((str(p.relative_to(root)),(r.stderr or r.stdout).strip()[-300:]))
        except Exception as e:
            errs.append((str(p), str(e)))
    bt.add_row('PASS', f'{ok} Python files compile successfully')
    for f,e in errs[:25]:
        bt.add_row('ERROR', f'{f}: {e}')
    console.print(bt)


def security_health_page(console):
    console.clear()
    console.print(Panel.fit(
        '[bold green]BLACKTIGER DEEP LOCAL SECURITY HEALTH[/bold green]\n'
        '[green]Storage • recursive file indicators • SHA-256 • optional ClamAV • syntax checks[/green]\n'
        '[yellow]No automatic deletion: flagged files can only be quarantined/deleted after your confirmation.[/yellow]',
        border_style='green'))
    storage_table(console)

    raw = Prompt.ask('\n[bold green]Folder to scan[/bold green]', default=str(Path.cwd()))
    root = Path(raw).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        console.print('[red]Folder not found.[/red]')
        Prompt.ask('Press Enter to return', default='')
        return

    console.print(f'[dim green]Deep scanning: {root}[/dim green]')
    scanned, errors, hits = deep_scan(root, console)

    ft = Table(title=f'Deep Scan — {scanned} files checked', border_style='green')
    ft.add_column('#', justify='right'); ft.add_column('File'); ft.add_column('Reason'); ft.add_column('SHA-256')
    if not hits:
        ft.add_row('-', 'None flagged', 'No heuristic indicators found', '-')
    else:
        for i,item in enumerate(hits[:100], 1):
            try: rel = str(item['path'].relative_to(root))
            except Exception: rel = str(item['path'])
            ft.add_row(str(i), rel, item['reason'], item['sha256'][:18] + '…' if len(item['sha256']) > 20 else item['sha256'])
    console.print(ft)
    console.print(f'[dim]Unreadable/error entries: {errors}[/dim]')

    infected, clam_msg = clamav_scan(root)
    console.print(f'[green]{clam_msg}[/green]' if infected is not None else f'[yellow]{clam_msg}[/yellow]')
    if infected:
        for x in infected[:50]:
            console.print(f'[red]CLAMAV: {x}[/red]')

    python_bug_check(console, root)
    quarantine_or_delete(console, root, hits)
    Prompt.ask('\nPress Enter to return', default='')
