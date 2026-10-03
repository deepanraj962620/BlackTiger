import os
from pathlib import Path
from dotenv import load_dotenv
from rich.panel import Panel
from rich.prompt import Prompt

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)

SYSTEM = """
You are BlackTiger AI by Deepanraj C. You are a continuous terminal assistant for Kali/Linux,
programming and defensive cybersecurity. You may generate normal programming projects such as games,
automation, utilities and local-device tools. For security topics, focus on systems the user owns or
has explicit authorization to test. Do not generate credential theft, malware, ransomware, hidden
camera access, phishing credential collection, stealth persistence, unauthorized access, destructive
denial of service, or code intended to compromise another person's system. For unsafe requests,
offer a safe lab or defensive equivalent. Prefer complete Python/Bash examples and practical run instructions.
"""

def ai_security_page(console):
    console.clear()
    console.print(Panel.fit(
        "[bold green]BLACKTIGER AI TERMINAL[/bold green]\n"
        "[green]Continuous chat + code generation[/green]\n"
        "[dim green]Ctrl+C returns • /clear resets chat[/dim green]",
        border_style="green"))

    key = os.getenv("GROQ_API_KEY")
    if not key or key == "PASTE_YOUR_NEW_GROQ_API_KEY_HERE":
        console.print("[yellow]Set your Groq API key in .env before using Option 3.[/yellow]")
        return

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    try:
        from groq import Groq
        client = Groq(api_key=key)
    except Exception as e:
        console.print(Panel(f"Could not initialize the Groq client: {e}", border_style="red"))
        return
    history = [{"role": "system", "content": SYSTEM}]
    console.print(f"[dim green]Model: {model}[/dim green]")

    while True:
        try:
            q = Prompt.ask("\n[bold green]you@blacktiger[/bold green]").strip()
            if not q:
                continue
            if q.lower() == "/clear":
                history = [history[0]]
                console.print("[yellow]Conversation cleared.[/yellow]")
                continue
            request_history = history + [{"role": "user", "content": q}]
            r = client.chat.completions.create(
                model=model, messages=request_history, temperature=0.25
            )
            ans = r.choices[0].message.content or ""
            history.extend(
                [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]
            )
            if len(history) > 31:
                history = [history[0]] + history[-30:]
            console.print(Panel(ans, title="BlackTiger AI", border_style="green"))
        except KeyboardInterrupt:
            return
        except Exception as e:
            console.print(Panel(
                f"AI error: {e}\nCurrent model: {model}\n"
                "Set GROQ_MODEL in .env to a model available to your Groq account.",
                border_style="red"))
