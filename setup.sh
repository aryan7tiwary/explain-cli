#!/bin/bash

# This script installs explain-cli system-wide with a stable app dir and wrapper.

# Ensure the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo: sudo ./setup.sh"
    exit 1
fi

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/usr/local/bin"
APP_DIR="/opt/explain-cli"
SCRIPT_NAME="explain-cli"

# Recreate application directory to avoid nested copies (e.g., src/src)
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"

# Copy application files fresh
cp -f "$SOURCE_DIR/cli.py" "$APP_DIR/cli.py"
cp -a "$SOURCE_DIR/src" "$APP_DIR/"

# Create/overwrite wrapper script in /usr/local/bin
cat > "$INSTALL_DIR/$SCRIPT_NAME" << 'EOF'
#!/bin/bash
PYTHONPATH="/opt/explain-cli" exec python3 "/opt/explain-cli/cli.py" "$@"
EOF

# Make the wrapper executable
chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

echo "explain-cli has been installed."
echo "Wrapper: $INSTALL_DIR/$SCRIPT_NAME"
echo "App dir: $APP_DIR"
echo "Run from anywhere: $SCRIPT_NAME --help"
