'use strict';

const path = require('node:path');

const DIAGNOSTIC_PATTERN = /^(.*)\((\d+),(\d+)\): error TS(\d+): (.*)$/;

function normalizeDiagnosticPath(filePath, cwd, repoRoot) {
  const normalizedInput = filePath.replaceAll('\\', '/');
  const absolutePath = path.isAbsolute(normalizedInput)
    ? normalizedInput
    : path.resolve(cwd, normalizedInput);
  return path.relative(repoRoot, absolutePath).replaceAll('\\', '/');
}

function parseDiagnostics(output, cwd, repoRoot) {
  return output
    .split(/\r?\n/)
    .map((line) => line.match(DIAGNOSTIC_PATTERN))
    .filter(Boolean)
    .map((match) => ({
      path: normalizeDiagnosticPath(match[1], cwd, repoRoot),
      line: Number(match[2]),
      column: Number(match[3]),
      code: `TS${match[4]}`,
      message: match[5].trim(),
    }));
}

function diagnosticKey(diagnostic) {
  return [
    diagnostic.path,
    diagnostic.line,
    diagnostic.column,
    diagnostic.code,
    diagnostic.message,
  ].join('|');
}

function findNewDiagnostics(baseDiagnostics, headDiagnostics) {
  const baseKeys = new Set(baseDiagnostics.map(diagnosticKey));
  return headDiagnostics.filter((diagnostic) => !baseKeys.has(diagnosticKey(diagnostic)));
}

function findChangedFileDiagnostics(headDiagnostics, changedFiles) {
  const changedFileSet = new Set(changedFiles.map((file) => file.replaceAll('\\', '/')));
  return headDiagnostics.filter((diagnostic) => changedFileSet.has(diagnostic.path));
}

function formatDiagnostic(diagnostic) {
  return `${diagnostic.path}(${diagnostic.line},${diagnostic.column}): error ${diagnostic.code}: ${diagnostic.message}`;
}

module.exports = {
  findChangedFileDiagnostics,
  findNewDiagnostics,
  formatDiagnostic,
  parseDiagnostics,
};
