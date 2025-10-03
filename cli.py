#!/usr/bin/env python3
import argparse
from src.parser import tokenize_command
from src.knowledge_base import COMMAND_KNOWLEDGE_BASE
from src.danger_detector import detect_dangerous_patterns
from src.man_parser import get_command_help
from src.custom_commands import load_custom_commands, add_custom_command

def analyze_command(tokens, knowledge_base):
    explanation = []
    warnings = []

    if not tokens:
        return explanation, warnings

    command = tokens[0]
    args = tokens[1:]

    if command in knowledge_base:
        command_info = knowledge_base[command]
        explanation.append(f"{command}: {command_info['description']}")
        if command_info['danger_level'] in ["high", "critical"]:
            warnings.append(f"The command '{command}' is considered {command_info['danger_level']} risk.")

        # Explain flags
        flags = command_info.get("flags", {})
        for arg in args:
            if arg in flags:
                explanation.append(f"  {arg}: {flags[arg]}")
            elif arg.startswith("-"):
                # Handle combined flags like -la
                for char in arg[1:]:
                    flag = f"-{char}"
                    if flag in flags:
                        explanation.append(f"  {flag}: {flags[flag]}")

    else:
        explanation.append(get_command_help(command))

    # Separate remaining arguments
    remaining_args = [arg for arg in args if not arg.startswith("-")]
    if remaining_args:
        explanation.append(f"Arguments: {', '.join(remaining_args)}")

    return explanation, warnings

def main():
    parser = argparse.ArgumentParser(description="Explains a shell command.")
    parser.add_argument("command_string", nargs='?', help="The shell command to explain.")
    parser.add_argument("--add-command", nargs=4, help="Add a new command to the custom knowledge base. Usage: --add-command <command> <description> <danger_level> <flags>", metavar=("COMMAND", "DESCRIPTION", "DANGER_LEVEL", "FLAGS"))

    args = parser.parse_args()

    custom_commands = load_custom_commands()
    knowledge_base = {**COMMAND_KNOWLEDGE_BASE, **custom_commands}

    if args.add_command:
        command, description, danger_level, flags_str = args.add_command
        # a simple way to parse flags, assuming "-f:description, -g:description"
        flags = dict(item.replace("'", "").split(":") for item in flags_str.split(",")) if flags_str else {}
        add_custom_command(command, description, danger_level, flags)
        print(f"Command '{command}' added to the custom knowledge base.")
        return

    if not args.command_string:
        parser.print_help()
        return

    tokens = tokenize_command(args.command_string)
    
    explanation, analysis_warnings = analyze_command(tokens, knowledge_base)
    danger_warnings = detect_dangerous_patterns(args.command_string, tokens)

    all_warnings = analysis_warnings + danger_warnings

    print(f"Command: {args.command_string}")
    if explanation:
        print(f"\nExplanation:\n" + "\n".join(explanation))
    if all_warnings:
        print(f"\nWarnings:\n" + "\n".join(all_warnings))

if __name__ == "__main__":
    main()
