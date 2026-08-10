from datetime import datetime

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
GRAY   = "\033[90m"


def color_priority(priority: str) -> str:
    p = priority.lower()
    if p == "critical":
        return f"{RED}{BOLD}{priority}{RESET}"
    if p == "high":
        return f"{RED}{priority}{RESET}"
    if p == "medium":
        return f"{YELLOW}{priority}{RESET}"
    return f"{GRAY}{priority}{RESET}"


def section(title: str) -> str:
    bar = "─" * (len(title) + 4)
    return f"\n{CYAN}{BOLD}┌{bar}┐\n│  {title}  │\n└{bar}┘{RESET}\n"


def timestamp() -> str:
    return datetime.now().strftime("%I:%M %p")
