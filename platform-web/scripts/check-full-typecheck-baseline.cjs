'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const {
  findChangedFileDiagnostics,
  findNewDiagnostics,
  formatDiagnostic,
  parseDiagnostics,
} = require('./full-typecheck-core.cjs');

const webRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(webRoot, '..');
const vueTscBin = path.join(webRoot, 'node_modules', '.bin', 'vue-tsc');

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || repoRoot,
    encoding: 'utf8',
    env: process.env,
    maxBuffer: 64 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  return {
    status: result.status ?? 1,
    output: `${result.stdout || ''}${result.stderr || ''}`,
  };
}

function resolveBaseRef() {
  if (process.env.PLATFORM_FULL_TYPECHECK_BASE_REF) {
    return process.env.PLATFORM_FULL_TYPECHECK_BASE_REF;
  }
  const mergeBase = run('git', ['merge-base', 'origin/main', 'HEAD']);
  if (mergeBase.status !== 0 || !mergeBase.output.trim()) {
    throw new Error('Unable to resolve the full typecheck base ref. Fetch origin/main or set PLATFORM_FULL_TYPECHECK_BASE_REF.');
  }
  return mergeBase.output.trim();
}

function collectDiagnostics(cwd, configPath) {
  const result = run(vueTscBin, ['-p', configPath, '--noEmit', '--pretty', 'false'], { cwd });
  return {
    diagnostics: parseDiagnostics(result.output, cwd, repoRoot),
    output: result.output,
    status: result.status,
  };
}

function linkIfPresent(source, destination) {
  if (fs.existsSync(source) && !fs.existsSync(destination)) {
    fs.symlinkSync(source, destination, 'dir');
  }
}

function changedFilesSince(baseRef) {
  const result = run('git', [
    'diff',
    '--name-only',
    `${baseRef}...HEAD`,
    '--',
    'platform-web',
  ]);
  if (result.status !== 0) {
    throw new Error(`Unable to collect changed files:\n${result.output}`);
  }
  return result.output.split(/\r?\n/).filter(Boolean);
}

function printDiagnostics(title, diagnostics) {
  if (diagnostics.length === 0) return;
  console.error(`\n${title}`);
  diagnostics.forEach((diagnostic) => console.error(formatDiagnostic(diagnostic)));
}

function main() {
  if (!fs.existsSync(vueTscBin)) {
    throw new Error('vue-tsc is not installed. Run pnpm install --frozen-lockfile first.');
  }

  const baseRef = resolveBaseRef();
  const current = collectDiagnostics(webRoot, 'tsconfig.full.json');
  const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'platform-full-typecheck-'));
  let worktreeAdded = false;

  try {
    const addWorktree = run('git', ['worktree', 'add', '--detach', '--quiet', temporaryRoot, baseRef]);
    if (addWorktree.status !== 0) {
      throw new Error(`Unable to create base worktree:\n${addWorktree.output}`);
    }
    worktreeAdded = true;

    const baseWebRoot = path.join(temporaryRoot, 'platform-web');
    const headConfig = fs.readFileSync(path.join(webRoot, 'tsconfig.full.json'), 'utf8');
    const baseConfigPath = path.join(baseWebRoot, 'tsconfig.full.pr-head.json');
    fs.writeFileSync(baseConfigPath, headConfig);

    linkIfPresent(path.join(repoRoot, 'node_modules'), path.join(temporaryRoot, 'node_modules'));
    linkIfPresent(path.join(webRoot, 'node_modules'), path.join(baseWebRoot, 'node_modules'));

    const baseline = collectDiagnostics(baseWebRoot, baseConfigPath);
    const changedFiles = changedFilesSince(baseRef);
    const changedFileDiagnostics = findChangedFileDiagnostics(
      current.diagnostics,
      changedFiles,
    );
    const newDiagnostics = findNewDiagnostics(baseline.diagnostics, current.diagnostics);

    console.log(
      [
        `[full-typecheck] base_ref=${baseRef}`,
        `base_diagnostics=${baseline.diagnostics.length}`,
        `head_diagnostics=${current.diagnostics.length}`,
        `changed_file_diagnostics=${changedFileDiagnostics.length}`,
        `new_diagnostics=${newDiagnostics.length}`,
      ].join(' '),
    );

    printDiagnostics('Diagnostics in files changed by this PR:', changedFileDiagnostics);
    printDiagnostics('Diagnostics newly introduced relative to the base:', newDiagnostics);

    if (changedFileDiagnostics.length > 0 || newDiagnostics.length > 0) {
      process.exitCode = 1;
      return;
    }

    if (current.status !== 0 && current.diagnostics.length === 0) {
      console.error(current.output);
      throw new Error('Full typecheck failed without parseable TypeScript diagnostics.');
    }
  } finally {
    if (worktreeAdded) {
      run('git', ['worktree', 'remove', '--force', temporaryRoot]);
    }
    fs.rmSync(temporaryRoot, { recursive: true, force: true });
  }
}

try {
  main();
} catch (error) {
  console.error(`[full-typecheck] ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
