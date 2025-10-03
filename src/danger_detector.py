def detect_dangerous_patterns(command_string, tokens):
    warnings = []
    if "rm" in tokens and "-rf" in tokens and "/" in tokens:
        # A more robust check for `rm -rf /` is needed here.
        # For now, this is a simple check.
        warnings.append("The command 'rm -rf /' will delete all files on your system.")

    # Check for downloading and executing scripts
    if any(cmd in tokens for cmd in ["curl", "wget"]):
        if "|" in command_string and any(shell in tokens for shell in ["bash", "sh"]):
            warnings.append("Downloading and executing a script from the internet can be dangerous.")

    if ">" in tokens and "/dev/null" in tokens:
        warnings.append("Redirecting output to /dev/null will hide all output and errors.")

    if ":(){ :|:& };:" in command_string:
        warnings.append("This is a fork bomb and will likely crash your system.")

    return warnings
