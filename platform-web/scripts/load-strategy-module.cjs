const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const ts = require('typescript');

// Execute the actual TypeScript modules with explicit test-only boundary mocks.
module.exports = function createLoader(mocks = {}) {
  const cache = new Map();
  const root = path.resolve(__dirname, '..');
  function load(filename) {
    filename = path.resolve(root, filename);
    if (cache.has(filename)) return cache.get(filename).exports;
    const module = { exports: {} };
    cache.set(filename, module);
    const localRequire = createRequire(filename);
    const requireDependency = (name) => {
      if (name in mocks) return mocks[name];
      if (name.startsWith('@/') || name.startsWith('.')) {
        let resolved = name.startsWith('@/')
          ? path.resolve(root, 'src', name.slice(2))
          : path.resolve(path.dirname(filename), name);
        if (!path.extname(resolved)) resolved += '.ts';
        return load(resolved);
      }
      return localRequire(name);
    };
    const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        esModuleInterop: true,
      },
    }).outputText;
    new Function('require', 'module', 'exports', code)(requireDependency, module, module.exports);
    return module.exports;
  }
  return load;
};
