import { defHttp } from '@/utils/http/axios';
import { PricediffModel } from './model/pricediffModel';

enum Api {
  STRATEGYLIST = '/pricediff/strategyList/',
  STRATEGYSTOPALL = '/pricediff/strategyStopAll/',
  STRATEGYBOARD = '/pricediff/strategyBoard/',
  STRATEGYSTATUSANDTIME = '/pricediff/strategyStatusAndTime/',
  DIFFSTRATEGYEDIT = '/pricediff/diffStrategyEdit/',
  FUNDINGSTRATEGYEDIT = '/pricediff/fundingStrategyEdit/',
  FUNDINGSTRATEGYRESTART = '/pricediff/fundingStrategyRestart/',
  DIFFSTRATEGYRESTART = '/pricediff/diffStrategyRestart/',
  // STRATEGYMANAGE = '/pricediff/strategyManage/',
  STRATEGYMANAGE = '/strategy/api/v1/cryptoStrategy/',
  DIFF_IN = '/pricediff/diff_in/',
  PRICEDIF_SYMBOL = '/pricediff/symbols/',
  STRATEGY_PARAM_OVERVIEW = '/pricediff/strategyParamOverview/',
}
export const getStrategyList = (params?: any) => defHttp.get({ url: Api.STRATEGYLIST, params });

export const getStrategyStopAll = (params?: any) =>
  defHttp.get({ url: Api.STRATEGYSTOPALL, params });

export const getStrategyBoard = (params?: any) => defHttp.get({ url: Api.STRATEGYBOARD, params });

export const getStrategyStatusAndTime = (params?: any) =>
  defHttp.get({ url: Api.STRATEGYSTATUSANDTIME, params });

export const postDiffStrategyEdit = (data) => defHttp.post({ url: Api.DIFFSTRATEGYEDIT, data });
export const postFundingStrategyEdit = (data) =>
  defHttp.post({ url: Api.FUNDINGSTRATEGYEDIT, data });

export const getFundingStrategyRestart = (params?: any) =>
  defHttp.get({ url: Api.FUNDINGSTRATEGYRESTART, params });
export const getDiffStrategyRestart = (params?: any) =>
  defHttp.get({ url: Api.DIFFSTRATEGYRESTART, params });
export const getStrategyManage = (params?: any) => defHttp.get({ url: Api.STRATEGYMANAGE, params });

export const postStrategyManage = (data?: any) => defHttp.post({ url: Api.STRATEGYMANAGE, data });

export const getStrategyParamOverview = (params?: any) =>
  defHttp.get({ url: Api.STRATEGY_PARAM_OVERVIEW, params });

export const getDiffIn = () => defHttp.get({ url: Api.DIFF_IN });

export const getPricedifSymbols = (params?: any) =>
  defHttp.get({ url: Api.PRICEDIF_SYMBOL, params });
