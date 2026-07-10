import { defineStore } from 'pinia';
import { Persistent } from '@/utils/cache/persistent';
import { PROJ_CFG_KEY } from '@/enums/cacheEnum';

interface ProjectConfigState {
  optionsMap: any;
  currentSymbolInfo: any;
  currentSymbolFutureInfo: any;
  currentSymbolMt5Info: any;
}
// 自定义项目配置
export const useProjectConfigStore = defineStore({
  id: 'app-project-config',
  state: (): ProjectConfigState => ({
    // 下拉数据
    optionsMap: null,
    // 交易-当前标的信息
    currentSymbolInfo: null,
    // 交易-期货-当前标的信息
    currentSymbolFutureInfo: null,
    // 交易-mt5-当前标的信息
    currentSymbolMt5Info: null,
  }),
  getters: {
    getProjectConfig(state): ProjectConfigState {
      return state || Persistent.getSession(PROJ_CFG_KEY) || ({} as ProjectConfigState);
    },
    getOptionsMap(state): any {
      const _mapSession = Persistent.getSession(PROJ_CFG_KEY)?.optionsMap || {};
      const _map = state.optionsMap || {};
      return { ..._mapSession, ..._map };
    },
    getCurrentSymbolInfo(state): any {
      return state.currentSymbolInfo || this.getProjectConfig.currentSymbolInfo || null;
    },
    getCurrentSymbolFutureInfo(state): any {
      return state.currentSymbolFutureInfo || this.getProjectConfig.currentSymbolFutureInfo || null;
    },
    getCurrentSymbolMt5Info(state): any {
      return state.currentSymbolMt5Info || this.getProjectConfig.currentSymbolMt5Info || null;
    },
  },
  actions: {
    setOptionsMap(val: any) {
      this.optionsMap = val ? val : {};
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, false, 60 * 60 * 1000);
    },
    setCurrentSymbolInfo(val: any) {
      this.currentSymbolInfo = val ? val : null;
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, true, 60 * 60 * 1000);
    },
    setCurrentSymbolFutureInfo(val: any) {
      this.currentSymbolFutureInfo = val ? val : null;
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, true, 60 * 60 * 1000);
    },
    setCurrentSymbolMt5Info(val: any) {
      this.currentSymbolMt5Info = val ? val : null;
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, true, 60 * 60 * 1000);
    },
  },
});
