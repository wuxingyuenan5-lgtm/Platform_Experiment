'use strict';

const fs = require('node:fs');
const path = require('node:path');

const FORBIDDEN_SEGMENTS = new Set(['demo', 'mock', 'test', 'tests', 'example', 'template']);

class ManifestError extends Error {
  constructor(message) {
    super(`[formal-route-manifest] ${message}`);
    this.name = 'ManifestError';
  }
}


function skipSpaceAndComments(source, start) {
  let index = start;
  while (index < source.length) {
    if (/\s/.test(source[index])) {
      index += 1;
      continue;
    }
    if (source.startsWith('//', index)) {
      const newline = source.indexOf('\n', index + 2);
      return newline === -1 ? source.length : skipSpaceAndComments(source, newline + 1);
    }
    if (source.startsWith('/*', index)) {
      const end = source.indexOf('*/', index + 2);
      if (end === -1) throw new ManifestError('unterminated block comment');
      index = end + 2;
      continue;
    }
    break;
  }
  return index;
}

function scanQuoted(source, start) {
  const quote = source[start];
  let index = start + 1;
  while (index < source.length) {
    if (source[index] === '\\') {
      index += 2;
      continue;
    }
    if (source[index] === quote) return index + 1;
    index += 1;
  }
  throw new ManifestError(`unterminated string starting at offset ${start}`);
}

function scanBalanced(source, start, open, close) {
  if (source[start] !== open) throw new ManifestError(`expected ${open} at offset ${start}`);
  let depth = 1;
  let index = start + 1;
  while (index < source.length) {
    const char = source[index];
    if (char === '\'' || char === '"' || char === '`') {
      index = scanQuoted(source, index);
      continue;
    }
    if (source.startsWith('//', index)) {
      const newline = source.indexOf('\n', index + 2);
      index = newline === -1 ? source.length : newline + 1;
      continue;
    }
    if (source.startsWith('/*', index)) {
      const end = source.indexOf('*/', index + 2);
      if (end === -1) throw new ManifestError('unterminated block comment');
      index = end + 2;
      continue;
    }
    if (char === open) depth += 1;
    if (char === close) {
      depth -= 1;
      if (depth === 0) return index + 1;
    }
    index += 1;
  }
  throw new ManifestError(`unterminated ${open}${close} block starting at offset ${start}`);
}

function findRouteObject(source, modulePath) {
  const marker = /\bconst\s+[A-Za-z_$][\w$]*\s*:\s*AppRouteModule\s*=\s*/g;
  const match = marker.exec(source);
  if (!match) throw new ManifestError(`${modulePath} does not declare an AppRouteModule object`);
  const start = skipSpaceAndComments(source, match.index + match[0].length);
  if (source[start] !== '{') throw new ManifestError(`${modulePath} AppRouteModule is not an object literal`);
  const end = scanBalanced(source, start, '{', '}');
  return source.slice(start, end);
}

function readIdentifier(source, start) {
  const match = /^[A-Za-z_$][\w$]*/.exec(source.slice(start));
  if (!match) throw new ManifestError(`expected property name at offset ${start}`);
  return { value: match[0], end: start + match[0].length };
}

function scanPropertyValue(source, start) {
  let index = start;
  let braces = 0;
  let brackets = 0;
  let parentheses = 0;
  while (index < source.length) {
    const char = source[index];
    if (char === '\'' || char === '"' || char === '`') {
      index = scanQuoted(source, index);
      continue;
    }
    if (source.startsWith('//', index)) {
      const newline = source.indexOf('\n', index + 2);
      index = newline === -1 ? source.length : newline + 1;
      continue;
    }
    if (source.startsWith('/*', index)) {
      const end = source.indexOf('*/', index + 2);
      if (end === -1) throw new ManifestError('unterminated block comment');
      index = end + 2;
      continue;
    }
    if (char === '{') braces += 1;
    else if (char === '}') {
      if (braces === 0 && brackets === 0 && parentheses === 0) break;
      braces -= 1;
    } else if (char === '[') brackets += 1;
    else if (char === ']') brackets -= 1;
    else if (char === '(') parentheses += 1;
    else if (char === ')') parentheses -= 1;
    else if (char === ',' && braces === 0 && brackets === 0 && parentheses === 0) break;
    index += 1;
  }
  return index;
}

function parseObjectProperties(objectSource) {
  if (!objectSource.startsWith('{') || !objectSource.endsWith('}')) {
    throw new ManifestError('expected object literal');
  }
  const properties = new Map();
  let index = 1;
  while (index < objectSource.length - 1) {
    index = skipSpaceAndComments(objectSource, index);
    if (objectSource[index] === ',' || objectSource[index] === ';') {
      index += 1;
      continue;
    }
    if (index >= objectSource.length - 1 || objectSource[index] === '}') break;
    const key = readIdentifier(objectSource, index);
    index = skipSpaceAndComments(objectSource, key.end);
    if (objectSource[index] !== ':') {
      throw new ManifestError(`property ${key.value} is not a key/value pair`);
    }
    index = skipSpaceAndComments(objectSource, index + 1);
    const end = scanPropertyValue(objectSource, index);
    properties.set(key.value, objectSource.slice(index, end).trim());
    index = end;
    if (objectSource[index] === ',') index += 1;
  }
  return properties;
}

