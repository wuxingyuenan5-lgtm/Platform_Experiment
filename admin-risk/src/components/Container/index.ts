import { withInstall } from '@/utils';
import collapseContainer from './src/collapse/CollapseContainer.vue';
import simpleContainer from './src/collapse/SimpleContainer.vue';
import panelContainer from './src/collapse/PanelContainer.vue';
import scrollContainer from './src/ScrollContainer.vue';

export const PanelContainer = withInstall(panelContainer);
export const SimpleContainer = withInstall(simpleContainer);
export const CollapseContainer = withInstall(collapseContainer);
export const ScrollContainer = withInstall(scrollContainer);

export * from './src/typing';
