import subprocess
import sys
import re

def _parse_man_page(man_page_text):
    name_match = re.search(r'NAME\n\s*(.*)', man_page_text)
    description_match = re.search(r'DESCRIPTION\n\s*(.*)', man_page_text)

    summary = ""
    if name_match:
        summary += name_match.group(1).strip()
    if description_match:
        summary += "\n\n" + description_match.group(1).strip()

    return summary if summary else man_page_text

def _parse_help_output(help_text):
    # A simple approach to summarize --help output is to take the first few lines
    return "\n".join(help_text.splitlines()[:10])

def get_command_help(command):
    if sys.platform != "linux":
        return "This tool is designed for Linux. Cannot fetch command help on other platforms."

    # Check if command exists
    try:
        subprocess.run(["which", command], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return f"Command not found: {command}"

    # Try `--help` first, as it's more universally available than `man`
    try:
        result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return _parse_help_output(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass # Fall through to man if --help fails

    if sys.platform == "linux":
        try:
            # Try to get help from `man`
            result = subprocess.run(["man", command], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return _parse_man_page(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return f"Could not find help for command: {command}"


def _extract_summary(help_text: str) -> str:
    lines = [line.strip() for line in help_text.splitlines() if line.strip()]
    if not lines:
        return ""
    # Prefer NAME or the first non-usage line
    for i, line in enumerate(lines[:8]):
        if not line.lower().startswith(("usage", "synopsis")):
            return line
    return lines[0]


def _extract_flags(help_text: str) -> dict:
    """Heuristically extract flags and their descriptions from help/man text.

    Returns a dict mapping flag (e.g., "-a", "--all") to a short description.
    """
    flags: dict[str, str] = {}
    for raw_line in help_text.splitlines():
        line = raw_line.rstrip()
        # Match lines that start with whitespace then a dash flag pattern
        # Examples:
        #   -a, --all               show all
        #       --color[=WHEN]      colorize output
        #   -l                      use a long listing format
        m = re.match(r"^\s*(?:([\-]{1,2}[A-Za-z0-9][^,\s]*)\s*,\s*)?([\-]{1,2}[A-Za-z0-9][^\s]*)\s+(.*)$", line)
        if m:
            flag1, flag2, desc = m.groups()
            desc = desc.strip()
            # Stop overly long descriptions; keep concise first clause
            desc = re.split(r"\s{2,}|\.$", desc)[0].strip() or desc
            for f in (flag1, flag2):
                if f:
                    # Normalize flags like "--color[=WHEN]" to "--color"
                    normalized = re.sub(r"\[.*?\]|=.+", "", f)
                    flags.setdefault(normalized, desc)
        else:
            # Also match simple single-flag lines like: "  -a    list all"
            m2 = re.match(r"^\s*([\-]{1,2}[A-Za-z0-9])\s{2,}(.*)$", line)
            if m2:
                f, desc = m2.groups()
                desc = desc.strip()
                desc = re.split(r"\s{2,}|\.$", desc)[0].strip() or desc
                flags.setdefault(f, desc)
    return flags


def _get_full_help_text(command: str) -> str:
    """Fetch full help/man text for a command without truncation.

    Tries `command --help` first (uses stdout or stderr regardless of exit code),
    then falls back to `man`.
    """
    if sys.platform != "linux":
        return "This tool is designed for Linux. Cannot fetch command help on other platforms."

    # Check if command exists
    try:
        subprocess.run(["which", command], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return f"Command not found: {command}"

    # Try --help and consider both stdout and stderr, regardless of return code
    try:
        result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=5)
        text = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        text = text.strip()
        if text:
            return text
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback to man
    try:
        result = subprocess.run(["man", command], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return f"Could not find help for command: {command}"


def get_command_details(command: str) -> dict:
    """Return structured details for a command from --help or man.

    Structure: { 'summary': str, 'flags': { flag: description } }
    """
    help_text = _get_full_help_text(command)
    if help_text.startswith("Command not found:") or help_text.startswith("Could not find help"):
        return {"summary": help_text, "flags": {}}

    # Always attempt man for a better summary; also merge flags from both sources
    man_text = ""
    try:
        man_result = subprocess.run(["man", command], capture_output=True, text=True, timeout=5)
        if man_result.returncode == 0 and man_result.stdout:
            man_text = man_result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    summary = ""
    if man_text:
        summary_from_man = _parse_man_page(man_text)
        if summary_from_man:
            summary = summary_from_man.splitlines()[0]
    if not summary:
        summary = _extract_summary(help_text)

    flags = {}
    # Merge flags with help taking precedence, then man
    help_flags = _extract_flags(help_text)
    man_flags = _extract_flags(man_text) if man_text else {}
    flags.update(man_flags)
    flags.update(help_flags)

    return {"summary": summary or help_text.splitlines()[0], "flags": flags}
