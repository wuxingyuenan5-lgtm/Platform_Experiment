import { createApp } from 'vue';

import { registerGlobComp } from '@/components/registerGlobComp';
import { setupGlobDirectives } from '@/directives';
import { setupI18n } from '@/locales/setupI18n';
import { setupErrorHandle } from '@/logics/error-handle';
import { initAppConfigStore } from '@/logics/initAppConfig';
import { router, setupRouter } from '@/router';
import { setupRouterGuard } from '@/router/guard';
import { setupStore } from '@/store';

import App from './App.vue';

async function bootstrap() {
  const app = createApp(App);

  setupStore(app);
  initAppConfigStore();
  registerGlobComp(app);
  await setupI18n(app);
  setupRouter(app);
  setupRouterGuard(router);
  setupGlobDirectives(app);
  setupErrorHandle(app);

  app.mount('#app');
}

bootstrap();
