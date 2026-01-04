#!/usr/bin/env python3
"""
Migrate a Logseq graph to Obsidian vault format.
Handles properties, admonitions, block references, journals, and more.
"""

import argparse
import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import json


class LogseqMigrator:
    """Handles migration of Logseq graph to Obsidian vault."""
    
    # Admonition type mappings
    ADMONITION_MAP = {
        "TIP": "tip",
        "NOTE": "note",
        "WARNING": "warning",
        "CAUTION": "caution",
        "IMPORTANT": "important",
        "QUOTE": "quote",
        "EXAMPLE": "example",
        "PINNED": "info",
        "CENTER": "note",
    }
    
    # Task state mappings
    TASK_MAP = {
        "TODO": "[ ]",
        "DOING": "[/]",
        "NOW": "[/]",
        "LATER": "[ ]",
        "DONE": "[x]",
        "WAITING": "[!]",
        "CANCELLED": "[-]",
    }
    
    def __init__(
        self,
        source_path: Path,
        output_path: Path,
        journals_folder: str = "Daily",
        flatten_top_level: bool = False,
        namespaces_to_folders: bool = False,
        block_refs_mode: str = "flag",  # flag, remove
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.source = source_path
        self.output = output_path
        self.journals_folder = journals_folder
        self.flatten_top_level = flatten_top_level
        self.namespaces_to_folders = namespaces_to_folders
        self.block_refs_mode = block_refs_mode
        self.dry_run = dry_run
        self.verbose = verbose
        
        self.stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "properties_converted": 0,
            "admonitions_converted": 0,
            "block_refs_flagged": 0,
            "tasks_converted": 0,
            "errors": [],
            "warnings": [],
        }
        
        # Build block ID to page mapping for block references
        self.block_id_map = {}
    
    def log(self, message: str, level: str = "info"):
        """Log a message if verbose mode is on."""
        if self.verbose or level in ["error", "warning"]:
            prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}.get(level, "")
            print(f"{prefix} {message}")
    
    def convert_properties_to_frontmatter(self, content: str) -> tuple[str, list]:
        """Convert Logseq properties to YAML frontmatter."""
        properties = {}
        lines = content.split("\n")
        new_lines = []
        in_content = False
        
        for line in lines:
            # Match property lines at the start of file (before content)
            prop_match = re.match(r'^([\w-]+)::\s*(.+)$', line)
            
            if prop_match and not in_content:
                key = prop_match.group(1)
                value = prop_match.group(2).strip()
                
                # Skip Logseq-specific properties we handle elsewhere
                if key in ["collapsed", "logseq.order-list-type", "id"]:
                    continue
                
                # Handle list values (comma-separated)
                if "," in value and key in ["tags", "alias", "aliases"]:
                    properties[key] = [v.strip() for v in value.split(",")]
                else:
                    properties[key] = value
            else:
                in_content = True
                new_lines.append(line)
        
        # Build frontmatter
        if properties:
            frontmatter_lines = ["---"]
            for key, value in properties.items():
                if isinstance(value, list):
                    frontmatter_lines.append(f"{key}:")
                    for item in value:
                        frontmatter_lines.append(f"  - {item}")
                else:
                    # Escape values that need quoting
                    if ":" in str(value) or str(value).startswith("["):
                        frontmatter_lines.append(f'{key}: "{value}"')
                    else:
                        frontmatter_lines.append(f"{key}: {value}")
            frontmatter_lines.append("---")
            frontmatter_lines.append("")
            
            return "\n".join(frontmatter_lines) + "\n".join(new_lines), list(properties.keys())
        
        return content, []
    
    def convert_admonitions(self, content: str) -> str:
        """Convert Logseq admonition blocks to Obsidian callouts."""
        
        def replace_admonition(match):
            full_match = match.group(0)
            # Get indent from the first line
            first_line = full_match.split('\n')[0]
            indent_match = re.match(r'^(\s*)', first_line)
            indent = indent_match.group(1) if indent_match else ""
            
            admon_type = match.group(1).upper()
            body = match.group(2)
            
            obsidian_type = self.ADMONITION_MAP.get(admon_type, "note")
            
            # Convert body lines to callout format
            body_lines = body.strip().split("\n")
            callout_lines = [f"{indent}> [!{obsidian_type}]"]
            for line in body_lines:
                # Strip common leading whitespace from body lines
                stripped = line.strip()
                if stripped:
                    callout_lines.append(f"{indent}> {stripped}")
            
            self.stats["admonitions_converted"] += 1
            return "\n".join(callout_lines)
        
        # Match #+BEGIN_TYPE ... #+END_TYPE blocks
        pattern = r'#\+BEGIN_(\w+)\s*\n(.*?)#\+END_\1'
        content = re.sub(pattern, replace_admonition, content, flags=re.DOTALL | re.IGNORECASE)
        
        return content
    
    def convert_numbered_lists(self, content: str) -> str:
        """Convert Logseq numbered lists to standard markdown."""
        lines = content.split("\n")
        new_lines = []
        list_counter = {}  # Track counters by indent level
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if next line has logseq.order-list-type:: number
            has_number_prop = False
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if "logseq.order-list-type:: number" in next_line:
                    has_number_prop = True
            
            if has_number_prop:
                # Get indent level
                indent_match = re.match(r'^(\t*)-\s+(.*)$', line)
                if indent_match:
                    indent = indent_match.group(1)
                    content_text = indent_match.group(2)
                    indent_level = len(indent)
                    
                    # Reset counter if indent level decreased
                    list_counter = {k: v for k, v in list_counter.items() if k <= indent_level}
                    
                    # Increment counter
                    list_counter[indent_level] = list_counter.get(indent_level, 0) + 1
                    
                    # Replace bullet with number
                    new_lines.append(f"{indent}{list_counter[indent_level]}. {content_text}")
                    i += 2  # Skip the property line
                    continue
            else:
                # Reset counter when we hit a non-numbered item
                bullet_match = re.match(r'^(\t*)-\s+', line)
                if bullet_match:
                    indent_level = len(bullet_match.group(1))
                    list_counter = {k: v for k, v in list_counter.items() if k < indent_level}
            
            # Skip standalone property lines
            if "logseq.order-list-type:: number" not in line:
                new_lines.append(line)
            i += 1
        
        return "\n".join(new_lines)
    
    def convert_block_ids(self, content: str) -> str:
        """Convert Logseq block IDs to Obsidian format."""
        # Match id:: uuid on its own line
        def replace_block_id(match):
            indent = match.group(1) or ""
            block_id = match.group(2)
            short_id = block_id[:8]  # Use first 8 chars
            return f" ^{short_id}"
        
        # Find lines ending with id:: uuid and move to end of previous content line
        lines = content.split("\n")
        new_lines = []
        
        for i, line in enumerate(lines):
            id_match = re.match(r'^(\s*)id::\s*([a-f0-9-]{36})$', line)
            if id_match and new_lines:
                # Append block ID to previous line
                short_id = id_match.group(2)[:8]
                new_lines[-1] = new_lines[-1].rstrip() + f" ^{short_id}"
            else:
                new_lines.append(line)
        
        return "\n".join(new_lines)
    
    def handle_block_references(self, content: str) -> str:
        """Handle Logseq block references ((uuid))."""
        if self.block_refs_mode == "remove":
            return re.sub(r'\(\([a-f0-9-]{36}\)\)', '', content)
        
        # Flag mode: wrap in comment
        def flag_ref(match):
            ref = match.group(0)
            self.stats["block_refs_flagged"] += 1
            return f"<!-- TODO: Fix block reference: {ref} -->"
        
        return re.sub(r'\(\([a-f0-9-]{36}\)\)', flag_ref, content)
    
    def convert_tasks(self, content: str) -> str:
        """Convert Logseq task states to Obsidian checkboxes."""
        for logseq_state, obsidian_state in self.TASK_MAP.items():
            # Match task at start of bullet
            pattern = rf'^(\s*-\s+){logseq_state}\s+'
            replacement = rf'\1{obsidian_state} '
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            # Count conversions (approximate)
            if logseq_state in content:
                self.stats["tasks_converted"] += 1
        
        return content
    
    def remove_collapsed_property(self, content: str) -> str:
        """Remove collapsed:: true lines and malformed collapsed bullets."""
        lines = content.split('\n')
        filtered_lines = []
        for line in lines:
            # Skip lines that are just collapsed:: true (with any whitespace)
            if re.match(r'^\s*collapsed::\s*true\s*$', line):
                continue
            # Also skip bullets that just contain "collapsed:: true"
            if re.match(r'^\s*-\s+collapsed::\s*true\s*$', line):
                continue
            filtered_lines.append(line)
        return '\n'.join(filtered_lines)
    
    def remove_logbook_blocks(self, content: str) -> str:
        """Remove :LOGBOOK: ... :END: blocks."""
        return re.sub(r':LOGBOOK:.*?:END:', '', content, flags=re.DOTALL)
    
    def clean_image_sizing(self, content: str) -> str:
        """Remove Logseq image sizing syntax."""
        return re.sub(r'\{:height\s+\d+,?\s*:width\s+\d+\}', '', content)
    
    def convert_embeds(self, content: str) -> str:
        """Convert Logseq embeds to Obsidian format."""
        # {{embed [[Page]]}} -> ![[Page]]
        content = re.sub(r'\{\{embed\s+\[\[([^\]]+)\]\]\}\}', r'![[\1]]', content)
        return content
    
    def flatten_top_level_bullets(self, content: str) -> str:
        """Convert top-level bullets to paragraphs and de-indent children."""
        lines = content.split("\n")
        new_lines = []
        in_flattened_section = False
        
        for line in lines:
            # Match top-level bullet (no indent)
            if re.match(r'^-\s+', line):
                # Remove the bullet, this becomes a "heading"
                text = re.sub(r'^-\s+', '', line)
                new_lines.append(text)
                new_lines.append("")  # Add blank line after
                in_flattened_section = True
            elif in_flattened_section and line.startswith('\t'):
                # De-indent by one level (remove first tab)
                new_lines.append(line[1:])
            else:
                new_lines.append(line)
        
        # Clean up multiple blank lines
        content = "\n".join(new_lines)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def convert_file(self, source_file: Path, dest_file: Path) -> bool:
        """Convert a single Logseq file to Obsidian format."""
        try:
            content = source_file.read_text(encoding="utf-8")
            original_content = content
            
            # Apply conversions in order
            content, props = self.convert_properties_to_frontmatter(content)
            if props:
                self.stats["properties_converted"] += len(props)
            
            content = self.convert_admonitions(content)
            content = self.convert_numbered_lists(content)
            content = self.convert_block_ids(content)
            content = self.handle_block_references(content)
            content = self.convert_tasks(content)
            content = self.remove_collapsed_property(content)
            content = self.remove_logbook_blocks(content)
            content = self.clean_image_sizing(content)
            content = self.convert_embeds(content)
            
            if self.flatten_top_level:
                content = self.flatten_top_level_bullets(content)
            
            # Clean up extra whitespace
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = content.strip() + "\n"
            
            if self.dry_run:
                if content != original_content:
                    self.log(f"Would convert: {source_file.name}", "info")
                return True
            
            # Write converted file
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(content, encoding="utf-8")
            self.stats["files_processed"] += 1
            
            return True
            
        except Exception as e:
            self.stats["errors"].append(f"{source_file}: {str(e)}")
            return False
    
    def convert_journal_filename(self, filename: str) -> str:
        """Convert journal filename from YYYY_MM_DD.md to YYYY-MM-DD.md."""
        # Match various date formats
        match = re.match(r'(\d{4})_(\d{2})_(\d{2})\.md$', filename)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}.md"
        return filename
    
    def process_namespace_path(self, filename: str) -> Path:
        """Convert namespace filename to folder path if enabled."""
        # Decode URL-encoded slashes
        decoded = filename.replace("%2F", "/").replace("%2f", "/")
        
        if self.namespaces_to_folders and "/" in decoded:
            # Split into path components
            parts = decoded.rsplit(".", 1)  # Separate extension
            if len(parts) == 2:
                path_parts = parts[0].split("/")
                return Path("/".join(path_parts[:-1])) / f"{path_parts[-1]}.{parts[1]}"
        
        # Just clean up the filename
        return Path(decoded.replace("/", "-"))
    
    def migrate(self) -> dict:
        """Run the full migration."""
        self.log(f"Starting migration from {self.source} to {self.output}")
        
        if not self.dry_run:
            self.output.mkdir(parents=True, exist_ok=True)
        
        # Process pages
        pages_dir = self.source / "pages"
        if pages_dir.exists():
            self.log(f"Processing pages...")
            for source_file in pages_dir.glob("*.md"):
                dest_name = self.process_namespace_path(source_file.name)
                dest_file = self.output / "pages" / dest_name
                self.convert_file(source_file, dest_file)
        
        # Process journals
        journals_dir = self.source / "journals"
        if journals_dir.exists():
            self.log(f"Processing journals...")
            for source_file in journals_dir.glob("*.md"):
                new_name = self.convert_journal_filename(source_file.name)
                dest_file = self.output / self.journals_folder / new_name
                self.convert_file(source_file, dest_file)
        
        # Copy assets
        assets_dir = self.source / "assets"
        if assets_dir.exists() and not self.dry_run:
            self.log(f"Copying assets...")
            dest_assets = self.output / "assets"
            if dest_assets.exists():
                shutil.rmtree(dest_assets)
            shutil.copytree(assets_dir, dest_assets)
        
        return self.stats


