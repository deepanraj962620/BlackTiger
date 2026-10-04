# BlackTiger v5.5 - Security Toolkit
Author: Deepanraj C

- Continuous AI chat until Ctrl+C; `/clear` resets chat.
- Browser camera sharing with explicit camera consent and optional recording consent.
- Storage/suspicious-file/syntax-check tables.
- Large BlackTiger banner and right-aligned metadata.
- Continuous website security audit for owned/authorized sites.

Install: `chmod +x install.sh run.sh && ./install.sh && ./run.sh`

Create `.env` from `.env.example`, then set your new Groq key and available model.

### Linux quick start
Install Python 3.11 or newer, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Then start the app with:

```bash
python main.py
```

If you are using shell scripts instead, run:

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

The app expects a valid Groq API key in `.env`; the sample value in `.env.example`
is intentionally a placeholder.

### Windows quick start
Install Python 3.11 or newer, then run `setup_windows.bat` once and `run_windows.bat`
to start the menu. Setup creates the virtual environment and copies `.env.example`
to `.env` if needed. The launcher selects that environment and enables UTF-8 output
for the banner. Option 3 also requires a valid Groq API key in `.env`; the example
value is intentionally a placeholder.

Camera note: browsers require localhost or HTTPS for camera access. A phone cannot
use its camera from a plain HTTP link to your PC's LAN address.


## v4.1 Camera theme link generator
Option 2 can generate Birthday, Festival, or Marriage themed camera-consent pages.
The page does not hide camera use and does not start recording automatically.
The visitor must check consent, press ALLOW CAMERA, approve the browser permission,
and the live preview + recording indicator remain visible while recording.


## v4.2 Live camera sharing
Option 2 creates:
- a phone share link
- a PC live-viewer link

For phone access over the internet, install `cloudflared`, start BlackTiger and choose
Option 2, then run this command in a second terminal:

```bash
cloudflared tunnel --url http://127.0.0.1:<PORT>
```

Use the exact port displayed by BlackTiger in the tunnel command, then paste the
generated `https://...trycloudflare.com` URL into the app. It selects an available
port between 8090 and 8190. Use the resulting HTTPS URL for both the phone share
link and PC viewer link. Keep both BlackTiger and the tunnel running until sharing
ends. The tunnel URL changes when a new Quick Tunnel is started; generate fresh
links each time. Treat the share link as private and send it only to the intended
phone user.

Opening only the tunnel's base URL shows a usage page; it is not a share session.
Open the complete PHONE SHARE LINK or PC LIVE VIEWER link printed by Option 2.

Option 2 checks that the HTTPS tunnel reaches the BlackTiger health endpoint before
printing links. If `cloudflared` is not installed, enter `LOCAL` for a same-computer
test. A phone cannot use plain LAN HTTP for camera access, so phone sharing requires
the HTTPS tunnel.

On Windows, install the official `cloudflared` executable. Option 2 checks both
`PATH` and the standard Program Files install folders and starts/stops its Quick
Tunnel automatically when it finds the executable.

The phone page clearly says the camera is being streamed, requires a consent checkbox,
requires the user to press the camera button and approve the browser permission,
shows the local preview, displays a LIVE indicator, and includes a STOP button.

This version intentionally does not hide camera use or start the camera silently.

## v5.0 Professional theme + deep security update
- Option 2 uses the supplied Birthday, Festival, and Marriage images as real landing-page designs.
- Flow: themed page -> NEXT -> clear consent screen -> browser camera permission -> visible live stream.
- If `cloudflared` is installed, BlackTiger tries to create the public HTTPS link automatically; otherwise it prints the exact Quick Tunnel command and accepts the generated URL.
- Option 4 now supports a recursive folder scan, SHA-256 hashing, suspicious-extension/name/entropy indicators, optional ClamAV detection, storage health, and Python syntax checks.
- Flagged files are never silently deleted. You can review each item and explicitly choose skip, quarantine, or permanent delete.
- Option 5 now reports hostname, resolved IP addresses, HTTP status/redirects, server/content metadata, security headers, TLS details, and a limited common-port inventory. It requires an ownership/authorization confirmation and saves a JSON report.

### Optional tools
For automatic public camera links:
```bash
sudo apt install cloudflared
```
If your distro does not provide it through APT, install Cloudflare's official `cloudflared` package for your platform.

For antivirus-backed deep scanning in Option 4:
```bash
sudo apt install clamav
sudo freshclam
```
### kali linux install commands  ##

git clone https://github.com/deepanraj962620/BlackTigger.git

cd BlackTigger

chmod +x install.sh run.sh run_portal.sh

./install.sh

./run.sh

## v5.1 reliability updates
- Added Windows setup and launch scripts with UTF-8 terminal handling.
- Closed-input startup now exits cleanly instead of raising an EOF traceback.
- Option 3 does not add failed AI requests to the chat history.
- Option 5 accepts HTTP/HTTPS URLs regardless of scheme capitalization and handles IPv4/IPv6 port checks.
- The `.env.example` API key is a placeholder; configure a valid key to use Option 3.

## v5.2 Option 2 reliability updates
- Camera server binds only to loopback and reports background startup failures.
- Tunnel startup reads output without blocking its timeout and stops the tunnel when sharing ends.
- Phone and viewer pages display connection failures; camera access stays disabled until the server connection is ready.
- Disconnected phone sessions stop streaming, and server-side frame events require the joined share session.

## v5.3 tunnel connection diagnostics
- Waits up to 60 seconds for the HTTPS Quick Tunnel health check, allowing for temporary DNS/network startup delays.
- Reports DNS lookup failures with Windows troubleshooting steps instead of only printing the raw connection exception.

## v5.4 Windows tunnel DNS fallback
- If Windows DNS cannot resolve the temporary Quick Tunnel hostname, Option 2 resolves it through Cloudflare DNS-over-HTTPS and verifies HTTPS with the original hostname and certificate.
- The PC viewer link uses localhost on the same computer, avoiding dependence on Windows DNS for the local viewer.

## v5.5 consent-based live recording
- Phone users must separately consent to recording; camera sharing still works when recording consent is declined.
- The PC viewer's START RECORDING and STOP RECORDING buttons control an MP4 recording, with a visible recording indicator on both pages.
- Recordings are saved under `recordings/` and are finalized when recording stops, the phone stops sharing, or either side disconnects.
