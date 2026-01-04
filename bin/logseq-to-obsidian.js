#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);
const scriptsDir = path.join(__dirname, '..', 'scripts');

function showHelp() {
  console.log(`
logseq-to-obsidian - Migrate Logseq graphs to Obsidian vaults

Usage:
  logseq-to-obsidian --config <config-file> [--dry-run] [--verbose]
  logseq-to-obsidian <logseq-path> <obsidian-path> [options]
  logseq-to-obsidian analyze <logseq-path> [--sample-size N]

Commands:
  analyze              Analyze a Logseq graph without migrating

Options:
  --config, -c         Path to config JSON file (recommended with Claude Code)
  --dry-run            Preview without writing files
  --flatten            Flatten top-level bullets to paragraphs
  --journals-folder    Journal folder name (default: "Daily")
  --namespaces-to-folders  Convert A/B pages to A/B.md in folders
  --block-refs [flag|remove]  How to handle block references
  --verbose            Show detailed progress
  --help, -h           Show this help message

Examples:
  logseq-to-obsidian --config .logseq-to-obsidian/config.json
  logseq-to-obsidian --config .logseq-to-obsidian/config.json --dry-run
  logseq-to-obsidian ~/logseq ~/obsidian --dry-run
  logseq-to-obsidian ~/logseq ~/obsidian --flatten
  logseq-to-obsidian analyze ~/logseq
`);
}

function runPython(script, args) {
  const scriptPath = path.join(scriptsDir, script);
  const proc = spawn('python3', [scriptPath, ...args], {
    stdio: 'inherit',
    env: process.env
  });

  proc.on('error', (err) => {
    if (err.code === 'ENOENT') {
      console.error('Error: python3 is required but not found in PATH');
      process.exit(1);
    }
    console.error('Error:', err.message);
    process.exit(1);
  });

  proc.on('close', (code) => {
    process.exit(code || 0);
  });
}

// Handle help
if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  showHelp();
  process.exit(0);
}

// Handle config mode
const configIndex = args.findIndex(a => a === '--config' || a === '-c');
if (configIndex !== -1) {
  const configPath = args[configIndex + 1];
  if (!configPath || configPath.startsWith('-')) {
    console.error('Error: --config requires a path to config file');
    console.error('Usage: logseq-to-obsidian --config <config-file>');
    process.exit(1);
  }

  // Build args for Python script
  const migrateArgs = ['--config', configPath];

  // Allow --dry-run and --verbose to pass through
  if (args.includes('--dry-run')) {
    migrateArgs.push('--dry-run');
  }
  if (args.includes('--verbose') || args.includes('-v')) {
    migrateArgs.push('--verbose');
  }

  // Pass --samples if provided
  const samplesIndex = args.findIndex(a => a === '--samples');
  if (samplesIndex !== -1 && args[samplesIndex + 1]) {
    migrateArgs.push('--samples', args[samplesIndex + 1]);
  }

  console.log('Starting migration with config...\n');
  runPython('migrate.py', migrateArgs);
}
// Handle analyze command
else if (args[0] === 'analyze') {
  const analyzeArgs = args.slice(1);
  if (analyzeArgs.length === 0) {
    console.error('Error: Please provide the path to your Logseq graph');
    console.error('Usage: logseq-to-obsidian analyze <logseq-path>');
    process.exit(1);
  }
  runPython('analyze_graph.py', analyzeArgs);
}
// Handle CLI mode (legacy)
else {
  if (args.length < 2 && !args.includes('--help')) {
    console.error('Error: Please provide both source and destination paths');
    console.error('Usage: logseq-to-obsidian <logseq-path> <obsidian-path> [options]');
    console.error('   or: logseq-to-obsidian --config <config-file>');
    process.exit(1);
  }

  const logseqPath = args[0];
  const obsidianPath = args[1];
  const options = args.slice(2);

  // Transform --flatten to --flatten-top-level for the Python script
  const migrateArgs = [logseqPath, '--output', obsidianPath];

  for (const opt of options) {
    if (opt === '--flatten') {
      migrateArgs.push('--flatten-top-level');
    } else {
      migrateArgs.push(opt);
    }
  }

  // Run analysis first
  console.log('Analyzing Logseq graph...\n');
  const analyzeProc = spawn('python3', [path.join(scriptsDir, 'analyze_graph.py'), logseqPath], {
    stdio: 'inherit'
  });

  analyzeProc.on('close', (code) => {
    if (code !== 0) {
      process.exit(code);
    }
    console.log('\nStarting migration...\n');
    runPython('migrate.py', migrateArgs);
  });
}
