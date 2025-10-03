#!/bin/bash

# This script sets up the explain-cli tool for easy access.

# Ensure the script is run with root privileges for copying to /usr/local/bin
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo: sudo ./setup.sh"
    exit 1
fi

SOURCE_DIR="$(dirname "$0")"
INSTALL_DIR="/usr/local/bin"
SCRIPT_NAME="explain-cli"

# Copy the main script to the install directory
cp "$SOURCE_DIR/cli.py" "$INSTALL_DIR/$SCRIPT_NAME"

# Make the script executable
chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

# Create a symbolic link for the src directory if needed (for imports)
# This assumes the src directory is relative to the cli.py script
# A more robust solution might involve packaging or setting PYTHONPATH
# For simplicity, we'll assume the user runs from the project root or handles PYTHONPATH

# Optional: Create a wrapper script if direct execution of cli.py causes import issues
# This is a more robust way to handle imports when the script is moved
WRAPPER_SCRIPT_CONTENT="""#!/bin/bash
PYTHONPATH=\"$SOURCE_DIR\" python3 \"$INSTALL_DIR/$SCRIPT_NAME\" \"$@\"\n"""

# For now, we'll rely on the direct copy and hope imports work or user sets PYTHONPATH
# If imports fail, the wrapper script approach would be better.

echo "explain-cli has been installed to $INSTALL_DIR."
echo "You can now run it from anywhere using: $SCRIPT_NAME \"your_command_here\""
echo "To add custom commands: $SCRIPT_NAME --add-command <command> <description> <danger_level> <flags>"
