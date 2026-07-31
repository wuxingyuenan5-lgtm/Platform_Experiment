import { futureHttp } from '@/utils/http/axios';

enum Api {
  FUTURE_STRATEGY_RISK = '/api/v1/strategy/risk/',
  FUTURE_STRATEGY_POSITION = '/api/v1/strategy/position/',
  FUTURE_STRATEGY_RISK_OVERVIEW = '/api/v1/strategy/risk/overview/',
  FUTURE_STRATEGY_CONFIG = '/api/v1/strategy/config/',
  STRATEGY_RISK_SWITCH = '/api/v1/strategy/risk-switch/',
  STRATEGY_SYMBOL_INFO = '/api/v1/strategy/symbol-info/',
  FUTURE_TQSYMBOLINFOLIST = '/api/v1/tqSymbolInfoList/',
  FUTURE_TQPERCENTAGEORDER = '/api/v1/tqPercentageOrder/',
  FUTURE_CANCELTASK = '/api/v1/cancelTask/',
  FUTURE_EXECUTIONlIST = '/api/v1/executionList/',
  FUTURE_TQICELIMIT = '/api/v1/tqIceLimit/',
  FUTURE_TQCHASEPRICELIMIT = '/api/v1/tqChasePriceLimit/',
  FUTURE_TQKLINESERIAL = '/api/v1/tqKlineSerial/',
  FUTURE_TQRISKDATA = '/api/v1/tqRiskData/',
  FUTURE_TQFORWARDCURVE = '/api/v1/tqForwardCurve/',
  FUTURE_TQPRICEDIFFERENCE = '/api/v1/tqPriceDifference/',
  FUTURE_TQQUOTE = '/api/v1/tqQuote/',
  FUTURE_TQCLOSEPOSITION = '/api/v1/tqClosePosition/',
  FUTURE_TQSHORTSELLING = '/api/v1/tqShortSelling/',
  FUTURE_TQBUYMORE = '/api/v1/tqBuyMore/',
  FUTURE_TQACCOUNT = '/api/v1/tqAccount/',
  FUTURE_TQSYMBOLINFO = '/api/v1/tqSymbolInfo/',
  FUTURE_TQSYMBOLLIST = '/api/v1/tqSymbolList/',
  FUTURE_TQINSERTORDER = '/api/v1/tqInsertOrder/',
  FUTURE_TQORDERRECORDS = '/api/v1/tqOrderRecords/',
  FUTURE_TQTRADERECORDS = '/api/v1/tqTradeRecords/',
  FUTURE_TQPOSITION = '/api/v1/tqPosition/',
  FUTURE_TQCURRENTORDER = '/api/v1/tqCurrentOrder/',
  FUTURE_TQCANCELORDER = '/api/v1/tqCancelOrder/',
}
export const postFutureStrategyRisk = (params?: any) =>
  futureHttp.post({
    url: Api.FUTURE_STRATEGY_RISK,
    params,
  });
export const getFutureStrategyPosition = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_STRATEGY_POSITION,
    params,
  });
export const getStrategyRiskOverview = (params?: any) =>
  futureHttp.get(
    {
      url: Api.FUTURE_STRATEGY_RISK_OVERVIEW,
      params,
    },
    { ignoreCancelToken: true },
  );
export const getStrategyConfig = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_STRATEGY_CONFIG,
    params,
  });
export const postStrategyRiskSwitch = (data?: any) =>
  futureHttp.post({
    url: Api.STRATEGY_RISK_SWITCH,
    data,
  });
export const getStrategySymbolInfo = (params?: any) =>
  futureHttp.get({
    url: Api.STRATEGY_SYMBOL_INFO,
    params,
  });
export const getFutureTqSymbolInfoList = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQSYMBOLINFOLIST,
    params,
  });
export const postFutureTqSymbolInfoList = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQSYMBOLINFOLIST,
    data,
  });
export const postFutureTqPercentageOrder = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQPERCENTAGEORDER,
    data,
  });

export const postFutureCancelTask = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_CANCELTASK,
    data,
  });

export const getFutureExecutionList = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_EXECUTIONlIST,
    params,
  });

export const postFutureTqIceLimit = (params?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQICELIMIT,
    params,
  });
export const getFutureTqIceLimit = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQICELIMIT,
    params,
  });

export const getFutureTqChasePriceLimit = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQCHASEPRICELIMIT,
    params,
  });
export const postFutureTqChasePriceLimit = (params?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQCHASEPRICELIMIT,
    params,
  });

export const getFutureTqKlineSerial = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQKLINESERIAL,
    params,
  });

export const getFutureTqRiskData = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQRISKDATA,
    params,
  });
export const getFutureTqForwardCurve = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQFORWARDCURVE,
    params,
  });
export const getFutureTqPriceDifference = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQPRICEDIFFERENCE,
    params,
  });
export const getFutureTqQuote = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQQUOTE,
    params,
  });

export const postFutureTqClosePosition = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQCLOSEPOSITION,
    data,
  });
export const postFutureTqShortSelling = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQSHORTSELLING,
    data,
  });
export const postFutureTqBuyMore = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQBUYMORE,
    data,
  });
export const getFutureTqAccount = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQACCOUNT,
    params,
  });
export const postFutureTqCancelOrder = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQCANCELORDER,
    data,
  });
export const getFutureTqCurrentOrder = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQCURRENTORDER,
    params,
  });
export const postFutureTqCurrentOrder = (data?: any) =>
  futureHttp.post({
    url: Api.FUTURE_TQCURRENTORDER,
    data,
  });
export const getFutureTqPosition = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQPOSITION,
    params,
  });
export const getFutureTqSymbolInfo = (params?: any) =>
  futureHttp.get({
    url: Api.FUTURE_TQSYMBOLINFO,
    params,
  });

export const getFutureTqSymbolList = (params?: any) =>
  futureHttp.get({ url: Api.FUTURE_TQSYMBOLLIST, params });

export const postFutureTqInsertOrder = (data?: any) =>
  futureHttp.post({ url: Api.FUTURE_TQINSERTORDER, data });

export const getFutureTqOrderRecords = (params?: any) =>
  futureHttp.get({ url: Api.FUTURE_TQORDERRECORDS, params });

export const postFutureTqOrderRecords = (data?: any) =>
  futureHttp.post({ url: Api.FUTURE_TQORDERRECORDS, data, responseType: 'blob' });

export const getFutureTqTradeRecords = (params?: any) =>
  futureHttp.get({ url: Api.FUTURE_TQTRADERECORDS, params });

export const postFutureTqTradeRecords = (data?: any) =>
  futureHttp.post({ url: Api.FUTURE_TQTRADERECORDS, data, responseType: 'blob' });
