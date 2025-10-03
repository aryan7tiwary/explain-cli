# Explain CLI

Explain CLI is a Linux-focused tool that takes a shell command and produces a concise, human-readable explanation along with safety warnings. It understands common Unix utilities, pipelines, redirections, flags, and several command-specific argument formats.

## Requirements

- Linux
- Python 3.8+

## Installation

System-wide (recommended):

```bash
cd /home/aryan/Desktop/explain-cli
sudo ./setup.sh
```

This installs the app under `/opt/explain-cli` and a wrapper at `/usr/local/bin/explain-cli`.

User-only (no sudo) alternative:

```bash
mkdir -p ~/.local/opt ~/.local/bin
cp -r /home/aryan/Desktop/explain-cli ~/.local/opt/explain-cli
printf '#!/bin/bash\nPYTHONPATH="$HOME/.local/opt/explain-cli" exec python3 "$HOME/.local/opt/explain-cli/cli.py" "$@"\n' > ~/.local/bin/explain-cli
chmod +x ~/.local/bin/explain-cli
echo 'Ensure ~/.local/bin is on your PATH'
```

## Usage

From anywhere after installation:

```bash
explain-cli "your command here"
```

Or, run directly from the repository during development:

```bash
python3 cli.py "your command here"
```

### Quoting guidance

- Prefer single quotes around the whole command when it contains spaces or quotes:
  - `explain-cli 'echo "Hello World"'`
- To include a literal single quote inside single quotes, use the portable sequence `'
"'"'
` (close, insert a single quote, reopen):
  - `explain-cli 'echo '\''He said "hi"'\'''`

## Key capabilities

- Command breakdown: plain-English summaries for many common commands
- Pipelines: explains each stage (`cmd1 | cmd2 | cmd3`)
- Redirections: identifies `>`, `>>`, `2>`, `2>>` and warns on overwrite
- Flags: explains only the flags you used (supports combined short flags like `-la` and `--flag=value`)
- Unknown commands: parses `--help` and `man` to summarize and infer flags
- Regex explanations: for `grep` patterns only
- chmod: decodes octal modes (e.g., `755`) into owner/group/others permissions
- chown: parses `owner[:group] target...` and detects numeric IDs
- Signals: explains `kill`/`killall` signal flags (`-9`, `-SIGKILL`, `-s SIGTERM`)
- Safety warnings: highlights sensitive file reads (e.g., `/etc/shadow`, SSH keys), risky constructs

## Examples

```bash
# Basic command
explain-cli "ls -la"

# Pipeline + regex
explain-cli "ls -l | grep '^-'"

# Redirection with overwrite warning
explain-cli "echo error > logfile.txt"

# chmod (octal mode)
explain-cli "chmod 755 script.sh"

# chown (owner:group)
explain-cli "chown root:wheel /var/www/index.html"

# kill with signal
explain-cli "kill -9 1234"

# Sensitive file read warning
explain-cli "cat /etc/shadow"
```

## Custom commands

You can extend the built-in knowledge base at runtime:

```bash
explain-cli --add-command <command> <description> <danger_level> <flags>
```

Arguments:

- `<command>`: Name of the command to add (e.g., `mycmd`).
- `<description>`: One-line summary that will appear in explanations.
- `<danger_level>`: One of `low`, `medium`, `high`, `critical`, or `none`.
- `<flags>`: Comma-separated list of `flag:description` pairs, or `none` if there are no flags.

Examples:

```bash
# No flags
explain-cli --add-command apropos "gives apt command for the description" none none

# With short flags
explain-cli --add-command mycmd "My custom tool" low "-a:Show all, -q:Quiet mode"

# With long flags (and values in explanations)
explain-cli --add-command fetcher "Download utility" medium "--url:Resource URL, --output:Output file path"
```

Notes:

- Flags must be provided as `flag:description`, separated by commas. Whitespace is ignored.
- Use `none` (or `null`/`nil`/`-`) for `<flags>` to add a command without flags.
- Custom entries are stored at `src/custom_knowledge_base.json` next to the module, so they work both locally and with the system-wide install.

Note: the custom knowledge base path is defined in `src/custom_commands.py`.

## Troubleshooting

- Command not found after install:
  - Ensure `/usr/local/bin` is on your `PATH`
  - `which explain-cli` and `type -a explain-cli`
  - Clear shell cache with `hash -r`

- Imports fail when running globally:
  - Re-run the installer: `sudo ./setup.sh`
  - Confirm files exist: `ls -l /opt/explain-cli /opt/explain-cli/src`

- Quotes inside the input command:
  - Use single quotes around the whole string and escape inner single quotes with `'
"'"'
`
  - For complex cases, pass the command via a heredoc into a variable, then call `explain-cli "$cmd"`

## Project structure

- `cli.py`: CLI entry point and explanation logic
- `src/parser.py`: Shell-safe tokenization
- `src/knowledge_base.py`: Built-in command summaries and flags
- `src/man_parser.py`: Parses `--help` and `man` for unknown commands
- `src/danger_detector.py`: Heuristics for dangerous patterns and sensitive paths
- `src/regex_explainer.py`: Heuristic regex explainer (used with grep)
- `src/signals.py`: Signal mapping and explanations for kill-like commands
- `src/custom_commands.py`: Custom knowledge base loader/writer

## License

MIT License
