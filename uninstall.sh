#!/bin/sh
# Git-Gud AI: Uninstaller
# Usage:
#   ./uninstall.sh                  # Uninstalls from current git repo
#   ./uninstall.sh /path/to/repo    # Uninstalls from specified git repo
#   ./uninstall.sh --global         # Removes global git config hook

set -e

TARGET_ARG="$1"

echo "⚖️  Uninstalling Git-Gud AI..."

uninstall_from_repo() {
    REPO_PATH="$1"
    GIT_DIR="$(git -C "$REPO_PATH" rev-parse --git-dir 2>/dev/null || true)"

    if [ -z "$GIT_DIR" ]; then
        echo "❌ Error: '$REPO_PATH' is not a git repository." >&2
        exit 1
    fi

    case "$GIT_DIR" in
        /*) HOOKS_DIR="$GIT_DIR/hooks" ;;
        *)  HOOKS_DIR="$REPO_PATH/$GIT_DIR/hooks" ;;
    esac

    DEST_HOOK="$HOOKS_DIR/pre-commit"
    LEGACY_HOOK="$HOOKS_DIR/pre-commit.legacy"

    # Remove bundled module
    rm -rf "$HOOKS_DIR/gitgud"

    if [ -f "$DEST_HOOK" ]; then
        # Check if legacy hook exists to restore
        if [ -f "$LEGACY_HOOK" ]; then
            echo "🔄 Restoring original pre-commit hook from: $LEGACY_HOOK"
            mv "$LEGACY_HOOK" "$DEST_HOOK"
            chmod +x "$DEST_HOOK" 2>/dev/null || true
            echo "✅ Restored previous pre-commit hook."
        else
            rm -f "$DEST_HOOK"
            echo "✅ Removed Git-Gud pre-commit hook from: $DEST_HOOK"
        fi
    else
        echo "ℹ️  No pre-commit hook found in $HOOKS_DIR."
    fi
}

uninstall_global() {
    GLOBAL_DIR="$HOME/.gitgud-hooks"
    rm -rf "$GLOBAL_DIR"
    git config --global --unset core.hooksPath 2>/dev/null || true
    echo "✅ Removed global Git-Gud hooks and unset git core.hooksPath."
}

if [ "$TARGET_ARG" = "--global" ]; then
    uninstall_global
elif [ -n "$TARGET_ARG" ]; then
    uninstall_from_repo "$TARGET_ARG"
else
    uninstall_from_repo "."
fi
