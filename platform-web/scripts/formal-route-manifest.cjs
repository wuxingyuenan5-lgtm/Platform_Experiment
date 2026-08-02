#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { ManifestError, findRouteObject, parseRoute } = require('./formal-route-parser.cjs');

const DEFAULT_ROOT = path.resolve(__dirname, '..');
const DEFAULT_MANIFEST = path.join(DEFAULT_ROOT, 'scripts', 'formal-route-manifest.json');
const ROUTE_MODULE_ROOT = path.join('src', 'router', 'routes', 'modules');

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function routeModulePaths(root) {
  const modulesRoot = path.join(root, ROUTE_MODULE_ROOT);
  if (!fs.existsSync(modulesRoot)) throw new ManifestError(`missing route module root: ${ROUTE_MODULE_ROOT}`);
  return fs.readdirSync(modulesRoot, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.ts'))
    .map((entry) => path.posix.join(ROUTE_MODULE_ROOT, entry.name))
    .sort((left, right) => left.localeCompare(right));
}

function generateManifest(options = {}) {
  const root = path.resolve(options.root || DEFAULT_ROOT);
  const modules = [];
  const names = new Map();
  const paths = new Map();
  for (const modulePath of routeModulePaths(root)) {
    const absolute = path.join(root, ...modulePath.split('/'));
    const raw = fs.readFileSync(absolute);
    const source = raw.toString('utf8');
    if (/(?:^|[\/])(demo|mock|tests?|example|template)(?:[\/]|$)/i.test(modulePath)) {
      throw new ManifestError(`forbidden route module entered formal discovery: ${modulePath}`);
    }
    if (source.includes('@/views/demo') || source.includes('/demo')) {
      throw new ManifestError(`formal route module references Demo content: ${modulePath}`);
    }
    const routes = parseRoute(findRouteObject(source, modulePath), {
      root,
      parentPath: '/',
      label: modulePath,
    });
    for (const route of routes) {
      if (names.has(route.name)) {
        throw new ManifestError(
          `duplicate Route name ${route.name}: ${names.get(route.name)} and ${modulePath}`,
        );
      }
      names.set(route.name, modulePath);
      if (paths.has(route.full_path)) {
        throw new ManifestError(
          `duplicate Route path ${route.full_path}: ${paths.get(route.full_path)} and ${modulePath}`,
        );
      }
      paths.set(route.full_path, modulePath);
    }
    modules.push({
      path: modulePath,
      sha256: sha256(raw),
      routes,
    });
  }
  return {
    schema_version: 2,
    authority: 'src/router/routes/modules/*.ts and generated typed View Registry',
    runtime_source: false,
    modules,
  };
}

function renderManifest(manifest) {
  return `${JSON.stringify(manifest)}\n`;
}

function generatedBytes(options = {}) {
  return Buffer.from(renderManifest(generateManifest(options)), 'utf8');
}

function writeManifest(options = {}) {
  const manifestPath = path.resolve(options.manifestPath || DEFAULT_MANIFEST);
  const bytes = generatedBytes(options);
  fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
  fs.writeFileSync(manifestPath, bytes);
  return { manifestPath, bytes, sha256: sha256(bytes) };
}

function checkManifest(options = {}) {
  const manifestPath = path.resolve(options.manifestPath || DEFAULT_MANIFEST);
  if (!fs.existsSync(manifestPath)) {
    throw new ManifestError(
      `manifest is missing: ${manifestPath}; run node scripts/formal-route-manifest.cjs --write`,
    );
  }
  const expected = generatedBytes(options);
  const actual = fs.readFileSync(manifestPath);
  if (!actual.equals(expected)) {
    throw new ManifestError(
      `manifest drift detected: ${manifestPath}; run node scripts/formal-route-manifest.cjs --write`,
    );
  }
  return { manifestPath, bytes: actual, sha256: sha256(actual) };
}

function main(argv = process.argv.slice(2)) {
  const write = argv.includes('--write');
  const check = argv.includes('--check');
  if (write === check) {
    throw new ManifestError('choose exactly one command: --write or --check');
  }
  const result = write ? writeManifest() : checkManifest();
  const action = write ? 'wrote' : 'verified';
  console.log(
    `Formal route manifest ${action}: ${path.relative(DEFAULT_ROOT, result.manifestPath)} `
      + `(${result.sha256})`,
  );
}

module.exports = {
  ManifestError,
  checkManifest,
  generateManifest,
  generatedBytes,
  renderManifest,
  writeManifest,
};

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
