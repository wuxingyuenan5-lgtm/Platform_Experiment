import { defHttp } from '@/utils/http/axios';

enum Api {
  ACCOUNT_CONFIG = '/settings/api/v1/account-config/',
  PRODUCT_CONFIG = '/settings/api/v1/product-config/',
  GLOBAL_CONFIG = '/settings/api/v1/global-config/',
}
export const getAccountConfig = (params?: any) =>
  defHttp.get({ url: Api.ACCOUNT_CONFIG, params }, { ignoreCancelToken: true });
export const postAccountConfig = (params?: any) =>
  defHttp.post({ url: Api.ACCOUNT_CONFIG, params });
export const getProductConfig = (params?: any) =>
  defHttp.get({ url: Api.PRODUCT_CONFIG, params }, { ignoreCancelToken: true });
export const postProductConfig = (data?: any) => defHttp.post({ url: Api.PRODUCT_CONFIG, data });
export const getGlobalConfig = (params?: any) => defHttp.get({ url: Api.GLOBAL_CONFIG, params });
export const postGlobalConfig = (data?: any) => defHttp.post({ url: Api.GLOBAL_CONFIG, data });
