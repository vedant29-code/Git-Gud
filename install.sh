#!/bin/sh
# Git-Gud AI: Installer
# Usage:
#   ./install.sh                  # Installs into current git repo
#   ./install.sh /path/to/repo    # Installs into specified git repo
#   ./install.sh --global         # Installs globally via git config --global core.hooksPath

set -e

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_ARG="$1"

echo "⚖️  Installing Git-Gud AI (The Pre-Commit Judge & Jury)..."

install_into_repo() {
    REPO_PATH="$1"
    GIT_DIR="$(git -C "$REPO_PATH" rev-parse --git-dir 2>/dev/null || true)"

    if [ -z "$GIT_DIR" ]; then
        echo "❌ Error: '$REPO_PATH' is not a git repository." >&2
        exit 1
    fi

    # Handle relative git-dir
    case "$GIT_DIR" in
        /*) HOOKS_DIR="$GIT_DIR/hooks" ;;
        *)  HOOKS_DIR="$REPO_PATH/$GIT_DIR/hooks" ;;
    esac

    mkdir -p "$HOOKS_DIR"
    DEST_HOOK="$HOOKS_DIR/pre-commit"

    # Check for existing hook
    if [ -f "$DEST_HOOK" ]; then
        if grep -q "Git-Gud AI" "$DEST_HOOK" 2>/dev/null; then
            echo "ℹ️  Git-Gud hook already installed in $HOOKS_DIR. Updating files..."
        else
            TIMESTAMP="$(date +%Y%m%d%H%M%S)"
            BACKUP_HOOK="$HOOKS_DIR/pre-commit.backup.$TIMESTAMP"
            LEGACY_HOOK="$HOOKS_DIR/pre-commit.legacy"

            echo "⚠️  Existing pre-commit hook detected."
            echo "   Creating backup: $BACKUP_HOOK"
            cp "$DEST_HOOK" "$BACKUP_HOOK"

            echo "   Chaining existing hook as: $LEGACY_HOOK"
            cp "$DEST_HOOK" "$LEGACY_HOOK"
            chmod +x "$LEGACY_HOOK" 2>/dev/null || true
        fi
    fi

    # Copy hook script
    cp "$SOURCE_DIR/hooks/pre-commit" "$DEST_HOOK"
    chmod +x "$DEST_HOOK" 2>/dev/null || true

    # Bundle gitgud python module into hooks directory for self-contained execution
    rm -rf "$HOOKS_DIR/gitgud"
    cp -r "$SOURCE_DIR/gitgud" "$HOOKS_DIR/gitgud"

    echo "✅ Successfully installed Git-Gud hook into: $DEST_HOOK"
    echo "💡 Ensure Ollama is running and model is pulled: 'ollama pull phi3'"
}

install_global() {
    GLOBAL_DIR="$HOME/.gitgud-hooks"
    mkdir -p "$GLOBAL_DIR"

    cp "$SOURCE_DIR/hooks/pre-commit" "$GLOBAL_DIR/pre-commit"
    chmod +x "$GLOBAL_DIR/pre-commit" 2>/dev/null || true

    rm -rf "$GLOBAL_DIR/gitgud"
    cp -r "$SOURCE_DIR/gitgud" "$GLOBAL_DIR/gitgud"

    git config --global core.hooksPath "$GLOBAL_DIR"

    echo "✅ Installed global hook directory: $GLOBAL_DIR"
    echo "   Configured: git config --global core.hooksPath '$GLOBAL_DIR'"
    echo "💡 Ensure Ollama is running and model is pulled: 'ollama pull phi3'"
}

if [ "$TARGET_ARG" = "--global" ]; then
    install_global
elif [ -n "$TARGET_ARG" ]; then
    install_into_repo "$TARGET_ARG"
else
    install_into_repo "."
fi
