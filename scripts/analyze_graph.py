#!/usr/bin/env python3
"""
Analyze a Logseq graph to detect patterns and features for migration planning.
Outputs a JSON report of detected features.
"""

import argparse
import json
import os
import re
import random
from pathlib import Path
from collections import defaultdict


def find_markdown_files(graph_path: Path) -> dict:
    """Find all markdown files in pages/ and journals/ folders."""
    files = {"pages": [], "journals": [], "other": []}
    
    pages_dir = graph_path / "pages"
    journals_dir = graph_path / "journals"
    
    if pages_dir.exists():
        files["pages"] = list(pages_dir.glob("*.md"))
    
    if journals_dir.exists():
        files["journals"] = list(journals_dir.glob("*.md"))
    
    # Check for other .md files in root
    for f in graph_path.glob("*.md"):
        if f.name not in ["README.md", "readme.md"]:
            files["other"].append(f)
    
    return files


def analyze_file(filepath: Path) -> dict:
    """Analyze a single file for Logseq patterns."""
    patterns = {
        "properties": [],
        "admonitions": [],
        "block_ids": [],
        "block_refs": [],
        "collapsed": 0,
        "numbered_lists": 0,
        "image_sizing": 0,
        "wiki_links": [],
        "tags": [],
        "tasks": defaultdict(int),
        "queries": 0,
        "logbook": 0,
        "embeds": 0,
        "namespaces": False,
        "max_indent_level": 0,
        "total_bullets": 0,
    }
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": str(e)}
    
    lines = content.split("\n")
    
    for line in lines:
        # Count bullets and indent level
        indent_match = re.match(r'^(\t*)-\s', line)
        if indent_match:
            patterns["total_bullets"] += 1
            indent_level = len(indent_match.group(1))
            patterns["max_indent_level"] = max(patterns["max_indent_level"], indent_level)
        
        # Properties (key:: value)
        prop_match = re.match(r'^(\s*)([\w-]+)::\s*(.+)$', line)
        if prop_match:
            prop_name = prop_match.group(2)
            if prop_name == "collapsed":
                patterns["collapsed"] += 1
            elif prop_name == "logseq.order-list-type":
                patterns["numbered_lists"] += 1
            elif prop_name == "id":
                patterns["block_ids"].append(prop_match.group(3)[:8])  # First 8 chars
            elif prop_name not in ["collapsed", "logseq.order-list-type", "id"]:
                patterns["properties"].append(prop_name)
        
        # Admonitions
        admon_match = re.search(r'#\+BEGIN_(\w+)', line)
        if admon_match:
            patterns["admonitions"].append(admon_match.group(1))
        
        # Block references ((id))
        block_refs = re.findall(r'\(\(([a-f0-9-]{36})\)\)', line)
        patterns["block_refs"].extend(block_refs)
        
        # Image sizing
        if re.search(r'\{:height\s+\d+.*:width\s+\d+\}', line):
            patterns["image_sizing"] += 1
        
        # Wiki links
        wiki_links = re.findall(r'\[\[([^\]]+)\]\]', line)
        patterns["wiki_links"].extend(wiki_links)
        
        # Tags (excluding property-like patterns)
        tags = re.findall(r'(?<!\w)#([\w-]+)(?!\w)', line)
        patterns["tags"].extend([t for t in tags if not t.startswith("+")])  # Exclude #+BEGIN
        
        # Task states
        for state in ["TODO", "DOING", "NOW", "LATER", "DONE", "WAITING", "CANCELLED"]:
            if re.search(rf'^\s*-\s+{state}\s+', line):
                patterns["tasks"][state] += 1
        
        # Queries
        if "{{query" in line:
            patterns["queries"] += 1
        
        # Logbook
        if ":LOGBOOK:" in line:
            patterns["logbook"] += 1
        
        # Embeds
        if "{{embed" in line:
            patterns["embeds"] += 1
    
    # Check for namespaces in filename
    if "%2F" in filepath.name or "/" in filepath.stem:
        patterns["namespaces"] = True
    
    # Convert defaultdict to regular dict
    patterns["tasks"] = dict(patterns["tasks"])
    
    return patterns


