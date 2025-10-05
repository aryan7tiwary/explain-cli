import shlex
import re

def tokenize_command(command_string):
    """Tokenize command string while preserving awk field references and other special constructs."""
    
    # First, protect awk field references ($1, $2, etc.) from shell parsing
    # Replace $N with a placeholder that we'll restore later
    awk_placeholders = {}
    placeholder_counter = 0
    
    # Find and protect awk field references
    def protect_awk_field(match):
        nonlocal placeholder_counter
        placeholder = f"__AWK_FIELD_{placeholder_counter}__"
        awk_placeholders[placeholder] = match.group(0)
        placeholder_counter += 1
        return placeholder
    
    # Protect awk field references in the command string
    protected_string = re.sub(r'\$\d+', protect_awk_field, command_string)
    
    # Now use shlex to parse the protected string
    try:
        tokens = shlex.split(protected_string)
    except ValueError:
        # If shlex fails, fall back to simple whitespace splitting
        tokens = protected_string.split()
    
    # Restore the awk field references
    restored_tokens = []
    for token in tokens:
        for placeholder, original in awk_placeholders.items():
            token = token.replace(placeholder, original)
        restored_tokens.append(token)
    
    return restored_tokens
