import base from '../playwright.hedge-board.config';
import path from 'node:path';
const servers = Array.isArray(base.webServer) ? base.webServer : [base.webServer!];
export default {
  ...base,
  testDir: path.resolve(process.cwd(), 'e2e/hedge-board'),
  outputDir: path.resolve(process.cwd(), 'test-results/cross-asset-preview'),
  webServer: servers.map((server, index) =>
    index === servers.length - 1
      ? {
          ...server,
          command:
            'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4437 --strictPort --outDir dist',
        }
      : server,
  ),
};
