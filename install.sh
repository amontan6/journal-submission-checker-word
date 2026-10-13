#!/bin/sh
# Install the journal-submission-checker-word agent for Claude Code.
# Copies the agent to <claude dir>/agents/ and the extractor to
# <claude dir>/checker-word-kit/, then points the agent at that extractor.
set -eu

KIT=$(cd "$(dirname "$0")" && pwd)
CLAUDE_DIR=${CLAUDE_CONFIG_DIR:-$HOME/.claude}

mkdir -p "$CLAUDE_DIR/agents" "$CLAUDE_DIR/checker-word-kit"
cp "$KIT/docx_extract.py" "$CLAUDE_DIR/checker-word-kit/"
sed "s|~/.claude/checker-word-kit|$CLAUDE_DIR/checker-word-kit|g" \
    "$KIT/journal-submission-checker-word.md" \
    > "$CLAUDE_DIR/agents/journal-submission-checker-word.md"

echo "Installed:"
echo "  agent     $CLAUDE_DIR/agents/journal-submission-checker-word.md"
echo "  extractor $CLAUDE_DIR/checker-word-kit/docx_extract.py"
echo "Restart Claude Code, then: @agent-journal-submission-checker-word check @paper.docx"
