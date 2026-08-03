import { readFileSync } from 'node:fs';
import { dirname, extname, resolve } from 'node:path';

import { generate } from '@ant-design/colors';
// @ts-ignore: typo
/* import { getThemeVariables } from 'ant-design-vue/dist/theme'; */
import { theme } from 'ant-design-vue/lib';
import convertLegacyToken from 'ant-design-vue/lib/theme/convertLegacyToken';

const { defaultAlgorithm, defaultSeed } = theme;
const primaryColor = '#1890FF';

function generateAntColors(color: string, theme: 'default' | 'dark' = 'default') {
  return generate(color, {
    theme,
  });
}

function resolveLessImport(baseDir: string, requestPath: string) {
  if (/^[a-z]+:/i.test(requestPath)) {
    return requestPath;
  }
  if (extname(requestPath)) {
    return resolve(baseDir, requestPath);
  }
  return resolve(baseDir, `${requestPath}.less`);
}

function inlineLessReferences(entryPath: string, seen = new Set<string>()) {
  const absolutePath = resolve(entryPath);
  if (seen.has(absolutePath)) {
    return '';
  }
  seen.add(absolutePath);

  const source = readFileSync(absolutePath, 'utf-8');
  const currentDir = dirname(absolutePath);

  return source.replace(
    /@import(?:\s+\(reference\))?\s+['"]([^'"]+)['"];?/g,
    (_match, importPath) => {
      if (importPath.startsWith('~')) {
        return '';
      }
      return inlineLessReferences(resolveLessImport(currentDir, importPath), seen);
    },
  );
}

/**
 * less global variable
 */
export function generateModifyVars() {
  const palettes = generateAntColors(primaryColor);
  const primary = palettes[5];
  const primaryColorObj: Record<string, string> = {};

  for (let index = 0; index < 10; index++) {
    primaryColorObj[`primary-${index + 1}`] = palettes[index];
  }
  // const modifyVars = getThemeVariables();
  const mapToken = defaultAlgorithm(defaultSeed);
  const v3Token = convertLegacyToken(mapToken);
  return {
    ...v3Token,
    'primary-color': primary,
    ...primaryColorObj,
    'info-color': primary,
    'processing-color': primary,
    'success-color': '#52C41A', //  Success color
    'error-color': '#FF4D4F', //  False color
    'warning-color': '#FAAD14', //   Warning color
    'font-size-base': '14px', //  Main font size
    'border-radius-base': '2px', //  Component/float fillet
    'link-color': primary, //   Link color
  };
}

export function getSharedLessSource() {
  return inlineLessReferences(resolve('src/design/config.less'));
}
