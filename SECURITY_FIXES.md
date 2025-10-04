# Security Fixes Required

## CRITICAL: Command Injection Fix

### Problem
User input is passed directly to subprocess calls without validation, allowing command injection attacks.

### Solution
Add input validation and sanitization in `src/man_parser.py`:

```python
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

def get_command_help(command):
    if sys.platform != "linux":
        return "This tool is designed for Linux. Cannot fetch command help on other platforms."

    # Validate command name first
    try:
        command = _validate_command_name(command)
    except ValueError as e:
        return f"Security error: {e}"

    # Rest of the function remains the same...
```

## MEDIUM: File Path Validation

### Problem
File operations in `src/custom_commands.py` don't validate paths.

### Solution
Add path validation:

```python
import os.path

def _validate_path(path):
    """Validate file path to prevent directory traversal."""
    # Resolve the path and check if it's within allowed directory
    resolved_path = os.path.abspath(path)
    allowed_dir = os.path.abspath(_MODULE_DIR)
    
    if not resolved_path.startswith(allowed_dir):
        raise ValueError(f"Path outside allowed directory: {path}")
    
    return resolved_path
```

## MEDIUM: Input Length Limits

### Problem
No limits on input size could lead to DoS attacks.

### Solution
Add input validation in `cli.py`:

```python
def main():
    parser = argparse.ArgumentParser(description="Explains a shell command.")
    parser.add_argument("command_string", nargs='?', help="The shell command to explain.")
    
    args = parser.parse_args()
    
    # Validate input length
    if args.command_string and len(args.command_string) > 10000:
        print("Error: Command string too long (max 10000 characters)")
        return 1
    
    # Rest of the function...
```

## Additional Security Measures

1. **Sandboxing**: Consider running subprocess calls in a restricted environment
2. **Rate Limiting**: Implement rate limiting for subprocess calls
3. **Logging**: Add security event logging
4. **Testing**: Add security tests for command injection scenarios
