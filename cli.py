#!/usr/bin/env python3
import argparse
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
from src.parser import tokenize_command
from src.knowledge_base import COMMAND_KNOWLEDGE_BASE
from src.danger_detector import detect_dangerous_patterns
from src.man_parser import get_command_help, get_command_details
from src.custom_commands import load_custom_commands, add_custom_command
from src.regex_explainer import looks_like_regex, explain_regex
from src.signals import explain_signal_flag

# Color codes for professional output
class Colors:
    """Professional color scheme for terminal output."""
    # Primary colors
    COMMAND = '\033[1;34m'      # Bright blue for command names
    FLAG = '\033[0;36m'         # Cyan for flags
    VALUE = '\033[0;32m'        # Green for values
    DESCRIPTION = '\033[0;37m'  # White for descriptions
    WARNING = '\033[1;33m'      # Bright yellow for warnings
    ERROR = '\033[1;31m'        # Bright red for errors
    SUCCESS = '\033[0;32m'      # Green for success messages
    META = '\033[0;90m'         # Dark gray for meta information
    
    # Reset
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def colorize(text, color):
    """Apply color to text if terminal supports it."""
    if not sys.stdout.isatty():
        return text  # No colors if not a terminal
    return f"{color}{text}{Colors.RESET}"

# Global flag to disable colors
NO_COLOR = False

def set_no_color(disable):
    """Set the global no-color flag."""
    global NO_COLOR
    NO_COLOR = disable

def colorize_with_flag(text, color):
    """Apply color to text if colors are enabled and terminal supports it."""
    if NO_COLOR or not sys.stdout.isatty():
        return text  # No colors if disabled or not a terminal
    return f"{color}{text}{Colors.RESET}"

def print_header(command):
    """Print a professional command header."""
    print(f"\n{colorize_with_flag('Command:', Colors.META)} {colorize_with_flag(command, Colors.COMMAND)}")
    print(f"{colorize_with_flag('─' * (len(command) + 10), Colors.META)}")

def print_explanation(explanation, warnings):
    """Print explanations with professional formatting."""
    if not explanation:
        return
    
    print(f"\n{colorize_with_flag('Explanation:', Colors.META)}")
    
    for line in explanation:
        if line.startswith("  "):
            # Indented line (flag or argument)
            if ":" in line and not line.strip().endswith(":"):
                # Has a colon (flag: description)
                parts = line.split(":", 1)
                flag_part = parts[0].strip()
                desc_part = parts[1].strip()
                
                # Colorize flag and description
                colored_flag = colorize_with_flag(flag_part, Colors.FLAG)
                colored_desc = colorize_with_flag(desc_part, Colors.DESCRIPTION)
                print(f"  {colored_flag}: {colored_desc}")
            else:
                # Regular indented line
                print(f"{colorize_with_flag(line, Colors.DESCRIPTION)}")
        else:
            # Main command line
            if ":" in line and not line.strip().endswith(":"):
                parts = line.split(":", 1)
                cmd_part = parts[0].strip()
                desc_part = parts[1].strip()
                
                colored_cmd = colorize_with_flag(cmd_part, Colors.COMMAND)
                colored_desc = colorize_with_flag(desc_part, Colors.DESCRIPTION)
                print(f"{colored_cmd}: {colored_desc}")
            else:
                print(f"{colorize_with_flag(line, Colors.COMMAND)}")

def print_warnings(warnings):
    """Print warnings with professional formatting."""
    if warnings:
        print(f"\n{colorize_with_flag('Warnings:', Colors.WARNING)}")
        for warning in warnings:
            print(f"  {colorize_with_flag('*', Colors.WARNING)} {colorize_with_flag(warning, Colors.DESCRIPTION)}")

def print_pipe_operator(op):
    """Print pipe operators with special formatting."""
    op_symbols = {
        '|': '|',
        '&&': '&&',
        '||': '||',
        ';': ';'
    }
    symbol = op_symbols.get(op, op)
    return f"{colorize_with_flag(symbol, Colors.META)}"

def truncate_description(description, max_length=100):
    """Truncate overly long descriptions to keep output readable."""
    if len(description) <= max_length:
        return description
    
    # Find a good break point (end of sentence or comma)
    truncated = description[:max_length]
    for break_char in ['. ', ', ', '; ']:
        last_break = truncated.rfind(break_char)
        if last_break > max_length * 0.7:  # Only break if we don't lose too much
            return truncated[:last_break + 1] + "..."
    
    return truncated + "..."

