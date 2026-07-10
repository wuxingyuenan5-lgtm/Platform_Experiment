import { defHttp } from '@/utils/http/axios';

enum Api {
  ACCOUNT_DATA = '/monitoring/api/v1/account-risk/',
  PRODUCT_DATA = '/monitoring/api/v1/product-data/',
  PRODUCT_RISK = '/monitoring/api/v1/product-risk/',
  PRODUCT_PROPORTION = '/monitoring/api/v1/crypto-product-proportion/',
  CRYPTO_ACCOUNT_RISK = '/monitoring/api/v1/crypto-account-risk/',
  SERVICES = '/monitoring/services/',
  PRODUCT_EQUITY_CURVE = '/monitor/api/v1/product-equity-curve/',
}
export const getAccountData = (params?: any) => defHttp.get({ url: Api.ACCOUNT_DATA, params });
export const getProductData = (params?: any) => defHttp.get({ url: Api.PRODUCT_DATA, params });
export const postProductData = (data?: any) =>
  defHttp.post(
    { url: Api.PRODUCT_DATA, data, responseType: 'blob' },
    {
      isReturnNativeResponse: true,
    },
  );

export const getProductRisk = (params?: any) =>
  defHttp.get({ url: Api.PRODUCT_RISK, params }, { ignoreCancelToken: true });

export const getCryptoProductProportion = (params?: any) =>
  defHttp.get({ url: Api.PRODUCT_PROPORTION, params }, { ignoreCancelToken: true });

export const getCryptoAccountRisk = (params?: any) =>
  defHttp.get({ url: Api.CRYPTO_ACCOUNT_RISK, params }, { ignoreCancelToken: true });

export const getMonitoringServices = () => defHttp.get({ url: Api.SERVICES });
// export const getProductEquityCurve = (params?: any) =>
//   monitorHttp.get({ url: Api.PRODUCT_EQUITY_CURVE, params });
