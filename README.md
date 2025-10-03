# Explain CLI

A Linux-only CLI tool that takes a shell command as input, explains it in plain English, and warns if it is dangerous.

## Usage

```bash
python cli.py "your_command_here"
```

## Features

- **Command Breakdown**: Human-readable explanation of each part of the command.
- **Safety Assessment**: Warnings for potentially dangerous commands.
- **Handles Complex Commands**: Parses pipelines, redirections, and compound commands.
- **Knowledge Base**: Contains a built-in dictionary of common Linux commands.
- **Unknown Command Resolution**: Fetches help for unknown commands using `man` or `--help`.

## Modules

- `cli.py`: The main entry point for the CLI tool.
- `parser.py`: Handles tokenizing and structuring the input command.
- `knowledge_base.py`: Contains the explanations for known commands.
- `danger_detector.py`: Detects dangerous patterns in commands.
- `man_parser.py`: Parses and summarizes `man` or `--help` output.