def handle_repeated_flags(flag, count):
    """Handle repeated flags like -vv, -vvv, etc."""
    if count == 1:
        return flag
    elif count == 2:
        return f"{flag}{flag}"
    else:
        return f"{flag}{count}"

def auto_escape_command(command_string):
    """Automatically escape special characters in command strings for better parsing."""
    import re
    
    # Don't escape if already properly quoted
    if (command_string.startswith('"') and command_string.endswith('"')) or \
       (command_string.startswith("'") and command_string.endswith("'")):
        return command_string
    
    # Escape dollar signs that aren't already escaped
    command_string = re.sub(r'(?<!\\)\$', r'\\$', command_string)
    
    # Escape unescaped double quotes
    command_string = re.sub(r'(?<!\\)"', r'\\"', command_string)
    
    # Escape unescaped backticks
    command_string = re.sub(r'(?<!\\)`', r'\\`', command_string)
    
    # Escape unescaped backslashes that aren't already escaping something
    # This is tricky - we need to be careful not to double-escape
    command_string = re.sub(r'(?<!\\)\\(?!["$`\\])', r'\\\\', command_string)
    
    return command_string

def parse_combined_flags(arg, flags):
    """Parse combined flags like -vv, -sC, -sV, etc."""
    if not arg.startswith('-') or len(arg) < 2:
        return []
    
    # Check for exact match first
    if arg in flags:
        return [(arg, flags[arg])]
    
    # Handle repeated single flags like -vv, -vvv
    if len(arg) > 2 and len(set(arg[1:])) == 1:  # All characters are the same
        char = arg[1]
        single_flag = f"-{char}"
        if single_flag in flags:
            count = len(arg) - 1
            return [(arg, f"{flags[single_flag]} (repeated {count} times)")]
    
    # Handle combined flags like -sC, -sV
    if len(arg) > 2:
        # Try to find the longest matching prefix
        for i in range(len(arg) - 1, 1, -1):
            prefix = arg[:i]
            if prefix in flags:
                remaining = arg[i:]
                results = [(prefix, flags[prefix])]
                # Parse remaining characters
                for char in remaining:
                    single_flag = f"-{char}"
                    if single_flag in flags:
                        results.append((single_flag, flags[single_flag]))
                return results
    
    # Fall back to individual character parsing
    results = []
    for char in arg[1:]:
        single_flag = f"-{char}"
        if single_flag in flags:
            results.append((single_flag, flags[single_flag]))
    
    return results

class ExplainAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the explain-cli API server."""
    
    def __init__(self, knowledge_base, *args, **kwargs):
        self.knowledge_base = knowledge_base
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests - return API documentation."""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            api_info = {
                "name": "explain-cli API",
                "version": "1.0.0",
                "description": "RESTful API for shell command explanation and analysis",
                "endpoints": {
                    "POST /explain": {
                        "description": "Analyze and explain shell commands with flag descriptions and security warnings",
                        "parameters": {
                            "command": "Shell command to explain (required, string)",
                            "no_auto_escape": "Disable automatic character escaping (optional, boolean, default: false)",
                            "no_color": "Disable colored output formatting (optional, boolean, default: true)"
                        },
                        "response": {
                            "command": "Original command string",
                            "escaped_command": "Auto-escaped version (if applicable)",
                            "explanation": "Array of explanation lines",
                            "warnings": "Array of security warnings",
                            "success": "Boolean indicating success"
                        }
                    },
                    "GET /": "API documentation and usage information"
                },
                "usage_examples": {
                    "curl": "curl -X POST http://localhost:8080/explain -H 'Content-Type: application/json' -d '{\"command\": \"ls -la\"}'",
                    "python": "import requests; response = requests.post('http://localhost:8080/explain', json={'command': 'ls -la'}); print(response.json())",
                    "javascript": "fetch('http://localhost:8080/explain', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({command: 'ls -la'})}).then(r => r.json()).then(console.log)"
                },
                "error_codes": {
                    "400": "Bad Request - Invalid JSON or missing required fields",
                    "404": "Not Found - Invalid endpoint",
                    "500": "Internal Server Error - Processing error"
                }
            }
            
            self.wfile.write(json.dumps(api_info, indent=2).encode())
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests - explain commands."""
        if self.path == '/explain':
            try:
                # Read request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Parse JSON
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON")
                    return
                
                # Validate required fields
                if 'command' not in data:
                    self.send_error(400, "Missing required field: command")
                    return
                
                command = data['command']
                no_auto_escape = data.get('no_auto_escape', False)
                no_color = data.get('no_color', True)  # Default to no color for API
                
                # Validate input length
                if len(command) > 10000:
                    self.send_error(400, "Command string too long (max 10000 characters)")
                    return
                
                # Process the command
                result = process_command_explanation(command, no_auto_escape, no_color, self.knowledge_base)
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                
                self.wfile.write(json.dumps(result, indent=2).encode())
                
            except Exception as e:
                self.send_error(500, f"Internal server error: {str(e)}")
        else:
            self.send_error(404, "Not Found")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce log verbosity."""
        pass

