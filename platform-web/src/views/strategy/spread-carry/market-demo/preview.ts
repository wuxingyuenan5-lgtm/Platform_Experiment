import { createApp } from 'vue';
import '../../shared/strategy-theme.less';
import CrossSpreadMarketDemo from './CrossSpreadMarketDemo.vue';

// Local preview of the same page, without starting platform auth or API services.
createApp(CrossSpreadMarketDemo).mount('#app');