def merge_patterns(all_patterns: list) -> dict:
    """Merge patterns from multiple files into a summary."""
    summary = {
        "properties": set(),
        "admonition_types": set(),
        "block_ids_count": 0,
        "block_refs_count": 0,
        "files_with_collapsed": 0,
        "numbered_lists_count": 0,
        "image_sizing_count": 0,
        "unique_wiki_links": set(),
        "unique_tags": set(),
        "task_counts": defaultdict(int),
        "queries_count": 0,
        "logbook_count": 0,
        "embeds_count": 0,
        "files_with_namespaces": 0,
        "max_indent_level": 0,
        "total_bullets": 0,
        "avg_bullets_per_file": 0,
    }
    
    valid_patterns = [p for p in all_patterns if "error" not in p]
    
    for p in valid_patterns:
        summary["properties"].update(p.get("properties", []))
        summary["admonition_types"].update(p.get("admonitions", []))
        summary["block_ids_count"] += len(p.get("block_ids", []))
        summary["block_refs_count"] += len(p.get("block_refs", []))
        if p.get("collapsed", 0) > 0:
            summary["files_with_collapsed"] += 1
        summary["numbered_lists_count"] += p.get("numbered_lists", 0)
        summary["image_sizing_count"] += p.get("image_sizing", 0)
        summary["unique_wiki_links"].update(p.get("wiki_links", []))
        summary["unique_tags"].update(p.get("tags", []))
        for task, count in p.get("tasks", {}).items():
            summary["task_counts"][task] += count
        summary["queries_count"] += p.get("queries", 0)
        summary["logbook_count"] += p.get("logbook", 0)
        summary["embeds_count"] += p.get("embeds", 0)
        if p.get("namespaces"):
            summary["files_with_namespaces"] += 1
        summary["max_indent_level"] = max(summary["max_indent_level"], p.get("max_indent_level", 0))
        summary["total_bullets"] += p.get("total_bullets", 0)
    
    if valid_patterns:
        summary["avg_bullets_per_file"] = round(summary["total_bullets"] / len(valid_patterns), 1)
    
    # Convert sets to sorted lists for JSON
    summary["properties"] = sorted(summary["properties"])
    summary["admonition_types"] = sorted(summary["admonition_types"])
    summary["unique_tags"] = sorted(list(summary["unique_tags"])[:20])  # Limit to 20
    summary["wiki_links_count"] = len(summary["unique_wiki_links"])
    del summary["unique_wiki_links"]  # Too large to include
    summary["task_counts"] = dict(summary["task_counts"])
    
    return summary


