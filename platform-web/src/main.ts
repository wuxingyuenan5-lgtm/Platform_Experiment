import 'uno.css';
// import '@/components/VxeTable/src/css/index.scss';
import 'ant-design-vue/dist/reset.css';
// Register icon sprite
import 'virtual:svg-icons-register';
import '@/design/index.less';

import * as VueRuntime from 'vue';

if (typeof globalThis !== 'undefined') {
  // Some legacy <script lang="tsx"> SFCs are compiled without retaining Vue API imports.
  Object.assign(globalThis as Record<string, unknown>, VueRuntime);
}

void import('./bootstrap');
