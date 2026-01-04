# Logseq to Obsidian Migration Tool

This project provides a skill for migrating Logseq graphs to Obsidian vaults.

## Project Structure

- `scripts/analyze_graph.py` - Analyzes Logseq graph for patterns
- `scripts/migrate.py` - Core migration engine
- `references/patterns.md` - Logseq → Obsidian syntax mappings
- `.claude/skills/logseq-to-obsidian/` - Migration skill (auto-discovered)

The `logseq-to-obsidian` skill will be automatically triggered when users ask about migrating from Logseq to Obsidian.
