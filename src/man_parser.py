import subprocess
import sys
import re
import os

def _validate_command_name(command):
    """Validate command name to prevent injection attacks."""
    # Only allow alphanumeric characters, hyphens, underscores, and dots
    if not re.match(r'^[a-zA-Z0-9._-]+$', command):
        raise ValueError(f"Invalid command name: {command}")
    
    # Prevent path traversal
    if '/' in command or '\\' in command:
        raise ValueError(f"Command name cannot contain path separators: {command}")
    
    # Prevent command chaining
    if any(char in command for char in [';', '&', '|', '`', '$', '(', ')', '<', '>']):
        raise ValueError(f"Command name contains dangerous characters: {command}")
    
    return command

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

    # Validate command name first
    try:
        command = _validate_command_name(command)
    except ValueError as e:
        return f"Security error: {e}"

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


def _get_smart_description(subcmd: str) -> str:
    """Generate smart descriptions for common subcommands based on context."""
    # Network-related subcommands
    if subcmd in ["link", "interface"]:
        return "Network device configuration"
    elif subcmd in ["address"]:
        return "Protocol address management"
    elif subcmd in ["addr"]:
        return "Protocol address management"
    elif subcmd in ["route", "routing"]:
        return "Routing table management"
    elif subcmd in ["neighbor", "neighbour", "arp"]:
        return "Neighbor/ARP table management"
    
    # Common action subcommands
    elif subcmd in ["show", "display", "list"]:
        return "Display information"
    elif subcmd in ["status", "state"]:
        return "Show status information"
    elif subcmd in ["start", "up"]:
        return "Start service/interface"
    elif subcmd in ["stop", "down"]:
        return "Stop service/interface"
    elif subcmd in ["restart", "reload"]:
        return "Restart/reload service"
    elif subcmd in ["enable", "on"]:
        return "Enable service/feature"
    elif subcmd in ["disable", "off"]:
        return "Disable service/feature"
    
    # Git-specific subcommands
    elif subcmd in ["push"]:
        return "Update remote refs along with associated objects"
    elif subcmd in ["pull"]:
        return "Fetch from and integrate with another repository"
    elif subcmd in ["commit"]:
        return "Record changes to the repository"
    elif subcmd in ["clone"]:
        return "Clone a repository into a new directory"
    elif subcmd in ["add"]:
        return "Add file contents to the index"
    elif subcmd in ["branch"]:
        return "List, create, or delete branches"
    elif subcmd in ["merge"]:
        return "Join two or more development histories"
    elif subcmd in ["fetch"]:
        return "Download objects and refs from another repository"
    
    # Generic fallback
    else:
        return f"Subcommand: {subcmd}"

