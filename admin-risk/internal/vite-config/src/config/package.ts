import { readPackageJSON } from 'pkg-types';
import { defineConfig, mergeConfig, type UserConfig } from 'vite';
import { commonConfig } from './common';

interface DefineOptions {
  overrides?: UserConfig;
  options?: {
    //
  };
}

function definePackageConfig(defineOptions: DefineOptions = {}) {
  const { overrides = {} } = defineOptions;
  const root = process.cwd();
  return defineConfig(async ({ mode }) => {
    const { dependencies = {}, peerDependencies = {} } = await readPackageJSON(root);
    const isBuild = mode === 'production' || process.env.NODE_ENV === 'production';
    let dtsPlugin = [] as any[];
    if (isBuild) {
      // lazy-load vite-plugin-dts so dev server doesn't try to resolve api-extractor
      try {
        // dynamic import to avoid resolving at module load time
        const mod = await import('vite-plugin-dts');
        const dts = (mod && (mod.default || mod)) as any;
        dtsPlugin = [
          dts({
            logLevel: 'error',
          }),
        ];
      } catch (e) {
        // ignore if plugin not available in this environment
        dtsPlugin = [];
      }
    }

    const packageConfig: UserConfig = {
      build: {
        lib: {
          entry: 'src/index.ts',
          formats: ['es'],
          fileName: () => 'index.mjs',
        },
        rollupOptions: {
          external: [...Object.keys(dependencies), ...Object.keys(peerDependencies)],
        },
      },
      plugins: dtsPlugin,
    };
    const mergedConfig = mergeConfig(commonConfig(mode), packageConfig);

    return mergeConfig(mergedConfig, overrides);
  });
}

export { definePackageConfig };
