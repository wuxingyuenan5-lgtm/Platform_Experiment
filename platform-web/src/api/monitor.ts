import { monitorHttp } from '@/utils/http/axios';
// import { TickerListResultModel } from './model/tickerModel';
// import { RateListResultModel } from './model/rateModel';
// import { FundingRateListResultModel } from './model/fundingRateModel';
// import { WalletbalanceSumListResultModel } from './model/walletbalanceModel';

enum Api {
  // CRYPTO_ACCOUNT_RISK = '/monitor/api/v1/crypto-account-risk/',
  // CRYPTORISKMONITOR = '/monitor/api/v1/cryptoRiskMonitor/',
  // SHARPRATE = '/monitor/api/v1/sharpRate/',
  // CRYPTOMULTIBALANCE = '/monitor/api/v1/cryptoMultiBalance/',
  // FINANCIALOVERVIEW = '/monitor/api/v1/financialOverview/',
  // USD2CNY = '/monitor/api/v1/usd2cny/',
  // MONITOR_ALLPOSITION = '/monitor/allPosition/',
  // MONITOR_TRANSACTIONLOGDIRECT = '/monitor/transactionLogDirect/',
  // MONITOR_GETASSETDATATOTAL = '/monitor/getAssetsDataTotal/',
  // MONITOR_CREATEASSETDATA = '/monitor/createAssetsData/',
  // MONITOR_ASSETDATA = '/monitor/assetsData/',
  // MONITOR_GETASSETDATA = '/monitor/getAssetsData/',
  // MONITOR_HOMEPAGE = '/monitor/homePage/',
  // MONITOR_ASSETAVERAGEPRICE = '/monitor/assetAveragePrice/',
  // MONITOR_ASSETQUANTITY = '/monitor/assetQuantity/',
  // MONITOR_PRICEDIFF = '/monitor/priceDiff/',
  // MONITOR_TOTALEQUITYOVERVIEW = '/monitor/api/v1/accountEquity/',
  // MONITOR_WALLETBALANCEINFOOVERVIEW = '/monitor/walletbalanceInfoOverview/',
  // MONITOR_RISKINDICATORSOVERVIEW = '/monitor/riskIndicatorsOverview/',
  // MONITOR_ARBITRAGEMONITOROVERVIEW = '/monitor/arbitrageMonitorOverview/',
  // MONITOR_CURRENCY = '/monitor/currency/',
  // MONITOR_CHECKCODE = '/monitor/checkCode/',
  // MONITOR_EXECUTIONSINFOFIRECT = '/monitor/executionsInfoDirect/',
  // MONITOR_ASSERTDIRECT = '/monitor/assertDirect/',
  // MONITOR_POSITION = '/monitor/position/',
  // MONITOR_POSITIONDIRECT = '/monitor/positionDirect/',
  // MONITOR_WALLETBALANCECOIN = '/monitor/walletbalanceCoin/',
  // MONITOR_WALLETBALANCESUM = '/monitor/walletbalanceSum/',
  // MONITOR_WALLETBALANCESUMLITE = '/monitor/walletbalanceSumLite/',
  // MONITOR_TICKERDIRECT = '/monitor/tickerDirect/',
  // MONITOR_TICKER = '/monitor/ticker/',
  // MONITOR_RATE = '/monitor/rate/',
  // MONITOR_FUNDINGRATE = '/monitor/fundingRate/',
  // MONITOR_BORROWRATE = '/monitor/borrowRate/',
  MONITOR_SYMBOLSELECT = '/monitor/symbolSelect/',
  // MONITOR_SYMBOL = '/monitor/symbol/',
  // MONITOR_WALLETBALANCE = '/monitor/walletbalance/',
  // MONITOR_WALLETBALANCELITE = '/monitor/walletbalanceLite/',
  // MONITOR_TEST = '/monitor/test/',
  // MONITOR_HISTORYORDERINFODIRECT = '/monitor/orderHistoryInfoDirect/',
}
// // export const getCryptoAccountRisk = (params?: any) =>
// //   monitorHttp.get({ url: Api.CRYPTO_ACCOUNT_RISK, params }, { ignoreCancelToken: true });

// export const getCryptoRiskMonitor = (params?: any) =>
//   monitorHttp.get({ url: Api.CRYPTORISKMONITOR, params });

// export const getSharpRate = (params?: any) => monitorHttp.get({ url: Api.SHARPRATE, params });

// export const getCryptoMultiBalance = (params?: any) =>
//   monitorHttp.get({ url: Api.CRYPTOMULTIBALANCE, params });

// // export const getFinancialOverview = (params?: any) =>
// //   monitor2Http.get({ url: Api.FINANCIALOVERVIEW, params });

