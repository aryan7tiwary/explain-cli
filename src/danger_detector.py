def detect_dangerous_patterns(command_string, tokens):
    warnings = []
    if "rm" in tokens and "-rf" in tokens and "/" in tokens:
        # A more robust check for `rm -rf /` is needed here.
        # For now, this is a simple check.
        warnings.append("The command 'rm -rf /' will delete all files on your system.")

    # Check for downloading and executing scripts
    if any(cmd in tokens for cmd in ["curl", "wget"]):
        if "|" in command_string and any(shell in tokens for shell in ["bash", "sh", "python", "python3", "perl", "ruby", "node", "php"]):
            warnings.append("Downloading and executing a script from the internet can be dangerous.")
        
        # Check for specific malicious patterns
        if "|" in command_string:
            # Look for patterns like "wget url | python3 script.py"
            for i, token in enumerate(tokens):
                if token in ["curl", "wget"] and i + 1 < len(tokens):
                    url = tokens[i + 1]
                    if any(ext in url.lower() for ext in [".py", ".sh", ".bash", ".pl", ".rb", ".js", ".php"]):
                        warnings.append(f"WARNING: This command downloads a script file ({url}) and pipes it to an interpreter. This could execute malicious code!")
                    elif "attacker" in url.lower() or "malware" in url.lower() or "evil" in url.lower():
                        warnings.append(f"WARNING: This command downloads from a suspicious URL ({url}) and pipes it to an interpreter. This is likely malicious!")

    if ">" in tokens and "/dev/null" in tokens:
        warnings.append("Redirecting output to /dev/null will hide all output and errors.")

    if ":(){ :|:& };:" in command_string:
        warnings.append("This is a fork bomb and will likely crash your system.")

    # Sensitive file reads
    sensitive_paths = {
        "/etc/shadow": "Contains password hashes for system users (highly sensitive)",
        "/etc/passwd": "Contains user account information (less sensitive but still private)",
        "~/.ssh/id_rsa": "Private SSH key (highly sensitive)",
        "~/.ssh/id_ed25519": "Private SSH key (highly sensitive)",
        "/root/.ssh/id_rsa": "Root's private SSH key (highly sensitive)",
    }
    read_commands = {"cat", "less", "more", "head", "tail", "sed", "awk", "grep", "cut"}
    if any(cmd in tokens for cmd in read_commands):
        for tok in tokens:
            if tok in sensitive_paths:
                warnings.append(f"Reading sensitive file: {tok}. {sensitive_paths[tok]}.")

    return warnings
