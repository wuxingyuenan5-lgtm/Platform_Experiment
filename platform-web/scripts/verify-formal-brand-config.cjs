const fs = require('node:fs');
const path = require('node:path');

const FORMAL_APP_TITLE = '全球变量金融平台';
const EXPECTED_PRODUCTION_CONFIG_VARIABLE =
  '__PRODUCTION__5168740353D891CF91D1878D5E7353F0__CONF__';
const CONFIG_RELATIVE_PATH = 'dist/_app.config.js';
const configPath = path.resolve(__dirname, '..', CONFIG_RELATIVE_PATH);

if (!fs.existsSync(configPath)) {
  throw new Error(`Built application config is missing: ${CONFIG_RELATIVE_PATH}`);
}

const source = fs.readFileSync(configPath, 'utf8');
const expectedTitleEntry = `"VITE_GLOB_APP_TITLE":"${FORMAL_APP_TITLE}"`;
const expectedWindowAssignment = `window.${EXPECTED_PRODUCTION_CONFIG_VARIABLE}=`;

if (!source.includes(expectedTitleEntry)) {
  throw new Error(
    `Built application config does not contain the formal title ${FORMAL_APP_TITLE}`,
  );
}

if (!source.includes(expectedWindowAssignment)) {
  throw new Error(
    `Built application config does not use ${EXPECTED_PRODUCTION_CONFIG_VARIABLE}`,
  );
}

if (source.includes('"VITE_GLOB_APP_TITLE":"Platform"')) {
  throw new Error('Built application config still uses the generic engineering title Platform');
}

console.log(
  `Formal brand build configuration verified: ${FORMAL_APP_TITLE} / ${EXPECTED_PRODUCTION_CONFIG_VARIABLE}`,
);