def _extract_subcommands(help_text: str) -> dict:
    """Extract subcommands and their descriptions from help/man text using multiple heuristics.
    
    Returns a dict mapping subcommand to description.
    """
    subcommands = {}
    lines = help_text.splitlines()
    
    # Heuristic 1: Look for OBJECT definitions (ip, ss, etc.)
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if "OBJECT" in line_stripped and ":=" in line_stripped and "{" in line_stripped:
            # Extract subcommands from the OBJECT line and continuation lines
            j = i
            subcmd_text = ""
            while j < len(lines) and "}" not in subcmd_text:
                subcmd_text += " " + lines[j].strip()
                j += 1
            
            # Parse subcommands from the text
            if "{" in subcmd_text and "}" in subcmd_text:
                start = subcmd_text.find("{") + 1
                end = subcmd_text.find("}")
                subcmd_list = subcmd_text[start:end]
                for subcmd in subcmd_list.split("|"):
                    subcmd = subcmd.strip()
                    if subcmd and len(subcmd) > 1:
                        subcommands[subcmd] = _get_smart_description(subcmd)
                        # Add common aliases
                        if subcmd == "address":
                            subcommands["addr"] = _get_smart_description("addr")
    
    # Heuristic 2: Look for indented subcommand lines (git, docker, etc.)
    for line in lines:
        line_stripped = line.strip()
        
        # Pattern: "   subcommand     description" (indented with multiple spaces)
        if re.match(r'^\s+[a-zA-Z][a-zA-Z0-9_-]*\s{2,}', line):
            parts = line_stripped.split(None, 1)
            if len(parts) >= 2:
                subcmd = parts[0]
                desc = parts[1]
                if len(subcmd) > 1 and len(desc) > 3:
                    subcommands[subcmd] = desc
        
        # Pattern: "subcommand - description" (dash separator)
        elif re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*\s+-', line_stripped):
            parts = line_stripped.split(' - ', 1)
            if len(parts) == 2:
                subcmd = parts[0].strip()
                desc = parts[1].strip()
                if len(subcmd) > 1 and len(desc) > 3:
                    subcommands[subcmd] = desc
        
        # Pattern: "subcommand description" (space separator, no dash)
        elif re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*\s+[A-Z]', line_stripped):
            parts = line_stripped.split(None, 1)
            if len(parts) >= 2:
                subcmd = parts[0]
                desc = parts[1]
                # Only if it looks like a description (starts with capital, reasonable length)
                if len(subcmd) > 1 and len(desc) > 5 and desc[0].isupper():
                    subcommands[subcmd] = desc
    
    # Heuristic 3: Look for command lists in sections
    in_commands_section = False
    for line in lines:
        line_stripped = line.strip().lower()
        
        # Detect sections that typically contain commands
        if any(keyword in line_stripped for keyword in ['commands:', 'subcommands:', 'available commands:', 'usage:']):
            in_commands_section = True
            continue
        elif line_stripped and not line_stripped.startswith((' ', '\t')) and ':' in line_stripped:
            in_commands_section = False
            continue
        
        # If we're in a commands section, look for command patterns
        if in_commands_section and line.strip():
            # Look for lines that start with a word followed by description
            if re.match(r'^\s*[a-zA-Z][a-zA-Z0-9_-]*\s+', line):
                parts = line.strip().split(None, 1)
                if len(parts) >= 2:
                    subcmd = parts[0]
                    desc = parts[1]
                    if len(subcmd) > 1 and len(desc) > 3:
                        subcommands[subcmd] = desc
    
    # Add common subcommands that might not be explicitly defined
    common_subcommands = {
        "show": "Display information",
        "list": "List items",
        "ps": "List processes/containers",
        "status": "Show status information",
        "start": "Start service/process",
        "stop": "Stop service/process",
        "restart": "Restart service/process",
        "reload": "Reload configuration",
        "enable": "Enable service/feature",
        "disable": "Disable service/feature",
        "add": "Add item",
        "remove": "Remove item",
        "delete": "Delete item",
        "create": "Create item",
        "destroy": "Destroy item",
        "up": "Bring up interface/service",
        "down": "Bring down interface/service"
    }
    
    # Add common find flags that are often not well-parsed from man pages
    find_flags = {
        "-mtime": "File's data was last modified n*24 hours ago",
        "-mmin": "File's data was last modified n minutes ago", 
        "-atime": "File was last accessed n*24 hours ago",
        "-amin": "File was last accessed n minutes ago",
        "-ctime": "File's status was last changed n*24 hours ago",
        "-cmin": "File's status was last changed n minutes ago",
        "-size": "File uses n units of space",
        "-user": "File is owned by user uname",
        "-group": "File belongs to group gname",
        "-perm": "File's permission bits are exactly mode",
        "-name": "Base of file name matches shell pattern pattern",
        "-type": "File is of type c",
        "-exec": "Execute command",
        "-executable": "Matches files which are executable",
        "-readable": "Matches files which are readable",
        "-writable": "Matches files which are writable",
        "-empty": "File is empty and is either a regular file or a directory",
        "-delete": "Delete files",
        "-print": "Print the full file name",
        "-ls": "List current file in ls -dils format"
    }
    
    # Note: find_flags will be handled in get_command_details function
    
    # Add common subcommands if they're not already defined
    for subcmd, desc in common_subcommands.items():
        if subcmd not in subcommands:
            subcommands[subcmd] = desc
    
    return subcommands

