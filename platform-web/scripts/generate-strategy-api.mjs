import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import openapiTS, { astToString } from 'openapi-typescript';
import ts from 'typescript';
import prettier from 'prettier';

const root = fileURLToPath(new URL('../..', import.meta.url));
const python = resolve(
  root,
  'platform-api',
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);
const exported = process.argv.includes('--from-schema')
  ? null
  : spawnSync(python, [resolve(root, 'platform-api/scripts/export_strategy_openapi.py')], {
      cwd: root,
      encoding: 'utf8',
      maxBuffer: 16 * 1024 * 1024,
    });
if (exported && exported.status !== 0) throw new Error(exported.stderr || 'OpenAPI export failed');
// CI verifies FastAPI -> JSON in the Python job and JSON -> TS in the Node job.
const schema = JSON.parse(
  exported
    ? exported.stdout
    : readFileSync(resolve(root, 'docs/contracts/platform-strategy.openapi.json'), 'utf8'),
);
const ast = await openapiTS(schema, {
  transform(node) {
    // Pydantic Decimal inputs allow JSON numbers too. The browser uses the exact
    // string subset so quantities never pass through IEEE-754 conversion.
    if (
      node.anyOf?.some((item) => item.type === 'string' && item.pattern) &&
      node.anyOf?.some((item) => item.type === 'number')
    ) {
      const exact = ts.factory.createKeywordTypeNode(ts.SyntaxKind.StringKeyword);
      return node.anyOf.some((item) => item.type === 'null')
        ? ts.factory.createUnionTypeNode([
            exact,
            ts.factory.createLiteralTypeNode(ts.factory.createNull()),
          ])
        : exact;
    }
  },
});
const generatedPath = resolve(root, 'platform-web/src/api/platform/generated/strategy.ts');
const generatedSource = await prettier.format(
  '// Generated from FastAPI. Run pnpm generate:strategy-api; do not edit by hand.\n' +
    astToString(ast),
  { ...(await prettier.resolveConfig(generatedPath)), filepath: generatedPath },
);
const outputs = new Map([
  [
    resolve(root, 'docs/contracts/platform-strategy.openapi.json'),
    `${JSON.stringify(schema, null, 2)}\n`,
  ],
  [generatedPath, generatedSource],
]);
for (const [path, content] of outputs) {
  if (process.argv.includes('--check')) {
    if (readFileSync(path, 'utf8') !== content) throw new Error(`Generated API is stale: ${path}`);
  } else {
    mkdirSync(resolve(path, '..'), { recursive: true });
    writeFileSync(path, content);
  }
}
