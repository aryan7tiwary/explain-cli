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
