#!/usr/bin/env python3
import argparse
from src.parser import tokenize_command
from src.knowledge_base import COMMAND_KNOWLEDGE_BASE
from src.danger_detector import detect_dangerous_patterns
from src.man_parser import get_command_help, get_command_details
from src.custom_commands import load_custom_commands, add_custom_command
from src.regex_explainer import looks_like_regex, explain_regex

def _analyze_single_command(tokens, knowledge_base):
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

        flags = command_info.get("flags", {})
        used_flags = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                name, eq, val = arg.partition('=')
                if name in flags:
                    if eq and val:
                        explanation.append(f"  {name}: {flags[name]} (value: {val})")
                    elif i + 1 < len(args) and not args[i+1].startswith('-'):
                        explanation.append(f"  {name}: {flags[name]} (value: {args[i+1]})")
                        i += 1
                    else:
                        explanation.append(f"  {name}: {flags[name]}")
            elif arg.startswith("-") and len(arg) > 2:
                for char in arg[1:]:
                    flag = f"-{char}"
                    if flag in flags:
                        explanation.append(f"  {flag}: {flags[flag]}")
            elif arg in flags:
                # Short flag possibly with a following value
                if i + 1 < len(args) and not args[i+1].startswith('-'):
                    explanation.append(f"  {arg}: {flags[arg]} (value: {args[i+1]})")
                    i += 1
                else:
                    explanation.append(f"  {arg}: {flags[arg]}")
            i += 1
    else:
        details = get_command_details(command)
        if details.get("summary"):
            explanation.append(details["summary"])
        flags = details.get("flags", {})
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                name, eq, val = arg.partition('=')
                if name in flags:
                    if eq and val:
                        explanation.append(f"  {name}: {flags[name]} (value: {val})")
                    elif i + 1 < len(args) and not args[i+1].startswith('-'):
                        explanation.append(f"  {name}: {flags[name]} (value: {args[i+1]})")
                        i += 1
                    else:
                        explanation.append(f"  {name}: {flags[name]}")
            elif arg.startswith("-") and len(arg) > 2:
                for char in arg[1:]:
                    flag = f"-{char}"
                    if flag in flags:
                        explanation.append(f"  {flag}: {flags[flag]}")
            elif arg in flags:
                if i + 1 < len(args) and not args[i+1].startswith('-'):
                    explanation.append(f"  {arg}: {flags[arg]} (value: {args[i+1]})")
                    i += 1
                else:
                    explanation.append(f"  {arg}: {flags[arg]}")
            i += 1

    # Remove values already consumed by flags
    consumed = set()
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith('--'):
            name, eq, val = arg.partition('=')
            if eq and val:
                pass
            elif i + 1 < len(args) and not args[i+1].startswith('-'):
                consumed.add(i+1)
                i += 1
        elif arg.startswith('-') and len(arg) == 2:
            if i + 1 < len(args) and not args[i+1].startswith('-'):
                consumed.add(i+1)
                i += 1
        i += 1
    positional_args = [arg for idx, arg in enumerate(args) if idx not in consumed and not arg.startswith("-")]
    if command == "grep" and positional_args:
        explanation.append(f"  pattern: {positional_args[0]}")
        if looks_like_regex(positional_args[0]):
            explanation.append(f"  regex: {explain_regex(positional_args[0])}")
        if len(positional_args) > 1:
            explanation.append(f"  files: {', '.join(positional_args[1:])}")
    elif positional_args:
        explanation.append(f"Arguments: {', '.join(positional_args)}")
        # Add regex explanations for any arg that looks like a regex
        for arg in positional_args:
            if looks_like_regex(arg):
                explanation.append(f"  regex: {explain_regex(arg)}")

    return explanation, warnings


def analyze_command(tokens, knowledge_base):
    segments = []
    current = []
    for tok in tokens:
        if tok == '|':
            if current:
                segments.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        segments.append(current)

    all_explanations = []
    all_warnings = []
    for segment in segments:
        exp, warns = _analyze_single_command(segment, knowledge_base)
        all_explanations.extend(exp)
        all_warnings.extend(warns)
    # Removed global regex scan to avoid false positives on paths/IPs
    return all_explanations, all_warnings

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