def create_api_handler(knowledge_base):
    """Create an API handler with the knowledge base."""
    def handler(*args, **kwargs):
        return ExplainAPIHandler(knowledge_base, *args, **kwargs)
    return handler

def process_command_explanation(command_string, no_auto_escape=False, no_color=True, knowledge_base=None):
    """Process a command explanation and return structured data."""
    if knowledge_base is None:
        custom_commands = load_custom_commands()
        knowledge_base = {**COMMAND_KNOWLEDGE_BASE, **custom_commands}
    
    # Auto-escape special characters for better parsing (unless disabled)
    if no_auto_escape:
        escaped_command = command_string
    else:
        escaped_command = auto_escape_command(command_string)
    
    tokens = tokenize_command(escaped_command)
    
    explanation, analysis_warnings = analyze_command(tokens, knowledge_base)
    danger_warnings = detect_dangerous_patterns(command_string, tokens)
    
    all_warnings = analysis_warnings + danger_warnings
    
    # Structure the response
    result = {
        "command": command_string,
        "escaped_command": escaped_command if escaped_command != command_string else None,
        "explanation": explanation,
        "warnings": all_warnings,
        "success": True
    }
    
    return result

def start_api_server(host='localhost', port=8080, knowledge_base=None):
    """Start the API server."""
    if knowledge_base is None:
        custom_commands = load_custom_commands()
        knowledge_base = {**COMMAND_KNOWLEDGE_BASE, **custom_commands}
    
    handler_class = create_api_handler(knowledge_base)
    server = HTTPServer((host, port), handler_class)
    
    print(f"explain-cli API server starting on http://{host}:{port}")
    print(f"API documentation available at http://{host}:{port}")
    print(f"Example usage: curl -X POST http://{host}:{port}/explain -H 'Content-Type: application/json' -d '{{\"command\": \"ls -la\"}}'")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down API server...")
        server.shutdown()