def load_config(config_path: Path) -> dict:
    """Load migration config from JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Validate required fields
    required = ['source', 'output']
    for field in required:
        if field not in config:
            raise ValueError(f"Missing required config field: '{field}'")

    # Resolve relative paths relative to config file's parent directory
    # Config is at .logseq-to-obsidian/config.json, so parent.parent is graph root
    config_dir = config_path.parent.parent

    if not Path(config['source']).is_absolute():
        config['source'] = str(config_dir / config['source'])
    if not Path(config['output']).is_absolute():
        config['output'] = str(config_dir / config['output'])

    return config


def config_to_migrator_args(config: dict) -> dict:
    """Convert config dict to LogseqMigrator constructor arguments."""
    prefs = config.get('preferences', {})

    return {
        'source_path': Path(config['source']),
        'output_path': Path(config['output']),
        'journals_folder': prefs.get('journalsFolder', 'Daily'),
        'flatten_top_level': prefs.get('flattenTopLevel', False),
        'namespaces_to_folders': prefs.get('namespacesToFolders', False),
        'block_refs_mode': prefs.get('blockRefs', 'flag'),
    }


def print_sample(source_path: Path, migrator: LogseqMigrator, num_samples: int = 2):
    """Print sample conversions for dry-run preview."""
    pages_dir = source_path / "pages"
    journals_dir = source_path / "journals"
    
    samples = []
    if pages_dir.exists():
        samples.extend(list(pages_dir.glob("*.md"))[:num_samples])
    if journals_dir.exists() and len(samples) < num_samples:
        samples.extend(list(journals_dir.glob("*.md"))[:num_samples - len(samples)])
    
    for sample_file in samples[:num_samples]:
        print(f"\n{'='*60}")
        print(f"📄 Sample: {sample_file.name}")
        print(f"{'='*60}")
        
        original = sample_file.read_text(encoding="utf-8")
        
        # Create a temporary migrator instance for this file
        temp_migrator = LogseqMigrator(
            source_path, Path("/tmp"),
            journals_folder=migrator.journals_folder,
            flatten_top_level=migrator.flatten_top_level,
            namespaces_to_folders=migrator.namespaces_to_folders,
            block_refs_mode=migrator.block_refs_mode,
            dry_run=True,
        )
        
        # Apply conversions
        content = original
        content, _ = temp_migrator.convert_properties_to_frontmatter(content)
        content = temp_migrator.convert_admonitions(content)
        content = temp_migrator.convert_numbered_lists(content)
        content = temp_migrator.convert_block_ids(content)
        content = temp_migrator.handle_block_references(content)
        content = temp_migrator.convert_tasks(content)
        content = temp_migrator.remove_collapsed_property(content)
        content = temp_migrator.remove_logbook_blocks(content)
        content = temp_migrator.clean_image_sizing(content)
        content = temp_migrator.convert_embeds(content)
        if temp_migrator.flatten_top_level:
            content = temp_migrator.flatten_top_level_bullets(content)
        content = re.sub(r'\n{3,}', '\n\n', content).strip()
        
        # Show first 40 lines of each
        orig_lines = original.split("\n")[:40]
        conv_lines = content.split("\n")[:40]
        
        print("\n📥 ORIGINAL (first 40 lines):")
        print("-" * 40)
        print("\n".join(orig_lines))
        if len(original.split("\n")) > 40:
            print(f"... ({len(original.split(chr(10)))} total lines)")
        
        print("\n📤 CONVERTED (first 40 lines):")
        print("-" * 40)
        print("\n".join(conv_lines))
        if len(content.split("\n")) > 40:
            print(f"... ({len(content.split(chr(10)))} total lines)")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Logseq graph to Obsidian vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using config file (recommended with Claude Code skill)
  python migrate.py --config .logseq-to-obsidian/config.json

  # Dry run to preview changes
  python migrate.py /path/to/logseq --output /path/to/obsidian --dry-run

  # Full migration with defaults
  python migrate.py /path/to/logseq --output /path/to/obsidian

  # Custom options
  python migrate.py /path/to/logseq --output /path/to/obsidian \\
      --journals-folder Daily --namespaces-to-folders --verbose
        """
    )

    # Config mode
    parser.add_argument("--config", "-c", type=Path, help="Path to config JSON file (overrides other options)")

    # CLI mode arguments
    parser.add_argument("source", type=Path, nargs="?", help="Path to Logseq graph folder")
    parser.add_argument("--output", "-o", type=Path, help="Path to output Obsidian vault")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--journals-folder", default="Daily", help="Folder name for journals (default: Daily)")
    parser.add_argument("--flatten-top-level", action="store_true", help="Convert top-level bullets to paragraphs")
    parser.add_argument("--namespaces-to-folders", action="store_true", help="Convert namespace pages to folder hierarchy")
    parser.add_argument("--block-refs", choices=["flag", "remove"], default="flag", help="How to handle block references (default: flag)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    parser.add_argument("--samples", type=int, default=2, help="Number of sample files to show in dry-run (default: 2)")

    args = parser.parse_args()

    # Determine mode: config or CLI
    if args.config:
        # Config mode
        try:
            config = load_config(args.config)
            migrator_args = config_to_migrator_args(config)
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            return 1
        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in config file: {e}")
            return 1

        source_path = migrator_args['source_path']
        output_path = migrator_args['output_path']

        # CLI flags can still override
        migrator_args['dry_run'] = args.dry_run
        migrator_args['verbose'] = args.verbose

    else:
        # CLI mode
        if not args.source:
            parser.error("source is required when not using --config")
        if not args.output:
            parser.error("--output is required when not using --config")

        source_path = args.source
        output_path = args.output

        migrator_args = {
            'source_path': source_path,
            'output_path': output_path,
            'journals_folder': args.journals_folder,
            'flatten_top_level': args.flatten_top_level,
            'namespaces_to_folders': args.namespaces_to_folders,
            'block_refs_mode': args.block_refs,
            'dry_run': args.dry_run,
            'verbose': args.verbose,
        }

    # Validate source path exists
    if not source_path.exists():
        print(f"❌ Error: Source path does not exist: {source_path}")
        return 1

    # Check for Logseq structure
    if not (source_path / "pages").exists() and not (source_path / "journals").exists():
        print(f"⚠️ Warning: No pages/ or journals/ folder found. Is this a Logseq graph?")

    migrator = LogseqMigrator(**migrator_args)
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be written\n")
        print_sample(source_path, migrator, args.samples)
    
    stats = migrator.migrate()
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 Migration Summary")
    print(f"{'='*60}")
    print(f"Files processed:      {stats['files_processed']}")
    print(f"Properties converted: {stats['properties_converted']}")
    print(f"Admonitions converted:{stats['admonitions_converted']}")
    print(f"Block refs flagged:   {stats['block_refs_flagged']}")
    print(f"Tasks converted:      {stats['tasks_converted']}")
    
    if stats["errors"]:
        print(f"\n❌ Errors ({len(stats['errors'])}):")
        for error in stats["errors"][:10]:
            print(f"   {error}")
        if len(stats["errors"]) > 10:
            print(f"   ... and {len(stats['errors']) - 10} more")
    
    if stats["warnings"]:
        print(f"\n⚠️ Warnings ({len(stats['warnings'])}):")
        for warning in stats["warnings"][:10]:
            print(f"   {warning}")
    
    if args.dry_run:
        print("\n✅ Dry run complete. Run without --dry-run to execute migration.")
    else:
        print(f"\n✅ Migration complete! Output: {output_path}")
        print("\n📌 Next steps:")
        print("   1. Open Obsidian")
        print("   2. Click 'Open folder as vault'")
        print(f"   3. Select: {output_path}")
        print("   4. Install recommended plugins: Calendar, Periodic Notes, Outliner, Dataview")
    
    return 0


if __name__ == "__main__":
    exit(main())
