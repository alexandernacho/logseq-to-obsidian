# Logseq to Obsidian Migration Tool

Migrate your Logseq graph to a clean Obsidian vault. Works best with [Claude Code](https://claude.com/claude-code) - Claude analyzes your graph, asks the right questions, and handles the conversion.

## Quick Start with Claude Code

The easiest way to migrate is using Claude Code directly in your Logseq graph:

```bash
cd /path/to/your/logseq/graph
claude
```

Then just ask:

> "Migrate this graph to Obsidian"

Claude will:
1. Analyze your graph structure and detect what features you're using
2. Ask only the relevant preference questions
3. Save your preferences to `.logseq-to-obsidian/config.json`
4. Run a dry-run preview
5. Execute the migration after your confirmation

Your config is saved, so you can re-run or tweak settings later without answering questions again.

## What Gets Converted

| Logseq Feature | Obsidian Result |
|----------------|-----------------|
| `property:: value` | YAML frontmatter |
| `collapsed:: true` | Removed |
| `#+BEGIN_TIP/QUOTE/WARNING` | `> [!tip]` callouts |
| `logseq.order-list-type:: number` | `1. 2. 3.` markdown lists |
| `id:: uuid` block IDs | `^block-id` at line end |
| `((uuid))` block references | Flagged with `<!-- TODO -->` |
| Image sizing `{:height :width}` | Removed |
| Journal `2025_04_03.md` | `2025-04-03.md` in `Daily/` |
| `Parent/Child` namespaces | Optional folder hierarchy |
| Task states (TODO/DONE/etc) | Checkbox syntax `- [ ]` / `- [x]` |
| `:LOGBOOK:` blocks | Removed |
| `{{embed [[Page]]}}` | `![[Page]]` |

## Installation

### Requirements
- Python 3.8+
- Node.js 14+ (optional, for npm installation)

### For Claude Code Users

Clone this repo into your Logseq graph directory:

```bash
cd /path/to/your/logseq/graph
git clone https://github.com/YOUR_USERNAME/logseq-to-obsidian.git .logseq-migration
cd .logseq-migration
```

Then start Claude Code from the cloned directory:

```bash
claude
```

And ask Claude to migrate:

> "Migrate this graph to Obsidian"

Claude will automatically discover and use the `logseq-to-obsidian` skill.

**Alternative: Install globally for CLI access:**

```bash
npm install -g logseq-to-obsidian
```

## Config File

After running with Claude Code, your preferences are saved to `.logseq-to-obsidian/config.json`:

```json
{
  "version": 1,
  "source": "/path/to/logseq/graph",
  "output": "/path/to/obsidian/vault",
  "preferences": {
    "flattenTopLevel": false,
    "namespacesToFolders": false,
    "blockRefs": "flag",
    "journalsFolder": "Daily"
  }
}
```

### Re-running Migrations

Edit the config and re-run without going through questions:

```bash
# Via Claude Code
claude
> "Re-run the migration with my saved config"

# Or directly
python3 scripts/migrate.py --config .logseq-to-obsidian/config.json
```

## CLI Usage (Advanced)

For power users who prefer command-line control:

### With Config File

```bash
# Using saved config
logseq-to-obsidian --config .logseq-to-obsidian/config.json

# Dry run first
logseq-to-obsidian --config .logseq-to-obsidian/config.json --dry-run
```

### Direct CLI Mode

```bash
# Analyze graph
logseq-to-obsidian analyze ~/logseq

# Dry run
logseq-to-obsidian ~/logseq ~/obsidian --dry-run

# Full migration with options
logseq-to-obsidian ~/logseq ~/obsidian \
  --flatten \
  --namespaces-to-folders \
  --journals-folder "Daily" \
  --verbose
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--config`, `-c` | Path to config JSON file | - |
| `--dry-run` | Preview without writing files | Off |
| `--flatten` | Convert top-level bullets to paragraphs | Off |
| `--journals-folder` | Folder name for daily notes | `Daily` |
| `--namespaces-to-folders` | Convert `A/B` pages to folder hierarchy | Off |
| `--block-refs [flag\|remove]` | How to handle block references | `flag` |
| `--verbose`, `-v` | Show detailed progress | Off |

## Opening in Obsidian

After migration:

1. Open Obsidian
2. Click **"Open folder as vault"**
3. Select your output folder
4. Done!

### Recommended Plugins

For Logseq refugees, install these community plugins:

| Plugin | Purpose |
|--------|---------|
| **Calendar** | Visual calendar sidebar for daily notes |
| **Periodic Notes** | Configure daily/weekly/monthly notes |
| **Outliner** | Fold bullets, move items (Logseq-like feel) |
| **Dataview** | Query your notes (replaces Logseq queries) |

## Known Limitations

- **Block references**: Can be flagged but not fully converted (requires building a block-to-page index)
- **Logseq queries**: Flagged for manual conversion to Dataview syntax
- **Flashcards**: Not converted (Obsidian uses different flashcard plugins)
- **Excalidraw**: Files are copied but may need plugin setup in Obsidian

## Contributing

PRs welcome! Some ideas:

- [ ] Full block reference conversion with page mapping
- [ ] Logseq query → Dataview query conversion
- [ ] Excalidraw compatibility
- [ ] Progress bar for large graphs

## License

MIT License - see [LICENSE](LICENSE)
