import { dataHttp } from '@/utils/http/axios';

enum Api {
  PRODUCT_NAV_PLATFORMNETVALUELIST = '/product/navplatformNetValueList',
  PRODUCT_NAV_PRODUCTRATIO = '/product/nav/productRatio',
  PRODUCT_NAV_FUNDINGRATIO = '/product/nav/fundingRatio',
  PRODUCT_NAV_SHFEDRAWDOWN = '/product/nav/shfeDrawdown',
  PRODUCT_NAV_DRAWDOWN = '/product/nav/drawdown',
  PRODUCT_NAV_LIST = '/product/nav/list',
}

export const getProductNavplatformNetValueList = (params?: any) =>
  dataHttp.get({ url: Api.PRODUCT_NAV_PLATFORMNETVALUELIST, params });
export const getProductNavProductRatio = (params?: any) =>
  dataHttp.get({ url: Api.PRODUCT_NAV_PRODUCTRATIO, params });
export const getProductNavFundingRatio = (params?: any) =>
  dataHttp.get({ url: Api.PRODUCT_NAV_FUNDINGRATIO, params });
export const getProductNavShfeDrawdown = (params?: any) =>
  dataHttp.get({ url: Api.PRODUCT_NAV_SHFEDRAWDOWN, params }, { ignoreCancelToken: true });
export const getProductNavDrawdown = (params?: any) =>
  dataHttp.get({ url: Api.PRODUCT_NAV_DRAWDOWN, params }, { ignoreCancelToken: true });
export const getProductNavList = (params?: any) =>
  dataHttp.get({ url: Api.PRODUCT_NAV_LIST, params });
