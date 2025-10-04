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
    lines = help_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or not line.strip():
            i += 1
            continue
            
        # Pattern 1: -a, --all               description (or description on next line)
        m1 = re.match(r"^\s*(?:([\-]{1,2}[A-Za-z0-9][^,\s]*)\s*,\s*)?([\-]{1,2}[A-Za-z0-9][^\s]*)(?:\s+(.*))?$", line)
        if m1:
            flag1, flag2, desc = m1.groups()
            desc = desc.strip() if desc else ""
            
            # Look for description on continuation lines (indented, no leading dash)
            j = i + 1
            while j < len(lines) and lines[j].startswith(" ") and not re.match(r"^\s*\-", lines[j]):
                cont_line = lines[j].strip()
                if cont_line and not cont_line.startswith("-"):
                    if desc:
                        desc += " " + cont_line
                    else:
                        desc = cont_line
                j += 1
            
            # Take first sentence, but allow longer descriptions
            if desc:
                desc = re.split(r"\s{2,}|\.$", desc)[0].strip() or desc
            
            # Handle both flags, cleaning up commas
            for f in (flag1, flag2):
                if f:
                    # Clean up trailing commas and normalize
                    clean_flag = f.rstrip(',').strip()
                    normalized = re.sub(r"\[.*?\]|=.+", "", clean_flag)
                    if desc:  # Only add if we have a description
                        flags[normalized] = desc  # Use direct assignment to ensure we get the description
            i = j
            continue
            
        # Pattern 2: -a    description (simple single flag)
        m2 = re.match(r"^\s*([\-]{1,2}[A-Za-z0-9])\s{2,}(.*)$", line)
        if m2:
            f, desc = m2.groups()
            desc = desc.strip()
            
            # Look for continuation lines
            j = i + 1
            while j < len(lines) and lines[j].startswith(" ") and not re.match(r"^\s*\-", lines[j]):
                cont_line = lines[j].strip()
                if cont_line and not cont_line.startswith("-"):
                    desc += " " + cont_line
                j += 1
            
            desc = re.split(r"\s{2,}|\.$", desc)[0].strip() or desc
            flags.setdefault(f, desc)
            i = j
            continue
            
        i += 1
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
    
    # Clean up any flags that have other flag names as values (like -T: --tcp)
    cleaned_flags = {}
    for flag, desc in flags.items():
        # If description looks like another flag (starts with -), try to find the real description
        if desc.startswith('-') and desc in flags:
            cleaned_flags[flag] = flags[desc]
        else:
            cleaned_flags[flag] = desc
    flags = cleaned_flags

    return {"summary": summary or help_text.splitlines()[0], "flags": flags}