def _extract_flags(help_text: str) -> dict:
    """Heuristically extract flags and their descriptions from help/man text.

    Returns a dict mapping flag (e.g., "-a", "--all", "-sC") to a short description.
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
            
        # Pattern 3: Combined flags like -sC, -sV (more flexible pattern)
        m3 = re.match(r"^\s*([\-]{1,2}[A-Za-z0-9]+[A-Z]?)\s+(.*)$", line)
        if m3:
            f, desc = m3.groups()
            desc = desc.strip()
            
            # Look for continuation lines
            j = i + 1
            while j < len(lines) and lines[j].startswith(" ") and not re.match(r"^\s*\-", lines[j]):
                cont_line = lines[j].strip()
                if cont_line and not cont_line.startswith("-"):
                    desc += " " + cont_line
                j += 1
            
            # Clean up description
            desc = re.split(r"\s{2,}|\.$", desc)[0].strip() or desc
            if desc and len(desc) > 3:  # Only add if we have a meaningful description
                flags[f] = desc
            i = j
            continue
            
        # Pattern 4: Look for flags in man page format like "-sC" or "--script"
        m4 = re.search(r'([\-]{1,2}[A-Za-z0-9]+[A-Z]?)\s+([A-Z][^\.]*\.?)', line)
        if m4 and not any(pattern in line.lower() for pattern in ['usage:', 'synopsis:', 'example:']):
            flag, desc = m4.groups()
            desc = desc.strip()
            if desc and len(desc) > 3:
                flags[flag] = desc
                
        # Pattern 5: Look for flags with better description capture
        m5 = re.match(r'^\s*([\-]{1,2}[A-Za-z0-9]+[A-Z]?)\s+(.*)$', line)
        if m5 and not any(pattern in line.lower() for pattern in ['usage:', 'synopsis:', 'example:']):
            flag, desc = m5.groups()
            desc = desc.strip()
            
            # Look for continuation lines
            j = i + 1
            while j < len(lines) and lines[j].startswith(" ") and not re.match(r"^\s*\-", lines[j]):
                cont_line = lines[j].strip()
                if cont_line and not cont_line.startswith("-"):
                    desc += " " + cont_line
                j += 1
            
            # Clean up description
            if desc and len(desc) > 3:
                # Take first sentence or reasonable length
                desc = re.split(r'\.\s+', desc)[0].strip()
                if not desc.endswith('.'):
                    desc += '.'
                flags[flag] = desc
            i = j
            continue
            
        i += 1
    
    # Post-process to handle common flag patterns and clean up
    cleaned_flags = {}
    for flag, desc in flags.items():
        # Skip very short or unclear descriptions
        if len(desc) < 3 or desc.lower() in ['flag', 'option', 'argument']:
            continue
            
        # Clean up the flag name
        clean_flag = flag.strip()
        
        # Handle flags with parameters like -p<port>
        if '<' in clean_flag and '>' in clean_flag:
            clean_flag = re.sub(r'<[^>]*>', '', clean_flag)
        
        # Handle flags with equals like --script=<script>
        if '=' in clean_flag:
            clean_flag = clean_flag.split('=')[0]
            
        if clean_flag and desc:
            cleaned_flags[clean_flag] = desc
    
    return cleaned_flags


def _get_full_help_text(command: str) -> str:
    """Fetch full help/man text for a command without truncation.

    Tries `command --help` first (uses stdout or stderr regardless of exit code),
    then falls back to `man`.
    """
    if sys.platform != "linux":
        return "This tool is designed for Linux. Cannot fetch command help on other platforms."

    # Validate command name first
    try:
        command = _validate_command_name(command)
    except ValueError as e:
        return f"Security error: {e}"

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

    Structure: { 'summary': str, 'flags': { flag: description }, 'subcommands': { subcmd: description } }
    """
    help_text = _get_full_help_text(command)
    if help_text.startswith("Command not found:") or help_text.startswith("Could not find help"):
        return {"summary": help_text, "flags": {}, "subcommands": {}}

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

    # Extract subcommands
    subcommands = {}
    help_subcommands = _extract_subcommands(help_text)
    man_subcommands = _extract_subcommands(man_text) if man_text else {}
    subcommands.update(man_subcommands)
    subcommands.update(help_subcommands)

    # Add find-specific flags if this is the find command
    if command == "find":
        find_flags = {
            "-mtime": "File's data was last modified n*24 hours ago",
            "-mmin": "File's data was last modified n minutes ago", 
            "-atime": "File was last accessed n*24 hours ago",
            "-amin": "File was last accessed n minutes ago",
            "-ctime": "File's status was last changed n*24 hours ago",
            "-cmin": "File's status was last changed n minutes ago",
            "-size": "File uses n units of space",
            "-user": "File is owned by user uname",
            "-group": "File belongs to group gname",
            "-perm": "File's permission bits are exactly mode",
            "-name": "Base of file name matches shell pattern pattern",
            "-type": "File is of type c",
            "-exec": "Execute command",
            "-executable": "Matches files which are executable",
            "-readable": "Matches files which are readable",
            "-writable": "Matches files which are writable",
            "-empty": "File is empty and is either a regular file or a directory",
            "-delete": "Delete files",
            "-print": "Print the full file name",
            "-ls": "List current file in ls -dils format"
        }
        
        # Add find flags, overriding poor man page extractions
        for flag, desc in find_flags.items():
            if flag not in flags or len(flags[flag]) < 10:
                flags[flag] = desc

    return {"summary": summary or help_text.splitlines()[0], "flags": flags, "subcommands": subcommands}