def generate_report(graph_path: Path, sample_size: int = 50) -> dict:
    """Generate a full analysis report for the graph."""
    files = find_markdown_files(graph_path)
    
    report = {
        "graph_path": str(graph_path),
        "file_counts": {
            "pages": len(files["pages"]),
            "journals": len(files["journals"]),
            "other": len(files["other"]),
            "total": len(files["pages"]) + len(files["journals"]) + len(files["other"]),
        },
        "assets_folder": (graph_path / "assets").exists(),
        "sample_size": 0,
        "patterns": {},
        "recommendations": [],
    }
    
    # Sample files for analysis
    all_files = files["pages"] + files["journals"]
    if len(all_files) > sample_size:
        sampled = random.sample(all_files, sample_size)
    else:
        sampled = all_files
    
    report["sample_size"] = len(sampled)
    
    # Analyze sampled files
    all_patterns = [analyze_file(f) for f in sampled]
    report["patterns"] = merge_patterns(all_patterns)
    
    # Generate recommendations based on patterns
    patterns = report["patterns"]
    
    if patterns["block_refs_count"] > 0:
        report["recommendations"].append({
            "feature": "block_references",
            "count": patterns["block_refs_count"],
            "action": "ask",
            "message": f"Found {patterns['block_refs_count']} block references. These require manual mapping. Options: flag for manual fix, or remove."
        })
    
    if patterns["files_with_namespaces"] > 0:
        report["recommendations"].append({
            "feature": "namespaces",
            "count": patterns["files_with_namespaces"],
            "action": "ask",
            "message": f"Found {patterns['files_with_namespaces']} files with namespace paths (e.g., Parent/Child). Convert to folder hierarchy?"
        })
    
    if patterns["queries_count"] > 0:
        report["recommendations"].append({
            "feature": "queries",
            "count": patterns["queries_count"],
            "action": "warn",
            "message": f"Found {patterns['queries_count']} Logseq queries. These will be flagged for manual Dataview conversion."
        })
    
    if patterns["admonition_types"]:
        report["recommendations"].append({
            "feature": "admonitions",
            "types": patterns["admonition_types"],
            "action": "info",
            "message": f"Will convert {len(patterns['admonition_types'])} admonition types to Obsidian callouts: {', '.join(patterns['admonition_types'])}"
        })
    
    if patterns["properties"]:
        report["recommendations"].append({
            "feature": "properties",
            "types": patterns["properties"][:10],
            "action": "info",
            "message": f"Will convert {len(patterns['properties'])} property types to YAML frontmatter"
        })
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Analyze a Logseq graph for migration")
    parser.add_argument("graph_path", type=Path, help="Path to Logseq graph folder")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of files to sample (default: 50)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")
    
    args = parser.parse_args()
    
    if not args.graph_path.exists():
        print(f"Error: Path does not exist: {args.graph_path}")
        return 1
    
    report = generate_report(args.graph_path, args.sample_size)
    
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        # Human-readable output
        print(f"\n📊 Logseq Graph Analysis: {report['graph_path']}")
        print("=" * 60)
        
        counts = report["file_counts"]
        print(f"\n📁 Files found:")
        print(f"   Pages:    {counts['pages']}")
        print(f"   Journals: {counts['journals']}")
        print(f"   Other:    {counts['other']}")
        print(f"   Total:    {counts['total']}")
        print(f"   Assets:   {'✓' if report['assets_folder'] else '✗'}")
        
        print(f"\n🔍 Analyzed {report['sample_size']} files")
        
        patterns = report["patterns"]
        print(f"\n📋 Detected patterns:")
        print(f"   Properties:      {len(patterns['properties'])} types")
        print(f"   Admonitions:     {len(patterns['admonition_types'])} types ({', '.join(patterns['admonition_types']) or 'none'})")
        print(f"   Block IDs:       {patterns['block_ids_count']}")
        print(f"   Block refs:      {patterns['block_refs_count']}")
        print(f"   Collapsed:       {patterns['files_with_collapsed']} files")
        print(f"   Numbered lists:  {patterns['numbered_lists_count']}")
        print(f"   Image sizing:    {patterns['image_sizing_count']}")
        print(f"   Wiki links:      {patterns['wiki_links_count']}")
        print(f"   Tags:            {len(patterns['unique_tags'])}")
        print(f"   Queries:         {patterns['queries_count']}")
        print(f"   Logbook blocks:  {patterns['logbook_count']}")
        print(f"   Embeds:          {patterns['embeds_count']}")
        print(f"   Namespaces:      {patterns['files_with_namespaces']} files")
        print(f"   Max indent:      {patterns['max_indent_level']} levels")
        print(f"   Avg bullets:     {patterns['avg_bullets_per_file']}/file")
        
        if patterns["task_counts"]:
            print(f"\n✅ Task states:")
            for state, count in sorted(patterns["task_counts"].items()):
                print(f"   {state}: {count}")
        
        if report["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in report["recommendations"]:
                icon = "❓" if rec["action"] == "ask" else "⚠️" if rec["action"] == "warn" else "ℹ️"
                print(f"   {icon} {rec['message']}")
        
        print()
    
    return 0


if __name__ == "__main__":
    exit(main())
