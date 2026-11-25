const fs = require('node:fs');
const path = require('node:path');

// Node's native cpSync crashes on this Windows host before tests can assert.
// Copy regular fixture files explicitly; never follow links outside the source.
module.exports = function copyFixtureDirectory(source, target) {
  fs.mkdirSync(target, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const from = path.join(source, entry.name);
    const to = path.join(target, entry.name);
    if (entry.isDirectory()) copyFixtureDirectory(from, to);
    else if (entry.isFile()) fs.copyFileSync(from, to);
    else throw new Error(`Unsupported fixture entry: ${from}`);
  }
};
