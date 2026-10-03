import re
import queue
import os
import ipaddress
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests
import urllib3
from rich.panel import Panel
from rich.prompt import Prompt

_server_thread = None
_server_port = None
_server_error = None
_tunnel_process = None


def _run(port):
    global _server_error
    from live_camera_server import app, socketio
    try:
        socketio.run(
            app,
            host='127.0.0.1',
            port=port,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True,
        )
    except Exception as e:
        _server_error = e


def _find_available_port():
    for port in range(8090, 8191):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
            return port
        except OSError:
            continue
    raise RuntimeError('No available port found between 8090 and 8190.')


def _wait_for_server(port, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _server_error is not None:
            raise RuntimeError(f'Could not start camera server: {_server_error}')
        if _server_thread is not None and not _server_thread.is_alive():
            raise RuntimeError('Camera server stopped before it became ready.')
        try:
            if requests.get(f'http://127.0.0.1:{port}/health', timeout=1).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(.25)
    raise RuntimeError('Camera server did not become ready.')


def _public_base_url(value):
    parsed = urlsplit(value.strip())
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('Enter a clean HTTPS tunnel base URL, e.g. https://example.trycloudflare.com')
    return f'https://{parsed.netloc}'


def _resolve_tunnel_addresses(hostname):
    addresses = []
    for record_type in ('A', 'AAAA'):
        response = requests.get(
            'https://cloudflare-dns.com/dns-query',
            params={'name': hostname, 'type': record_type},
            headers={'accept': 'application/dns-json'},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('Status') != 0:
            continue
        expected_version = 4 if record_type == 'A' else 6
        for answer in payload.get('Answer', []):
            if answer.get('type') != (1 if expected_version == 4 else 28):
                continue
            try:
                address = ipaddress.ip_address(answer.get('data', ''))
            except ValueError:
                continue
            if address.version == expected_version and str(address) not in addresses:
                addresses.append(str(address))
    return addresses


def _get_tunnel_health(base_url):
    try:
        return requests.get(f'{base_url}/health', timeout=3)
    except requests.RequestException as error:
        error_text = str(error).lower()
        if not any(
            marker in error_text
            for marker in ('nameresolutionerror', 'failed to resolve', 'getaddrinfo failed')
        ):
            raise

        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        if hostname is None:
            raise
        addresses = _resolve_tunnel_addresses(hostname)
        if not addresses:
            raise RuntimeError(
                f'DNS-over-HTTPS returned no addresses for {hostname}.'
            ) from error

        last_error = error
        port = parsed.port or 443
        host_header = parsed.netloc
        for address in addresses:
            pool = urllib3.HTTPSConnectionPool(
                host=address,
                port=port,
                server_hostname=hostname,
                assert_hostname=hostname,
                timeout=urllib3.Timeout(connect=3, read=3),
                maxsize=1,
            )
            try:
                response = pool.request(
                    'GET',
                    '/health',
                    headers={'Host': host_header},
                    retries=False,
                )
                if response.status == 200:
                    return response
                last_error = RuntimeError(
                    f'Tunnel endpoint returned HTTP {response.status}.'
                )
            except (urllib3.exceptions.HTTPError, OSError) as fallback_error:
                last_error = fallback_error
            finally:
                pool.close()
        raise RuntimeError(
            f'Windows DNS could not resolve {hostname}, and the direct HTTPS '
            f'health check failed: {last_error}'
        ) from error


def _verify_public_base_url(base_url, timeout=60):
    deadline = time.monotonic() + timeout
    last_error = 'tunnel health endpoint did not return a successful response'
    while time.monotonic() < deadline:
        try:
            response = _get_tunnel_health(base_url)
            if hasattr(response, 'raise_for_status'):
                response.raise_for_status()
                payload = response.json()
            else:
                if response.status != 200:
                    raise RuntimeError(
                        f'Tunnel endpoint returned HTTP {response.status}.'
                    )
                payload = json.loads(response.data)
            if isinstance(payload, dict) and payload.get('ok') is True:
                return
            last_error = 'tunnel returned an unexpected health response'
        except (requests.RequestException, urllib3.exceptions.HTTPError, OSError, RuntimeError, ValueError) as e:
            last_error = str(e)
        time.sleep(.5)
    if any(
        marker in last_error.lower()
        for marker in (
            'nameresolutionerror',
            'failed to resolve',
            'getaddrinfo failed',
            'could not resolve',
        )
    ):
        return_hint = (
            'The HTTPS tunnel name could not be resolved by DNS. Check that this PC '
            'has internet access and working DNS, then try Option 2 again. '
            'On Windows, you can test DNS with '
            '`Resolve-DnsName <tunnel-hostname>`.'
        )
    else:
        return_hint = (
            'Check that cloudflared is still running and the tunnel URL is correct, '
            'then try Option 2 again.'
        )
    raise RuntimeError(
        f'Could not reach the BlackTiger server through this HTTPS URL. '
        f'{return_hint} Last check: {last_error}'
    )


def _stop_tunnel():
    global _tunnel_process
    process = _tunnel_process
    _tunnel_process = None
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        if process.poll() is not None:
            return
        raise
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def _find_cloudflared():
    exe = shutil.which('cloudflared')
    if exe:
        return exe

    install_dirs = [
        Path(value)
        for value in (
            os.environ.get('ProgramFiles'),
            os.environ.get('ProgramFiles(x86)'),
            os.environ.get('LOCALAPPDATA'),
        )
        if value
    ]
    candidates = [directory / 'cloudflared' / 'cloudflared.exe' for directory in install_dirs]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _auto_cloudflare(port, console):
    global _tunnel_process
    exe = _find_cloudflared()
    if not exe:
        return None
    console.print('[dim green]cloudflared detected — creating a public HTTPS Quick Tunnel...[/dim green]')
    _tunnel_process = subprocess.Popen(
        [exe, 'tunnel', '--url', f'http://127.0.0.1:{port}', '--no-autoupdate'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
    )
    pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
    deadline = time.monotonic() + 25
    output = queue.Queue()
    recent_lines = []

    def read_output():
        if _tunnel_process is None or _tunnel_process.stdout is None:
            output.put(None)
            return
        for line in _tunnel_process.stdout:
            output.put(line.rstrip())
        output.put(None)

    threading.Thread(target=read_output, daemon=True).start()
    while time.monotonic() < deadline:
        process = _tunnel_process
        if process is None or process.poll() is not None:
            break
        try:
            line = output.get(timeout=min(.25, deadline - time.monotonic()))
        except queue.Empty:
            continue
        if line is None:
            break
        recent_lines.append(line)
        match = pattern.search(line)
        if match:
            return match.group(0)

    if recent_lines:
        console.print('[yellow]cloudflared output:[/yellow]')
        for line in recent_lines[-5:]:
            console.print(f'[dim]{line}[/dim]')
    _stop_tunnel()
    return None


def camera_portal_page(console):
    global _server_thread, _server_port, _server_error
    console.clear()
    console.print(Panel.fit(
        '[bold green]PROFESSIONAL CAMERA SHARE LINK[/bold green]\n'
        '[green]Birthday • Festival • Marriage themed landing page -> NEXT -> explicit camera consent[/green]\n'
        '[yellow]Camera access never starts silently; the phone user must approve browser permission.[/yellow]',
        border_style='green'))

    console.print('[green][1][/green] Birthday')
    console.print('[green][2][/green] Festival')
    console.print('[green][3][/green] Marriage')
    choice = Prompt.ask('[bold green]Choose theme[/bold green]', choices=['1','2','3'], default='2')
    theme = {'1':'birthday','2':'festival','3':'marriage'}[choice]
    title = Prompt.ask('[green]Page title[/green]', default={'birthday':'Birthday Surprise','festival':'Festival Wishes','marriage':'Wedding Memories'}[theme])

    if _server_thread is None or not _server_thread.is_alive():
        try:
            _server_port = _find_available_port()
        except RuntimeError as e:
            console.print(f'[red]{e}[/red]'); return
        _server_error = None
        _server_thread = threading.Thread(target=_run, args=(_server_port,), daemon=True)
        _server_thread.start()

    try:
        _wait_for_server(_server_port)
        base_url = _auto_cloudflare(_server_port, console)
        if not base_url:
            console.print(
                '\n[yellow]A public phone link needs cloudflared and an HTTPS tunnel.[/yellow]'
            )
            console.print(
                '[bold]Run in another terminal: cloudflared tunnel --url '
                f'http://127.0.0.1:{_server_port}[/bold]'
            )
            console.print(
                '[dim]For a same-computer test, enter LOCAL. Phone cameras need HTTPS; '
                'plain LAN HTTP links cannot request camera permission.[/dim]'
            )
            tunnel_url = Prompt.ask(
                '[green]Paste the tunnel HTTPS URL, enter LOCAL, or leave blank to cancel[/green]'
            ).strip()
            if not tunnel_url:
                return
            if tunnel_url.upper() == 'LOCAL':
                base_url = f'http://127.0.0.1:{_server_port}'
            else:
                base_url = _public_base_url(tunnel_url)
                _verify_public_base_url(base_url)
        else:
            _verify_public_base_url(base_url)

        r = requests.post(f'http://127.0.0.1:{_server_port}/api/session', json={'theme':theme,'title':title}, timeout=5)
        r.raise_for_status(); sid = r.json()['session_id']
    except (OSError, requests.RequestException, RuntimeError, ValueError) as e:
        _stop_tunnel()
        console.print(f'[red]Live-share setup failed: {e}[/red]'); return

    share = f'{base_url}/share/{sid}'
    viewer = f'http://127.0.0.1:{_server_port}/viewer/{sid}'
    console.print(Panel(
        f'[bold green]PUBLIC PHONE WEBSITE[/bold green]\n{share}\n\n'
        f'[bold green]LOCAL PC LIVE VIEWER[/bold green]\n{viewer}\n\n'
        '[yellow]Phone flow:[/yellow]\n'
        f'1. Opens the {theme.title()} page using your supplied design image\n'
        '2. Taps NEXT\n3. Reads the camera-sharing notice\n4. Ticks consent\n'
        '5. Taps ALLOW CAMERA & START LIVE SHARE\n6. Browser asks for camera permission\n'
        '7. A visible LIVE indicator remains until STOP is tapped', border_style='green'))
    console.print('[dim]Keep BlackTiger and the tunnel running. Ctrl+C returns to the main menu.[/dim]')
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        _stop_tunnel()
        return
