import { defHttp } from '@/utils/http/axios';

enum Api {
  EXE_CONVERTER = '/execution/api/v1/converter/',
  EXE_POSITION_BALANCE = '/execution/api/v1/positions/balance/',
  EXE_LEVERAGE_RATIO = '/execution/api/v1/total-leverage-ratio/',
  EXE_SYMBOLS = '/execution/api/v1/symbols/',
  EXE_TASKS_DETAIL = '/execution/api/v1/tasks/detail/',
  EXE_TASKS = '/execution/api/v1/tasks/',
  EXE_POSITION = '/execution/api/v1/positions/',
  EXE_ALL_POSITION = '/execution/api/v1/all-positions/',
  EXE_POSITION_CLOSE = '/execution/api/v1/positions/close/',
}
export const getConverter = (params?: any) => defHttp.get({ url: Api.EXE_CONVERTER, params });

export const getPositionsBalance = (params?: any) =>
  defHttp.get({ url: Api.EXE_POSITION_BALANCE, params }, { ignoreCancelToken: true });

export const getTotalLeverageRatio = (params?: any) =>
  defHttp.get({ url: Api.EXE_LEVERAGE_RATIO, params }, { ignoreCancelToken: true });

export const getExecutionTasksSymbols = (params?: any) =>
  defHttp.get({ url: Api.EXE_SYMBOLS, params });

export const getExecutionTasks = (params?: any) => defHttp.get({ url: Api.EXE_TASKS, params });
export const getExecutionTasksDetail = (params?: any) =>
  defHttp.get({ url: Api.EXE_TASKS_DETAIL, params });
export const getExecutionPositionsClose = (params?: any) =>
  defHttp.get({ url: Api.EXE_POSITION_CLOSE, params });
export const postExecutionPositionsClose = (data?: any) =>
  defHttp.post({ url: Api.EXE_POSITION_CLOSE, data });
export const getExecutionAllPositions = (params?: any) =>
  defHttp.get({ url: Api.EXE_ALL_POSITION, params }, { ignoreCancelToken: true });
export const getExecutionPositions = (params?: any) =>
  defHttp.get({ url: Api.EXE_POSITION, params });