def _analyze_single_command(tokens, knowledge_base):
    explanation = []
    warnings = []
    if not tokens:
        return explanation, warnings

    command = tokens[0]
    args = tokens[1:]
    
    # Special handling for sudo - explain both sudo and the command it runs
    if command == "sudo" and args:
        # Explain sudo itself
        if command in knowledge_base:
            command_info = knowledge_base[command]
            explanation.append(f"{command}: {command_info['description']}")
            if command_info['danger_level'] in ["high", "critical"]:
                warnings.append(f"The command '{command}' is considered {command_info['danger_level']} risk.")
        
        # Explain the command being run with sudo
        sub_command = args[0]
        sub_args = args[1:]
        
        if sub_command in knowledge_base:
            sub_info = knowledge_base[sub_command]
            explanation.append(f"  Executing: {sub_command} - {sub_info['description']}")
            if sub_info['danger_level'] in ["high", "critical"]:
                warnings.append(f"The command '{sub_command}' is considered {sub_info['danger_level']} risk.")
            
            # Explain flags for the sub-command
            flags = sub_info.get("flags", {})
            for arg in sub_args:
                if arg.startswith("--") and arg in flags:
                    explanation.append(f"    {arg}: {flags[arg]}")
                elif arg.startswith("-") and len(arg) > 2:
                    # First check if the entire flag exists (for combined flags like -sC, -sV)
                    if arg in flags:
                        explanation.append(f"    {arg}: {flags[arg]}")
                    else:
                        # If not found as a combined flag, try individual characters
                        for char in arg[1:]:
                            flag = f"-{char}"
                            if flag in flags:
                                explanation.append(f"    {flag}: {flags[flag]}")
                elif arg in flags:
                    explanation.append(f"    {arg}: {flags[arg]}")
        else:
            # Unknown sub-command - get details from man/help
            details = get_command_details(sub_command)
            if details.get("summary"):
                explanation.append(f"  Executing: {details['summary']}")
            
            # Explain flags and subcommands for the sub-command
            flags = details.get("flags", {})
            subcommands = details.get("subcommands", {})
            for arg in sub_args:
                if arg.startswith("--"):
                    name, eq, val = arg.partition('=')
                    if name in flags:
                        if eq and val:
                            explanation.append(f"    {name}: {flags[name]} (value: {val})")
                        else:
                            explanation.append(f"    {name}: {flags[name]}")
                elif arg.startswith("-") and len(arg) > 2:
                    # First check if the entire flag exists (for combined flags like -sC, -sV)
                    if arg in flags:
                        explanation.append(f"    {arg}: {flags[arg]}")
                    else:
                        # If not found as a combined flag, try individual characters
                        for char in arg[1:]:
                            flag = f"-{char}"
                            if flag in flags:
                                explanation.append(f"    {flag}: {flags[flag]}")
                elif arg in flags:
                    explanation.append(f"    {arg}: {flags[arg]}")
                elif arg in subcommands:
                    explanation.append(f"    {arg}: {subcommands[arg]}")
        
        # Handle special sub-commands that need custom parsing
        if sub_command == "find" and sub_args:
            explanation.append(f"  search_path: {sub_args[0]}")
            
            # Get find flags from man page for dynamic parsing
            details = get_command_details("find")
            find_flags = details.get("flags", {})
            
            i = 1
            while i < len(sub_args):
                arg = sub_args[i]
                
                # Handle flags that take values
                if arg in find_flags and i + 1 < len(sub_args):
                    next_arg = sub_args[i+1]
                    # Check if next argument is a value (not another flag)
                    is_value = (
                        not next_arg.startswith('-') or  # Not a flag
                        next_arg[1:].isdigit() or        # Negative number like -7
                        next_arg.startswith('+') or      # Positive number like +30
                        next_arg in ['{}', ';'] or       # Special find tokens
                        (len(next_arg) > 1 and next_arg[1] in '0123456789')  # Negative number
                    )
                    
                    if is_value:
                        value = next_arg
                        if arg == "-name":
                            explanation.append(f"    -name: find files matching pattern '{value}'")
                        elif arg == "-type":
                            type_desc = {"f": "regular file", "d": "directory", "l": "symbolic link"}.get(value, value)
                            explanation.append(f"    -type: find items of type '{type_desc}'")
                        elif arg == "-mtime":
                            if value.startswith('+'):
                                explanation.append(f"    -mtime: find files modified more than {value[1:]} days ago")
                            elif value.startswith('-'):
                                explanation.append(f"    -mtime: find files modified less than {value[1:]} days ago")
                            else:
                                explanation.append(f"    -mtime: find files modified exactly {value} days ago")
                        elif arg == "-mmin":
                            if value.startswith('+'):
                                explanation.append(f"    -mmin: find files modified more than {value[1:]} minutes ago")
                            elif value.startswith('-'):
                                explanation.append(f"    -mmin: find files modified less than {value[1:]} minutes ago")
                            else:
                                explanation.append(f"    -mmin: find files modified exactly {value} minutes ago")
                        elif arg == "-size":
                            explanation.append(f"    -size: find files of size {value}")
                        elif arg == "-user":
                            explanation.append(f"    -user: find files owned by user '{value}'")
                        elif arg == "-group":
                            explanation.append(f"    -group: find files owned by group '{value}'")
                        elif arg == "-perm":
                            explanation.append(f"    -perm: find files with permissions {value}")
                        elif arg == "-exec":
                            explanation.append(f"    -exec: execute command '{value}' on found files")
                        else:
                            explanation.append(f"    {arg}: {find_flags[arg]} (value: {value})")
                        i += 2
                    else:
                        # Not a value, treat as flag without value
                        if arg == "-delete":
                            explanation.append(f"    -delete: delete found files (dangerous)")
                            warnings.append("The -delete flag will permanently remove files")
                        elif arg == "-print":
                            explanation.append(f"    -print: print found files (default action)")
                        elif arg == "-ls":
                            explanation.append(f"    -ls: list found files in long format")
                        elif arg == "-executable":
                            explanation.append(f"    -executable: find executable files")
                        elif arg == "-readable":
                            explanation.append(f"    -readable: find readable files")
                        elif arg == "-writable":
                            explanation.append(f"    -writable: find writable files")
                        else:
                            explanation.append(f"    {arg}: {find_flags[arg]}")
                        i += 1
                elif arg in find_flags:
                    # Flag without value
                    if arg == "-delete":
                        explanation.append(f"    -delete: delete found files (dangerous)")
                        warnings.append("The -delete flag will permanently remove files")
                    elif arg == "-print":
                        explanation.append(f"    -print: print found files (default action)")
                    elif arg == "-ls":
                        explanation.append(f"    -ls: list found files in long format")
                    elif arg == "-executable":
                        explanation.append(f"    -executable: find executable files")
                    elif arg == "-readable":
                        explanation.append(f"    -readable: find readable files")
                    elif arg == "-writable":
                        explanation.append(f"    -writable: find writable files")
                    else:
                        explanation.append(f"    {arg}: {find_flags[arg]}")
                    i += 1
                elif arg == "{}":
                    # This is part of -exec, skip it
                    i += 1
                elif arg == ";":
                    # End of -exec command
                    i += 1
                else:
                    explanation.append(f"    argument: {arg}")
                    i += 1
        else:
            # Add remaining arguments for other commands
            remaining_args = [arg for arg in sub_args if not arg.startswith("-")]
            if remaining_args:
                explanation.append(f"  Arguments: {', '.join(remaining_args)}")
        
        return explanation, warnings

    if command in knowledge_base:
        command_info = knowledge_base[command]
        explanation.append(f"{command}: {command_info['description']}")
        if command_info['danger_level'] in ["high", "critical"]:
            warnings.append(f"The command '{command}' is considered {command_info['danger_level']} risk.")

        flags = command_info.get("flags", {})
        # Always try to get additional flags dynamically and merge them
        details = get_command_details(command)
        dynamic_flags = details.get("flags", {})
        # Merge dynamic flags with hardcoded ones (dynamic takes precedence for conflicts)
        flags.update(dynamic_flags)
        used_flags = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                name, eq, val = arg.partition('=')
                if name in flags:
                    truncated_desc = truncate_description(flags[name])
                    if eq and val:
                        explanation.append(f"  {name}: {truncated_desc} (value: {val})")
                    elif i + 1 < len(args) and not args[i+1].startswith('-'):
                        explanation.append(f"  {name}: {truncated_desc} (value: {args[i+1]})")
                        i += 1
                    else:
                        explanation.append(f"  {name}: {truncated_desc}")
            elif arg.startswith("-") and len(arg) > 2:
                # Use the new combined flag parser
                flag_results = parse_combined_flags(arg, flags)
                for flag, desc in flag_results:
                    truncated_desc = truncate_description(desc)
                    explanation.append(f"  {flag}: {truncated_desc}")
            elif arg in flags:
                # Short flag possibly with a following value
                if i + 1 < len(args) and not args[i+1].startswith('-'):
                    truncated_desc = truncate_description(flags[arg])
                    explanation.append(f"  {arg}: {truncated_desc} (value: {args[i+1]})")
                    i += 1
                else:
                    truncated_desc = truncate_description(flags[arg])
                    explanation.append(f"  {arg}: {truncated_desc}")
            i += 1
    else:
        details = get_command_details(command)
        if details.get("summary"):
            explanation.append(details["summary"])
        flags = details.get("flags", {})
        subcommands = details.get("subcommands", {})
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                name, eq, val = arg.partition('=')
                if name in flags:
                    truncated_desc = truncate_description(flags[name])
                    if eq and val:
                        explanation.append(f"  {name}: {truncated_desc} (value: {val})")
                    elif i + 1 < len(args) and not args[i+1].startswith('-'):
                        explanation.append(f"  {name}: {truncated_desc} (value: {args[i+1]})")
                        i += 1
                    else:
                        explanation.append(f"  {name}: {truncated_desc}")
            elif arg.startswith("-") and len(arg) > 2:
                # Use the new combined flag parser
                flag_results = parse_combined_flags(arg, flags)
                for flag, desc in flag_results:
                    truncated_desc = truncate_description(desc)
                    explanation.append(f"  {flag}: {truncated_desc}")
            elif arg in flags:
                if i + 1 < len(args) and not args[i+1].startswith('-'):
                    explanation.append(f"  {arg}: {flags[arg]} (value: {args[i+1]})")
                    i += 1
                else:
                    explanation.append(f"  {arg}: {flags[arg]}")
            elif arg in subcommands:
                # Handle subcommands
                explanation.append(f"  {arg}: {subcommands[arg]}")
            i += 1

    # Detect I/O redirections in args and mark consumed indices
    redirections = []  # list of tuples (op, target)
    i = 0
    while i < len(args):
        tok = args[i]
        # Supported forms: '>', '>>', '1>', '2>', '1>>', '2>>'
        if tok in ('>', '>>') or (len(tok) <= 3 and tok.endswith(('>', '>>')) and tok[:-1].isdigit()):
            if i + 1 < len(args):
                redirections.append((tok, args[i+1]))
                i += 1
        i += 1

    # Remove values already consumed by flags
    consumed = set()
    i = 0
    while i < len(args):
        arg = args[i]
        # Generic signal flag explanations for kill-like commands
        if command in ("kill", "killall"):
            next_arg = args[i+1] if i + 1 < len(args) else None
            sig_exp = explain_signal_flag(arg, next_arg)
            if sig_exp:
                explanation.append(sig_exp)
                if arg == '-s' and next_arg and not next_arg.startswith('-'):
                    consumed.add(i+1)
        # Skip flag parsing for find command - handle it specially later
        elif command != "find" and arg.startswith('--'):
            name, eq, val = arg.partition('=')
            if eq and val:
                pass
            elif i + 1 < len(args) and not args[i+1].startswith('-'):
                consumed.add(i+1)
                i += 1
        # Do not generically consume a value after single-dash short flags;
        # Without per-command metadata this can misclassify positional args
        i += 1
    # Exclude redirection targets as positional args
    redir_target_indices = set()
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in ('>', '>>') or (len(tok) <= 3 and tok.endswith(('>', '>>')) and tok[:-1].isdigit()):
            if i + 1 < len(args):
                redir_target_indices.add(i+1)
                i += 1
        i += 1

    # Filter out recognized subcommands from positional args
    recognized_subcommands = set()
    if command in knowledge_base:
        # For commands in knowledge base, check if they have subcommands
        details = get_command_details(command)
        recognized_subcommands = set(details.get("subcommands", {}).keys())
    else:
        # For commands not in knowledge base, get subcommands from man parser
        details = get_command_details(command)
        recognized_subcommands = set(details.get("subcommands", {}).keys())
    
    positional_args = [arg for idx, arg in enumerate(args) if idx not in consumed and idx not in redir_target_indices and not arg.startswith("-") and arg not in recognized_subcommands]
    
    # Special handling for find command (before other command-specific logic)
    if command == "find" and args:
        explanation.append(f"  search_path: {args[0]}")
        
        # Get find flags from man page for dynamic parsing
        details = get_command_details("find")
        find_flags = details.get("flags", {})
        
        i = 1
        while i < len(args):
            arg = args[i]
            
            # Handle flags that take values
            if arg in find_flags and i + 1 < len(args):
                next_arg = args[i+1]
                # Check if next argument is a value (not another flag)
                # Values can be: numbers, negative numbers, patterns, etc.
                is_value = (
                    not next_arg.startswith('-') or  # Not a flag
                    next_arg[1:].isdigit() or        # Negative number like -7
                    next_arg.startswith('+') or      # Positive number like +30
                    next_arg in ['{}', ';'] or       # Special find tokens
                    (len(next_arg) > 1 and next_arg[1] in '0123456789')  # Negative number
                )
                
                if is_value:
                    value = next_arg
                    if arg == "-name":
                        explanation.append(f"  -name: find files matching pattern '{value}'")
                    elif arg == "-type":
                        type_desc = {"f": "regular file", "d": "directory", "l": "symbolic link"}.get(value, value)
                        explanation.append(f"  -type: find items of type '{type_desc}'")
                    elif arg == "-mtime":
                        if value.startswith('+'):
                            explanation.append(f"  -mtime: find files modified more than {value[1:]} days ago")
                        elif value.startswith('-'):
                            explanation.append(f"  -mtime: find files modified less than {value[1:]} days ago")
                        else:
                            explanation.append(f"  -mtime: find files modified exactly {value} days ago")
                    elif arg == "-mmin":
                        if value.startswith('+'):
                            explanation.append(f"  -mmin: find files modified more than {value[1:]} minutes ago")
                        elif value.startswith('-'):
                            explanation.append(f"  -mmin: find files modified less than {value[1:]} minutes ago")
                        else:
                            explanation.append(f"  -mmin: find files modified exactly {value} minutes ago")
                    elif arg == "-size":
                        explanation.append(f"  -size: find files of size {value}")
                    elif arg == "-user":
                        explanation.append(f"  -user: find files owned by user '{value}'")
                    elif arg == "-group":
                        explanation.append(f"  -group: find files owned by group '{value}'")
                    elif arg == "-perm":
                        explanation.append(f"  -perm: find files with permissions {value}")
                    elif arg == "-exec":
                        explanation.append(f"  -exec: execute command '{value}' on found files")
                    else:
                        explanation.append(f"  {arg}: {find_flags[arg]} (value: {value})")
                    i += 2
                else:
                    # Not a value, treat as flag without value
                    if arg == "-delete":
                        explanation.append(f"  -delete: delete found files (dangerous)")
                        warnings.append("The -delete flag will permanently remove files")
                    elif arg == "-print":
                        explanation.append(f"  -print: print found files (default action)")
                    elif arg == "-ls":
                        explanation.append(f"  -ls: list found files in long format")
                    elif arg == "-executable":
                        explanation.append(f"  -executable: find executable files")
                    elif arg == "-readable":
                        explanation.append(f"  -readable: find readable files")
                    elif arg == "-writable":
                        explanation.append(f"  -writable: find writable files")
                    else:
                        explanation.append(f"  {arg}: {find_flags[arg]}")
                    i += 1
            elif arg in find_flags:
                # Flag without value
                if arg == "-delete":
                    explanation.append(f"  -delete: delete found files (dangerous)")
                    warnings.append("The -delete flag will permanently remove files")
                elif arg == "-print":
                    explanation.append(f"  -print: print found files (default action)")
                elif arg == "-ls":
                    explanation.append(f"  -ls: list found files in long format")
                elif arg == "-executable":
                    explanation.append(f"  -executable: find executable files")
                elif arg == "-readable":
                    explanation.append(f"  -readable: find readable files")
                elif arg == "-writable":
                    explanation.append(f"  -writable: find writable files")
                else:
                    explanation.append(f"  {arg}: {find_flags[arg]}")
                i += 1
            
            # Handle special cases
            elif arg == "{}":
                # This is part of -exec, skip it
                i += 1
            elif arg == ";":
                # End of -exec command
                i += 1
            else:
                explanation.append(f"  argument: {arg}")
                i += 1
    elif command == "grep" and positional_args:
        explanation.append(f"  pattern: {positional_args[0]}")
        if looks_like_regex(positional_args[0]):
            explanation.append(f"  regex: {explain_regex(positional_args[0])}")
        if len(positional_args) > 1:
            explanation.append(f"  files: {', '.join(positional_args[1:])}")
    elif command == "chmod" and positional_args:
        mode = positional_args[0]
        target = ", ".join(positional_args[1:]) if len(positional_args) > 1 else None
        # Octal mode like 755 or 0644
        import re as _re
        if _re.fullmatch(r"0?[0-7]{3}", mode):
            digits = mode[-3:]
            who = ["owner", "group", "others"]
            bits = []
            for label, d in zip(who, digits):
                val = int(d)
                perms = []
                if val & 4:
                    perms.append("read")
                if val & 2:
                    perms.append("write")
                if val & 1:
                    perms.append("execute")
                perm_str = "none" if not perms else "/".join(perms)
                bits.append(f"  {label}: {d} ({perm_str})")
            explanation.append(f"  mode: {mode}")
            explanation.extend(bits)
            if target:
                explanation.append(f"  target: {target}")
        else:
            # For symbolic modes like u+x,g-w
            explanation.append(f"  mode: {mode}")
            if target:
                explanation.append(f"  target: {target}")
    elif command == "chown" and positional_args:
        owner_group = positional_args[0]
        targets = positional_args[1:]
        owner = None
        group = None
        if ":" in owner_group:
            owner, group = owner_group.split(":", 1)
            owner = owner if owner else None
            group = group if group else None
        else:
            owner = owner_group
        def _id_hint(val: str) -> str:
            return " (numeric id)" if val.isdigit() else ""
        if owner is not None:
            explanation.append(f"  owner: {owner}{_id_hint(owner)}")
        if group is not None:
            explanation.append(f"  group: {group}{_id_hint(group)}")
        if targets:
            explanation.append(f"  target: {', '.join(targets)}")
    elif command == "echo" and positional_args:
        # Prefer more descriptive echo explanation and suppress generic Arguments line
        explanation.append("- echo: prints a line of text to standard output")
        explanation.append(f"- \"{positional_args[0]}\": the string being printed")
    elif positional_args:
        explanation.append(f"Arguments: {', '.join(positional_args)}")

    # Add explanations for redirections and warnings for overwrite
    for op, target in redirections:
        if op in ('>', '1>'):
            explanation.append(f"- {op} {target}: redirects the output into a file named {target} (overwrites file if it exists)")
            warnings.append(f"This command overwrites {target}. Any existing content will be lost.")
        elif op in ('>>', '1>>'):
            explanation.append(f"- {op} {target}: appends standard output to {target}")
        elif op.startswith('2') and op.endswith('>>'):
            explanation.append(f"- {op} {target}: appends standard error to {target}")
        elif op.startswith('2') and op.endswith('>'):
            explanation.append(f"- {op} {target}: redirects standard error to {target} (overwrites)")

    return explanation, warnings


