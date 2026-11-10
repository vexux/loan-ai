import sys
import time
import asyncio
import itertools


class Spinner:
    """Animated Braille spinner with elapsed-time ticker for asyncio."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str):
        self.message = message
        self._running = False
        self._task = None
        self._start_time = 0.0

    async def _spin(self):
        cycler = itertools.cycle(self.FRAMES)
        self._start_time = time.perf_counter()
        while self._running:
            frame = next(cycler)
            elapsed = time.perf_counter() - self._start_time
            # \033[2K clears the entire line so it doesn't wrap/stack in Windows
            sys.stdout.write(f"\033[2K\r  {frame} {self.message} \033[90m({elapsed:.1f}s)\033[0m")
            sys.stdout.flush()
            await asyncio.sleep(0.08)

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._spin())

    async def stop(self, success: bool = True, custom_text: str = ""):
        self._running = False
        if self._task:
            await self._task
        elapsed = time.perf_counter() - self._start_time
        sys.stdout.write("\033[2K\r")
        icon = "✔" if success else "✖"
        text = custom_text or self.message
        sys.stdout.write(f"  {icon} {text} \033[90m({elapsed:.1f}s)\033[0m\n")
        sys.stdout.flush()



def print_banner():
    """Prints a clean, monochrome application banner."""
    print("\n╭──────────────────────────────────────────────────────────────────╮")
    print("│                   🏦 ENTERPRISE AI ASSISTANT                     │")
    print("│       \033[90mAutonomous SLM Agent Architecture with RBAC & Memory\033[0m       │")
    print("├──────────────────────────────────────────────────────────────────┤")
    print("│  RBAC Commands:  /login <customer_id|admin>  |  /logout | /whoami│")
    print("│  Session:        /clear (resets memory)      |  exit / quit      │")
    print("╰──────────────────────────────────────────────────────────────────╯\n")


def print_card(title: str, content: str, is_error: bool = False):
    width = 68
    title_bar = f" {title} "
    fill_right = "─" * max(2, width - len(title_bar) - 6)
    print(f"\n╭────{title_bar}{fill_right}╮")
    for line in content.strip().splitlines():
        print(f"  {line}")
    print(f"╰{'─' * (width - 2)}╯\n")


def print_observability(trace_id: str, duration: str, status: str, trace_file: str = ""):
    is_ok = status.upper() == "SUCCESS"
    status_str = "✔ SUCCESS" if is_ok else "✖ FAILED"
    width = 68
    title_bar = " 📊 OBSERVABILITY "
    fill_right = "─" * max(2, width - len(title_bar) - 6)
    print(f"╭────{title_bar}{fill_right}╮")
    print(f"  Status:     {status_str}")
    print(f"  Trace ID:   {trace_id}")
    print(f"  Duration:   {duration}")
    if trace_file:
        print(f"  Audit Log:  \033[90m{trace_file}\033[0m")
    print(f"╰{'─' * (width - 2)}╯\n")
