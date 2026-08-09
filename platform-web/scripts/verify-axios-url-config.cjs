const fs = require('fs');
const path = require('path');

function normalizeApiBase(value) {
  if (typeof value !== 'string') return '';
  const trimmed = value.trim();
  return trimmed && trimmed !== 'undefined' && trimmed !== 'null' ? trimmed : '';
}

function resolveApiBase(candidates, label, options = {}) {
  for (const candidate of candidates) {
    const normalized = normalizeApiBase(candidate);
    if (normalized) return normalized;
  }
  if (options.required) throw new Error(`${label} 未配置`);
  return '';
}

function joinApiBase(base, requestUrl) {
  const url = typeof requestUrl === 'string' ? requestUrl : '';
  if (!base) return url;
  if (!url) return base;
  if (/^[a-z][a-z\d+\-.]*:\/\//i.test(url)) return url;
  if (base === '/') return url.startsWith('/') ? url : `/${url}`;
  return `${base.replace(/\/+$/, '')}/${url.replace(/^\/+/, '')}`;
}

function assertEqual(actual, expected, label) {
  if (actual !== expected) throw new Error(`${label}: expected ${expected}, got ${actual}`);
}

function assertThrows(fn, label) {
  let thrown = false;
  try {
    fn();
  } catch {
    thrown = true;
  }
  if (!thrown) throw new Error(`${label}: expected throw`);
}

assertEqual(normalizeApiBase(undefined), '', 'undefined base');
assertEqual(normalizeApiBase('undefined'), '', 'literal undefined base');
assertEqual(normalizeApiBase('null'), '', 'literal null base');
assertEqual(normalizeApiBase('  /api/auth  '), '/api/auth', 'trimmed base');
assertEqual(
  resolveApiBase([undefined, '/'], '平台业务 API', { required: true }),
  '/',
  'required fallback',
);
assertThrows(
  () => resolveApiBase([undefined, 'null', ''], '平台业务 API', { required: true }),
  'required missing',
);
assertEqual(resolveApiBase([undefined, ''], '数据服务'), '', 'optional missing');
assertEqual(
  joinApiBase('/', '/risk/api/v1/risk-records/'),
  '/risk/api/v1/risk-records/',
  'root base absolute path',
);
assertEqual(joinApiBase('/', 'login'), '/login', 'root base relative path');
assertEqual(joinApiBase('/api/auth', '/login'), '/api/auth/login', 'nested base absolute path');
assertEqual(joinApiBase('/api/data/', '/health'), '/api/data/health', 'trim duplicate slash');

const source = fs.readFileSync(
  path.join(process.cwd(), 'src', 'utils', 'http', 'axios', 'index.ts'),
  'utf8',
);
const sourceWithoutComments = source.replace(/\/\/.*$/gm, '');

for (const required of [
  'requireApiUrl && !apiUrl',
  'resolveApiBase(',
  'joinApiBase(',
  'VITE_GLOB_API_URL_PLOY, globSetting.apiUrl',
  'apiUrl: dataApiUrl',
  'apiUrl: monitorApiUrl',
  'apiUrl: futureApiUrl',
  'requestInterceptors: (config)',
]) {
  if (!source.includes(required)) throw new Error(`axios source missing ${required}`);
}

if (
  /apiUrl:\\s*appenvConfig\\.VITE_GLOB_API_URL_(DATA|MONITOR|FUTURE)/.test(sourceWithoutComments)
) {
  throw new Error('optional API client still uses raw env base directly');
}

console.log('axios URL configuration checks passed');
