#!/bin/bash
#
# Logseq to Obsidian Migration
# Usage: ./migrate.sh <logseq-path> <obsidian-path> [options]
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 2 ]; then
    echo "Usage: ./migrate.sh <logseq-path> <obsidian-path> [options]"
    echo ""
    echo "Options:"
    echo "  --dry-run              Preview without writing files"
    echo "  --flatten              Flatten top-level bullets to paragraphs"
    echo "  --analyze-only         Only analyze, don't migrate"
    echo "  --help                 Show full help"
    echo ""
    echo "Examples:"
    echo "  ./migrate.sh ~/logseq ~/obsidian --dry-run"
    echo "  ./migrate.sh ~/logseq ~/obsidian --flatten"
    exit 1
fi

LOGSEQ_PATH="$1"
OBSIDIAN_PATH="$2"
shift 2

# Check for analyze-only flag
if [[ " $@ " =~ " --analyze-only " ]]; then
    echo "🔍 Analyzing Logseq graph..."
    python3 "$SCRIPT_DIR/scripts/analyze_graph.py" "$LOGSEQ_PATH"
    exit $?
fi

# Build migration command
CMD="python3 $SCRIPT_DIR/scripts/migrate.py $LOGSEQ_PATH --output $OBSIDIAN_PATH"

# Handle our simplified flags
for arg in "$@"; do
    case $arg in
        --flatten)
            CMD="$CMD --flatten-top-level"
            ;;
        --help)
            python3 "$SCRIPT_DIR/scripts/migrate.py" --help
            exit 0
            ;;
        *)
            CMD="$CMD $arg"
            ;;
    esac
done

# Run analysis first
echo "🔍 Analyzing Logseq graph..."
python3 "$SCRIPT_DIR/scripts/analyze_graph.py" "$LOGSEQ_PATH"
echo ""

# Run migration
echo "🚀 Starting migration..."
$CMD
