# Explain CLI

A command-line tool that provides human-readable explanations of shell commands, with built-in safety warnings and support for complex command structures including pipelines, redirections, and flag combinations.

## Features

- **Command Analysis**: Explains common Unix utilities, their flags, and arguments
- **Pipeline Support**: Breaks down complex command chains with pipe operators
- **Dynamic Parsing**: Automatically extracts flag information from man pages and help output
- **Safety Warnings**: Detects potentially dangerous patterns and sensitive file operations
- **Custom Commands**: Extensible knowledge base for adding custom command definitions
- **Redirection Handling**: Identifies and explains output redirections with overwrite warnings

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

```bash
explain-cli "command to explain"
```

### Examples

```bash
# Basic command with flags
explain-cli "ls -la /tmp"

# Pipeline with multiple commands
explain-cli "ps aux | grep python | head -5"

# Network scanning with safety warnings
explain-cli "nmap -sC -sV target.com"
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

Add custom command definitions to extend the built-in knowledge base:

```bash
explain-cli --add-command <command> <description> <danger_level> <flags>
```

### Parameters

- `command`: Command name
- `description`: Human-readable description
- `danger_level`: `low`, `medium`, `high`, `critical`, or `none`
- `flags`: Comma-separated `flag:description` pairs, or `none`

### Example

```bash
explain-cli --add-command mytool "Custom utility" medium "-v:verbose mode, --config:config file path"
```

## Requirements

- Linux operating system
- Python 3.8 or higher

## License

MIT License