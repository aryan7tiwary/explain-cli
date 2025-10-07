# Explain CLI

A professional command-line tool that provides detailed explanations of shell commands with intelligent flag parsing, security warnings, and API integration capabilities.

## Features

- **Intelligent Command Analysis**: Explains Unix utilities with dynamic flag extraction from man pages
- **Pipeline Processing**: Handles complex command chains with pipe operators and redirections
- **Security Analysis**: Detects dangerous patterns and provides safety warnings
- **Auto-escaping**: Automatically handles special characters for improved parsing
- **RESTful API**: HTTP server mode for integration with other tools and applications
- **Extensible Knowledge Base**: Support for custom command definitions and flag descriptions

## Installation

### System-wide Installation (Recommended)

```bash
sudo ./setup.sh
```

This installs the application to `/opt/explain-cli` and creates a system-wide executable at `/usr/local/bin/explain-cli`.

### User Installation

```bash
mkdir -p ~/.local/opt ~/.local/bin
cp -r . ~/.local/opt/explain-cli
printf '#!/bin/bash\nPYTHONPATH="$HOME/.local/opt/explain-cli" exec python3 "$HOME/.local/opt/explain-cli/cli.py" "$@"\n' > ~/.local/bin/explain-cli
chmod +x ~/.local/bin/explain-cli
```

Ensure `~/.local/bin` is in your PATH.

## Usage

### Command Line Interface

```bash
explain-cli "command to explain"
```

**Examples:**
```bash
# File operations with flag explanations
explain-cli "find /var/log -name '*.log' -mtime +30 -exec rm {} \;"

# Network analysis with security warnings
explain-cli "nmap -sC -sV -p- target.com"

# Complex pipeline processing
explain-cli "ps aux | grep python | awk '{print \$1, \$2, \$11}' | sort -u"
```

### API Server Mode

Start the HTTP API server for programmatic access:

```bash
explain-cli --api --port 8080
```

**API Usage:**
```bash
# Explain a command via HTTP
curl -X POST http://localhost:8080/explain \
  -H 'Content-Type: application/json' \
  -d '{"command": "ls -la"}'

# With options
curl -X POST http://localhost:8080/explain \
  -H 'Content-Type: application/json' \
  -d '{"command": "grep \"error\" /var/log", "no_auto_escape": false}'
```

### Command Options

```bash
explain-cli --help                    # Show help and examples
explain-cli --no-color "command"      # Disable colored output
explain-cli --no-auto-escape "cmd"    # Disable automatic escaping
explain-cli --api --host 0.0.0.0      # Start API server on all interfaces
```

## Project Structure

```
explain-cli/
├── cli.py                    # Main CLI entry point and command analysis logic
├── setup.sh                  # Installation script
└── src/
    ├── parser.py             # Shell-safe command tokenization
    ├── knowledge_base.py     # Built-in command definitions and flags
    ├── man_parser.py         # Dynamic parsing of man pages and help output
    ├── danger_detector.py    # Safety pattern detection and warnings
    ├── custom_commands.py    # Custom knowledge base management
    ├── regex_explainer.py    # Regular expression pattern explanation
    └── signals.py            # Signal handling for kill-like commands
```

## Custom Commands

Extend the knowledge base with custom command definitions:

```bash
explain-cli --add-command <command> <description> <danger_level> <flags>
```

**Example:**
```bash
explain-cli --add-command mytool "Custom utility" medium "-v:verbose mode, --config:config file path"
```

**Parameters:**
- `command`: Command name
- `description`: Human-readable description  
- `danger_level`: `low`, `medium`, `high`, `critical`, or `none`
- `flags`: Comma-separated `flag:description` pairs, or `none`

## Requirements

- Linux operating system
- Python 3.8 or higher

## License

MIT License