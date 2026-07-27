'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');

const projectRoot = path.resolve(__dirname, '..');
const moduleCache = new Map();

function formatDiagnostic(diagnostic) {
  const message = ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n');
  if (!diagnostic.file || diagnostic.start === undefined) return message;
  const position = diagnostic.file.getLineAndCharacterOfPosition(diagnostic.start);
  return `${diagnostic.file.fileName}:${position.line + 1}:${position.character + 1} ${message}`;
}

function resolveLocalModule(specifier, parentFile) {
  const candidate = path.resolve(path.dirname(parentFile), specifier);
  for (const value of [candidate, `${candidate}.ts`, path.join(candidate, 'index.ts')]) {
    if (fs.existsSync(value) && fs.statSync(value).isFile()) return value;
  }
  throw new Error(`Cannot resolve local TypeScript module ${specifier} from ${parentFile}`);
}

function loadTypeScriptModule(filePath) {
  const resolvedPath = path.resolve(filePath);
  const cached = moduleCache.get(resolvedPath);
  if (cached) return cached.exports;

  const source = fs.readFileSync(resolvedPath, 'utf8');
  const result = ts.transpileModule(source, {
    fileName: resolvedPath,
    reportDiagnostics: true,
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      moduleResolution: ts.ModuleResolutionKind.Node10,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const errors = (result.diagnostics || []).filter(
    (diagnostic) => diagnostic.category === ts.DiagnosticCategory.Error,
  );
  if (errors.length) {
    throw new Error(errors.map(formatDiagnostic).join('\n'));
  }

  const moduleRecord = { exports: {} };
  moduleCache.set(resolvedPath, moduleRecord);
  const localRequire = (specifier) => {
    if (specifier.startsWith('.')) {
      return loadTypeScriptModule(resolveLocalModule(specifier, resolvedPath));
    }
    return require(specifier);
  };
  const execute = new Function(
    'require',
    'module',
    'exports',
    '__filename',
    '__dirname',
    result.outputText,
  );
  execute(
    localRequire,
    moduleRecord,
    moduleRecord.exports,
    resolvedPath,
    path.dirname(resolvedPath),
  );
  return moduleRecord.exports;
}

const userAccess = loadTypeScriptModule(path.join(projectRoot, 'src/access/userAccess.ts'));
const routeAccess = loadTypeScriptModule(path.join(projectRoot, 'src/access/routeAccess.ts'));
const decimalDisplay = loadTypeScriptModule(
  path.join(projectRoot, 'src/utils/decimalDisplay.ts'),
);

test('browser permission points match exactly without wildcard expansion', () => {
  assert.equal(userAccess.hasPermission(['user.read'], 'user.read'), true);
  assert.equal(userAccess.hasPermission(['*'], 'user.read'), false);
});

test('all-of and any-of permission requirements remain exact', () => {
  const granted = ['profile.read_self', 'member.holding.read_self'];
  assert.equal(
    userAccess.hasEveryPermission(granted, ['profile.read_self', 'member.holding.read_self']),
    true,
  );
  assert.equal(userAccess.hasEveryPermission(granted, ['profile.read_self', 'user.read']), false);
  assert.equal(userAccess.hasAnyPermission(granted, ['user.read', 'profile.read_self']), true);
  assert.equal(userAccess.hasAnyPermission(['*'], ['user.read', 'profile.read_self']), false);
});

test('route all-of and any-of metadata use the same policy', () => {
  assert.equal(
    userAccess.canAccessRoute(['profile.read_self', 'member.holding.read_self'], {
      permissions: 'profile.read_self',
      anyPermissions: ['member.holding.read_self', 'user.read'],
    }),
    true,
  );
  assert.equal(
    userAccess.canAccessRoute(['profile.read_self'], {
      permissions: 'profile.read_self',
      anyPermissions: ['member.holding.read_self', 'user.read'],
    }),
    false,
  );
});

test('route permissions normalize and combine parent and child requirements', () => {
  assert.deepEqual(routeAccess.normalizeRoutePermissions(' user.read '), ['user.read']);
  assert.deepEqual(routeAccess.normalizeRoutePermissions(['user.read', ' ', 'user.audit.read']), [
    'user.read',
    'user.audit.read',
  ]);
  assert.deepEqual(routeAccess.normalizeRoutePermissions(undefined), []);

  const matched = [
    { meta: { permissions: 'profile.read_self' } },
    { meta: { permissions: ['member.holding.read_self', 'profile.read_self'] } },
  ];
  assert.deepEqual(routeAccess.matchedRoutePermissions(matched), [
    'profile.read_self',
    'member.holding.read_self',
  ]);
  assert.equal(
    routeAccess.canAccessMatchedRoute(matched, [
      'profile.read_self',
      'member.holding.read_self',
    ]),
    true,
  );
  assert.equal(routeAccess.canAccessMatchedRoute(matched, ['profile.read_self']), false);
});

test('route tree filtering removes denied branches without mutating source', () => {
  const source = [
    {
      path: '/account',
      meta: { permissions: 'profile.read_self' },
      children: [
        {
          path: 'index',
          meta: { permissions: 'profile.read_self' },
        },
      ],
    },
    {
      path: '/risk',
      children: [
        {
          path: 'users',
          meta: { permissions: 'user.read' },
        },
        {
          path: 'detail',
        },
      ],
    },
  ];

  assert.deepEqual(routeAccess.filterPermissionTree(source, ['profile.read_self']), [
    {
      path: '/account',
      meta: { permissions: 'profile.read_self' },
      children: [
        {
          path: 'index',
          meta: { permissions: 'profile.read_self' },
          children: [],
        },
      ],
    },
    {
      path: '/risk',
      children: [
        {
          path: 'detail',
          children: [],
        },
      ],
    },
  ]);
  assert.equal(source[1].children.length, 2);
});

test('empty protected parents are removed', () => {
  const source = [
    {
      path: '/users',
      children: [
        {
          path: 'index',
          meta: { permissions: 'user.read' },
        },
      ],
    },
  ];
  assert.deepEqual(routeAccess.filterPermissionTree(source, []), []);
});

test('Decimal display groups canonical strings without Number conversion', () => {
  assert.equal(
    decimalDisplay.formatDecimalString('123456789.123456789123456789'),
    '123,456,789.123456789123456789',
  );
  assert.equal(decimalDisplay.formatDecimalString('-1000.0001'), '-1,000.0001');
});

test('Decimal display keeps unavailable values distinct from zero', () => {
  assert.equal(decimalDisplay.formatNullableDecimalString(undefined), '不可用');
  assert.equal(decimalDisplay.formatMoneyString(null, 'CNY'), '不可用');
  assert.equal(decimalDisplay.formatNullableDecimalString('0'), '0');
  assert.equal(decimalDisplay.formatMoneyString('0', 'CNY'), '0 CNY');
});

test('signed money formatting does not use floating point arithmetic', () => {
  assert.equal(decimalDisplay.formatSignedMoneyString('0.01', 'CNY'), '+0.01 CNY');
  assert.equal(decimalDisplay.formatSignedMoneyString('-0.01', 'CNY'), '-0.01 CNY');
  assert.equal(decimalDisplay.formatSignedMoneyString('0.000', 'CNY'), '0.000 CNY');
});

test('ratio formatting moves the decimal point exactly', () => {
  assert.equal(decimalDisplay.formatRatioPercentString('1'), '+100%');
  assert.equal(
    decimalDisplay.formatRatioPercentString('0.123456789123456789'),
    '+12.3456789123456789%',
  );
  assert.equal(decimalDisplay.formatRatioPercentString('-0.0001'), '-0.01%');
  assert.equal(decimalDisplay.formatRatioPercentString('0'), '0%');
});

test('Decimal direction comes from the canonical string', () => {
  assert.equal(decimalDisplay.decimalDirection('100'), 'positive');
  assert.equal(decimalDisplay.decimalDirection('-0.0001'), 'negative');
  assert.equal(decimalDisplay.decimalDirection('0.000'), 'zero');
  assert.equal(decimalDisplay.decimalDirection(undefined), 'zero');
});