// export const getUsd2cny = (params?: any) => monitorHttp.get({ url: Api.USD2CNY, params });

// export const getAllPosition = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_ALLPOSITION, params });

// export const getTransactionLogDirect = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_TRANSACTIONLOGDIRECT, params });

// export const postTransactionLogDirect = (data?: any) =>
//   monitorHttp.post({ url: Api.MONITOR_TRANSACTIONLOGDIRECT, data, responseType: 'blob' });

// export const getAssetsDataTotal = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_GETASSETDATATOTAL, params });

// export const createAssetsData = (data?: any) =>
//   monitorHttp.post({ url: Api.MONITOR_CREATEASSETDATA, data });

// export const postAssetsData = (data?: any) =>
//   monitorHttp.post({ url: Api.MONITOR_ASSETDATA, data });

// export const getAssetsData = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_ASSETDATA, params });

// export const getAssetsDataOld = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_GETASSETDATA, params });

// export const getMonitorHomePage = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_HOMEPAGE, params });

// export const postMonitorAssetAveragePrice = (data?: any) =>
//   monitorHttp.post({ url: Api.MONITOR_ASSETAVERAGEPRICE, data });

// export const getMonitorAssetAveragePrice = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_ASSETAVERAGEPRICE, params });

// export const getMonitorAssetQuantity = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_ASSETQUANTITY, params });

// export const getMonitorPriceDiff = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_PRICEDIFF, params });

// export const getTotalEquityOverview = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_TOTALEQUITYOVERVIEW, params });

// export const getWalletbalanceInfoOverview = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_WALLETBALANCELITE, params });

// export const getRiskIndicatorsOverview = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_RISKINDICATORSOVERVIEW, params });

// export const getArbitrageMonitorOverview = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_ARBITRAGEMONITOROVERVIEW, params });

// export const getCurrency = (params?: any) => monitorHttp.get({ url: Api.MONITOR_CURRENCY, params });

// export const getCheckCode = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_CHECKCODE, params });

// export const getExecutionsInfoDirect = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_EXECUTIONSINFOFIRECT, params });

// export const postExecutionsInfoDirect = (data?: any) =>
//   monitorHttp.post({ url: Api.MONITOR_EXECUTIONSINFOFIRECT, data, responseType: 'blob' });

// export const getPosition = (params?: any) => monitorHttp.get({ url: Api.MONITOR_POSITION, params });

// export const getPositionDirect = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_POSITIONDIRECT, params });

// export const getAssertDirect = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_ASSERTDIRECT, params });

// export const getWalletbalanceCoin = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_WALLETBALANCECOIN, params });

// export const getWalletbalanceSumLite = (params?: any) =>
//   monitorHttp.get<WalletbalanceSumListResultModel>({
//     url: Api.MONITOR_WALLETBALANCESUMLITE,
//     params,
//   });

// export const getWalletbalanceSum = (params?: any) =>
//   monitorHttp.get<WalletbalanceSumListResultModel>({ url: Api.MONITOR_WALLETBALANCESUM, params });

// export const getTickerDirect = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_TICKERDIRECT, params });

// export const getHistoryOrderInfoDirect = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_HISTORYORDERINFODIRECT, params });

// export const postHistoryOrderInfoDirect = (data?: any) =>
//   monitorHttp.post({ url: Api.MONITOR_HISTORYORDERINFODIRECT, data, responseType: 'blob' });

// export const getMonitorTest = (params?: any) => monitorHttp.get({ url: Api.MONITOR_TEST, params });

// export const getMonitorWalletbalanceLite = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_WALLETBALANCELITE, params });

// export const getMonitorWalletbalance = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_WALLETBALANCE, params });

// export const getMonitorSymbol = (params?: any) =>
//   monitorHttp.get({ url: Api.MONITOR_SYMBOL, params });

// export const postMonitorSymbol = (data?: any) =>
//   monitorHttp.post({ url: Api.MONITOR_SYMBOL, data });

export const getMonitorSymbolSelect = (params?: any) =>
  monitorHttp.get({ url: Api.MONITOR_SYMBOLSELECT, params });

// export const getMonitorBorrowRate = (params?: any) =>
//   monitorHttp.get<FundingRateListResultModel>({ url: Api.MONITOR_BORROWRATE, params });

// export const getMonitorFundingRate = (params?: any) =>
//   monitorHttp.get<FundingRateListResultModel>({ url: Api.MONITOR_FUNDINGRATE, params });

// export const getMonitorTicker = () =>
//   monitorHttp.get<TickerListResultModel>({ url: Api.MONITOR_TICKER });

// export const getMonitorRate = () => monitorHttp.get<RateListResultModel>({ url: Api.MONITOR_RATE });
