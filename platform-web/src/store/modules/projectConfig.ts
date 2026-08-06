import { defineStore } from 'pinia';
import { PROJ_CFG_KEY } from '@/enums/cacheEnum';
import { Persistent } from '@/utils/cache/persistent';

interface ProjectConfigState {
  optionsMap: Recordable;
  currentSymbolInfo: any;
  currentSymbolFutureInfo: any;
  currentSymbolMt5Info: any;
}

function readProjectConfig(): Partial<ProjectConfigState> {
  return Persistent.getSession<ProjectConfigState>(PROJ_CFG_KEY) || {};
}

// 自定义项目配置
export const useProjectConfigStore = defineStore({
  id: 'app-project-config',
  state: (): ProjectConfigState => ({
    // 下拉数据
    optionsMap: {},
    // 交易-当前标的信息
    currentSymbolInfo: null,
    // 交易-期货-当前标的信息
    currentSymbolFutureInfo: null,
    // 交易-mt5-当前标的信息
    currentSymbolMt5Info: null,
  }),
  getters: {
    getProjectConfig(state): ProjectConfigState {
      return { ...state, ...readProjectConfig() } as ProjectConfigState;
    },
    getOptionsMap(state): Recordable {
      const sessionMap = readProjectConfig().optionsMap || {};
      return { ...sessionMap, ...state.optionsMap };
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
    setOptionsMap(val: Recordable | null) {
      this.optionsMap = val || {};
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, false, 60 * 60 * 1000);
    },
    setCurrentSymbolInfo(val: any) {
      this.currentSymbolInfo = val || null;
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, true, 60 * 60 * 1000);
    },
    setCurrentSymbolFutureInfo(val: any) {
      this.currentSymbolFutureInfo = val || null;
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, true, 60 * 60 * 1000);
    },
    setCurrentSymbolMt5Info(val: any) {
      this.currentSymbolMt5Info = val || null;
      Persistent.setSession(PROJ_CFG_KEY, this.$state as any, true, 60 * 60 * 1000);
    },
  },
});
