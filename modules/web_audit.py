import json
import socket
import ssl
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

COMMON_PORTS = {
    21:'FTP',22:'SSH',25:'SMTP',53:'DNS',80:'HTTP',110:'POP3',143:'IMAP',
    443:'HTTPS',465:'SMTPS',587:'SMTP Submission',993:'IMAPS',995:'POP3S',
    3306:'MySQL',5432:'PostgreSQL',6379:'Redis',8080:'HTTP Alt',8443:'HTTPS Alt'
}
SECURITY_HEADERS = [
    'content-security-policy','strict-transport-security','x-content-type-options',
    'x-frame-options','referrer-policy','permissions-policy','cross-origin-opener-policy'
]


def normalize_url(url):
    url = url.strip()
    p = urllib.parse.urlparse(url)
    if p.scheme.lower() not in {'http', 'https'}:
        if '://' in url:
            raise ValueError('URL must use HTTP or HTTPS.')
        url = 'https://' + url
        p = urllib.parse.urlparse(url)
    if not p.hostname:
        raise ValueError('Invalid URL/hostname.')
    if p.username or p.password:
        raise ValueError('URLs containing embedded credentials are not supported.')
    return p.geturl()


def resolve_host(host):
    rows = []
    for _, _, _, _, sockaddr in socket.getaddrinfo(host, None):
        ip = sockaddr[0]
        if ip not in rows:
            rows.append(ip)
    return rows


def scan_ports(host, timeout=0.45):
    results = []
    for port, service in COMMON_PORTS.items():
        try:
            with socket.create_connection((host, port), timeout=timeout):
                results.append({'port':port,'service':service,'state':'open'})
        except Exception:
            pass
    return results


def tls_metadata(host, port=443):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=8) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as ss:
            cert = ss.getpeercert()
            return {
                'version': ss.version(),
                'cipher': ss.cipher()[0] if ss.cipher() else None,
                'issuer': dict(x[0] for x in cert.get('issuer', [])),
                'subject': dict(x[0] for x in cert.get('subject', [])),
                'notBefore': cert.get('notBefore'),
                'notAfter': cert.get('notAfter'),
                'san_count': len(cert.get('subjectAltName', [])),
            }


def audit(url):
    url = normalize_url(url)
    p0 = urllib.parse.urlparse(url)
    host = p0.hostname
    ips = resolve_host(host)

    r = requests.get(url, timeout=12, allow_redirects=True, headers={'User-Agent':'BlackTiger-Authorized-Audit/5.1'})
    h = {k.lower():v for k,v in r.headers.items()}
    p = urllib.parse.urlparse(r.url)

    out = {
        'requested_url': url,
        'final_url': r.url,
        'hostname': p.hostname or host,
        'resolved_ips': ips,
        'http_status': r.status_code,
        'server': h.get('server','not disclosed'),
        'content_type': h.get('content-type','not disclosed'),
        'content_length': h.get('content-length','not disclosed'),
        'redirect_count': len(r.history),
        'headers': {x: ('present' if x in h else 'missing') for x in SECURITY_HEADERS},
        'ports': [],
        'tls': None,
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
    }

    # Small common-port inventory only; no exploit attempts or service brute forcing.
    scan_host = ips[0] if ips else out['hostname']
    out['ports'] = scan_ports(scan_host)
    if p.scheme == 'https':
        try:
            out['tls'] = tls_metadata(out['hostname'], p.port or 443)
        except Exception as e:
            out['tls'] = {'error': str(e)}
    return out


def web_audit_page(console):
    console.clear()
    console.print(Panel.fit(
        '[bold green]WEBSITE SECURITY AUDIT / SURFACE INVENTORY[/bold green]\n'
        '[green]IP • DNS • HTTP metadata • security headers • TLS • common open ports • JSON report[/green]\n'
        '[yellow]Use only on websites/systems you own or have explicit permission to assess.[/yellow]',
        border_style='green'))

    if not Confirm.ask('I confirm I own the target or have authorization to audit it', default=False):
        console.print('[yellow]Audit cancelled.[/yellow]')
        Prompt.ask('Press Enter to return', default='')
        return

    while True:
        try:
            target = Prompt.ask('\n[bold green]website@blacktiger[/bold green]')
            data = audit(target)
            t = Table(title='Website Surface Report', border_style='green')
            t.add_column('Field'); t.add_column('Result')
            t.add_row('HTTP Status', str(data['http_status']))
            t.add_row('Final URL', data['final_url'])
            t.add_row('Hostname', data['hostname'])
            t.add_row('IP Address(es)', ', '.join(data['resolved_ips']) or 'unresolved')
            t.add_row('Server', data['server'])
            t.add_row('Content-Type', data['content_type'])
            t.add_row('Redirects', str(data['redirect_count']))
            if data['tls']:
                if 'error' in data['tls']:
                    t.add_row('TLS', 'error: ' + data['tls']['error'])
                else:
                    t.add_row('TLS', f"{data['tls']['version']} / {data['tls']['cipher']}")
                    t.add_row('TLS Expiry', str(data['tls']['notAfter']))
            for name, state in data['headers'].items():
                t.add_row('Header: ' + name, state)
            console.print(t)

            pt = Table(title='Common Port Inventory', border_style='green')
            pt.add_column('Port'); pt.add_column('Service'); pt.add_column('State')
            if data['ports']:
                for x in data['ports']:
                    pt.add_row(str(x['port']), x['service'], x['state'])
            else:
                pt.add_row('-', '-', 'No common ports responded')
            console.print(pt)

            out = Path('reports'); out.mkdir(exist_ok=True)
            f = out / datetime.now().strftime('web_audit_%Y%m%d_%H%M%S.json')
            f.write_text(json.dumps(data, indent=2), encoding='utf-8')
            console.print(f'[dim green]Saved report: {f}[/dim green]')

            if not Confirm.ask('Audit another authorized website?', default=False):
                return
        except KeyboardInterrupt:
            return
        except Exception as e:
            console.print(f'[red]Audit error: {e}[/red]')
            if not Confirm.ask('Try another target?', default=True):
                return
