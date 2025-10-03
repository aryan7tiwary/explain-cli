import json

KNOWLEDGE_BASE_PATH = "C:\\Users\\Aryan\\Desktop\\SafeShell\\explain-cli\\src\\custom_knowledge_base.json"

def load_custom_commands():
    """Loads the custom knowledge base from the JSON file."""
    try:
        with open(KNOWLEDGE_BASE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def add_custom_command(command, description, danger_level, flags):
    """Adds a new command to the custom knowledge base."""
    custom_commands = load_custom_commands()
    custom_commands[command] = {
        "description": description,
        "danger_level": danger_level,
        "flags": flags
    }
    with open(KNOWLEDGE_BASE_PATH, "w") as f:
        json.dump(custom_commands, f, indent=4)