function splitArrayObjects(arraySource) {
  if (!arraySource.startsWith('[') || !arraySource.endsWith(']')) {
    throw new ManifestError('children must be an array literal');
  }
  const objects = [];
  let index = 1;
  while (index < arraySource.length - 1) {
    index = skipSpaceAndComments(arraySource, index);
    if (arraySource[index] === ',') {
      index += 1;
      continue;
    }
    if (arraySource[index] === ']') break;
    if (arraySource[index] !== '{') {
      throw new ManifestError(`children entry at offset ${index} is not an object literal`);
    }
    const end = scanBalanced(arraySource, index, '{', '}');
    objects.push(arraySource.slice(index, end));
    index = end;
  }
  return objects;
}

function decodeStringLiteral(raw, label) {
  if (!raw) return null;
  const quote = raw[0];
  if ((quote !== '\'' && quote !== '"') || raw[raw.length - 1] !== quote) {
    throw new ManifestError(`${label} must be a quoted string literal; received ${raw}`);
  }
  let result = '';
  for (let index = 1; index < raw.length - 1; index += 1) {
    const char = raw[index];
    if (char !== '\\') {
      result += char;
      continue;
    }
    index += 1;
    if (index >= raw.length - 1) throw new ManifestError(`invalid escape in ${label}`);
    const escaped = raw[index];
    const mapped = { n: '\n', r: '\r', t: '\t', b: '\b', f: '\f', v: '\v', '0': '\0' };
    if (Object.prototype.hasOwnProperty.call(mapped, escaped)) {
      result += mapped[escaped];
    } else if (escaped === 'u') {
      const digits = raw.slice(index + 1, index + 5);
      if (!/^[0-9a-fA-F]{4}$/.test(digits)) throw new ManifestError(`invalid unicode escape in ${label}`);
      result += String.fromCodePoint(Number.parseInt(digits, 16));
      index += 4;
    } else if (escaped === 'x') {
      const digits = raw.slice(index + 1, index + 3);
      if (!/^[0-9a-fA-F]{2}$/.test(digits)) throw new ManifestError(`invalid hex escape in ${label}`);
      result += String.fromCodePoint(Number.parseInt(digits, 16));
      index += 2;
    } else {
      result += escaped;
    }
  }
  return result;
}

function optionalString(properties, key, label) {
  const raw = properties.get(key);
  return raw === undefined ? null : decodeStringLiteral(raw, `${label}.${key}`);
}

function optionalBoolean(properties, key) {
  const raw = properties.get(key);
  if (raw === undefined) return false;
  if (raw === 'true') return true;
  if (raw === 'false') return false;
  throw new ManifestError(`meta.${key} must be a boolean literal; received ${raw}`);
}

function viewImport(componentSource, label) {
  if (!componentSource) return null;
  const matches = [...componentSource.matchAll(/\bimport\(\s*(['"])@\/views\/([^'"\n]+)\1\s*\)/g)];
  if (matches.length > 1) throw new ManifestError(`${label} has multiple dynamic View imports`);
  return matches.length === 1 ? matches[0][2] : null;
}

function joinRoutePath(parentPath, declaredPath) {
  if (declaredPath.startsWith('/')) return declaredPath.replace(/\/{2,}/g, '/');
  const parent = parentPath === '/' ? '' : parentPath.replace(/\/$/, '');
  return `${parent}/${declaredPath}`.replace(/\/{2,}/g, '/');
}

function resolveView(root, imported, label) {
  if (!imported) return null;
  const normalized = imported.replace(/\\/g, '/');
  const segments = normalized.toLowerCase().split('/');
  if (segments.some((segment) => FORBIDDEN_SEGMENTS.has(segment))) {
    throw new ManifestError(`${label} references forbidden non-product View path: ${imported}`);
  }
  const base = path.join(root, 'src', 'views', normalized);
  const candidates = [
    base,
    `${base}.vue`,
    `${base}.tsx`,
    path.join(base, 'index.vue'),
    path.join(base, 'index.tsx'),
  ];
  if (!candidates.some((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile())) {
    throw new ManifestError(`${label} View cannot resolve: ${imported}`);
  }
  return normalized;
}

function parseRoute(objectSource, context) {
  const properties = parseObjectProperties(objectSource);
  const declaredPath = optionalString(properties, 'path', context.label);
  const name = optionalString(properties, 'name', context.label);
  if (declaredPath === null) throw new ManifestError(`${context.label} is missing path`);
  if (name === null) throw new ManifestError(`${context.label} is missing name`);
  const fullPath = joinRoutePath(context.parentPath, declaredPath);
  const redirect = optionalString(properties, 'redirect', context.label);
  const imported = resolveView(
    context.root,
    viewImport(properties.get('component'), context.label),
    context.label,
  );
  const metaRaw = properties.get('meta');
  const meta = metaRaw ? parseObjectProperties(metaRaw) : new Map();
  const route = {
    declared_path: declaredPath,
    full_path: fullPath,
    name,
    redirect,
    view_import: imported,
    hide_menu: optionalBoolean(meta, 'hideMenu'),
    keep_alive: optionalBoolean(meta, 'keepAlive'),
  };
  const routes = [route];
  const childrenRaw = properties.get('children');
  if (childrenRaw) {
    for (const [index, child] of splitArrayObjects(childrenRaw).entries()) {
      routes.push(
        ...parseRoute(child, {
          ...context,
          parentPath: fullPath,
          label: `${context.label}.children[${index}]`,
        }),
      );
    }
  }
  return routes;
}


module.exports = { ManifestError, findRouteObject, parseRoute };