def analyze_command(tokens, knowledge_base):
    segments = []
    current = []
    for tok in tokens:
        if tok in ['|', '&&', '||', ';']:
            if current:
                segments.append(current)
                current = []
            # Add the operator as a separate segment for explanation
            segments.append([tok])
        else:
            current.append(tok)
    if current:
        segments.append(current)

    all_explanations = []
    all_warnings = []
    for segment in segments:
        if len(segment) == 1 and segment[0] in ['&&', '||', ';', '|']:
            # Explain operators
            op = segment[0]
            if op == '&&':
                all_explanations.append(f"  {op}: Execute next command only if previous command succeeds")
            elif op == '||':
                all_explanations.append(f"  {op}: Execute next command only if previous command fails")
            elif op == ';':
                all_explanations.append(f"  {op}: Execute next command regardless of previous command's result")
            elif op == '|':
                all_explanations.append(f"  {print_pipe_operator(op)}: Pipe the output of the previous command as input to the next command")
        else:
            exp, warns = _analyze_single_command(segment, knowledge_base)
            all_explanations.extend(exp)
            all_warnings.extend(warns)
    return all_explanations, all_warnings

def main():
    parser = argparse.ArgumentParser(
        description="Explain shell commands with detailed flag descriptions and security warnings.",
        epilog="Examples:\n"
               "  %(prog)s 'ls -la'\n"
               "  %(prog)s 'find /var/log -name \"*.log\" -mtime +30'\n"
               "  %(prog)s --api --port 8080\n"
               "  %(prog)s --add-command mycmd 'Custom command' low '-v:verbose'",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command_string", nargs='?', 
                       help="Shell command to explain")
    parser.add_argument("--add-command", nargs=4, 
                       help="Add custom command to knowledge base",
                       metavar=("COMMAND", "DESCRIPTION", "DANGER_LEVEL", "FLAGS"))
    parser.add_argument("--no-color", action="store_true", 
                       help="Disable colored output")
    parser.add_argument("--no-auto-escape", action="store_true", 
                       help="Disable automatic character escaping")
    parser.add_argument("--api", action="store_true", 
                       help="Start HTTP API server")
    parser.add_argument("--host", default="localhost", 
                       help="API server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8080, 
                       help="API server port (default: 8080)")

    args = parser.parse_args()

    # Set the no-color flag
    set_no_color(args.no_color)

    custom_commands = load_custom_commands()
    knowledge_base = {**COMMAND_KNOWLEDGE_BASE, **custom_commands}

    # Handle API mode
    if args.api:
        start_api_server(args.host, args.port, knowledge_base)
        return

    if args.add_command:
        command, description, danger_level, flags_str = args.add_command
        # Parse flags provided as "-f:desc, -g:desc"; allow "none" to mean no flags
        flags = {}
        if flags_str and flags_str.strip().lower() not in {"none", "null", "nil", "-"}:
            parts = [p.strip() for p in flags_str.split(",") if p.strip()]
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                    flags[k.strip().replace("'", "")] = v.strip().replace("'", "")
        add_custom_command(command, description, danger_level, flags)
        print(f"{colorize_with_flag('Success:', Colors.SUCCESS)} Command '{colorize_with_flag(command, Colors.COMMAND)}' added to the custom knowledge base.")
        return

    if not args.command_string:
        parser.print_help()
        return

    # Validate input length to prevent DoS attacks
    if len(args.command_string) > 10000:
        print(f"{colorize_with_flag('Error:', Colors.ERROR)} Command string too long (max 10000 characters)")
        return

    # Auto-escape special characters for better parsing (unless disabled)
    if args.no_auto_escape:
        escaped_command = args.command_string
    else:
        escaped_command = auto_escape_command(args.command_string)
        
        # Show the user what we're actually parsing (if different from input)
        if escaped_command != args.command_string:
            print(f"{colorize_with_flag('Note:', Colors.META)} Auto-escaped command: {colorize_with_flag(escaped_command, Colors.DESCRIPTION)}")
    
    tokens = tokenize_command(escaped_command)
    
    explanation, analysis_warnings = analyze_command(tokens, knowledge_base)
    danger_warnings = detect_dangerous_patterns(args.command_string, tokens)

    all_warnings = analysis_warnings + danger_warnings

    # Print colorized output
    print_header(args.command_string)
    print_explanation(explanation, all_warnings)
    print_warnings(all_warnings)

if __name__ == "__main__":
    main()
