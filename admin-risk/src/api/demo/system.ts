import {
  AccountParams,
  DeptListItem,
  MenuParams,
  RoleParams,
  RolePageParams,
  MenuListGetResultModel,
  DeptListGetResultModel,
  AccountListGetResultModel,
  RolePageListGetResultModel,
  RoleListGetResultModel,
} from './model/systemModel';
import { defHttp } from '@/utils/http/axios';

const _baseVersion = '/auth_system/api/v1/admin';

enum Api {
  RoleTest = _baseVersion + '/rolesTest/',
  PRODUCTS = _baseVersion + '/products/',
  AccountList = _baseVersion + '/users/',
  IsAccountExist = '/quantSystem/accountExist',
  DeptList = '/quantSystem/getDeptList',
  setRoleStatus = '/quantSystem/changeRoleStatus/',
  MenuList = _baseVersion + '/menus/',
  RolePageList = _baseVersion + '/roles/',
  GetAllRoleList = '/quantSystem/getAllRoleList',
}
// export const getRolesTest = (params?: any) => monitorHttp.get({ url: Api.RoleTest, params });
export const getProducts = (params?: any) => defHttp.get({ url: Api.PRODUCTS, params });
export const postProducts = (data?: any) => defHttp.post({ url: Api.PRODUCTS, data });

export const getAccountList = (params?: AccountParams) =>
  defHttp.get<AccountListGetResultModel>({ url: Api.AccountList, params });

export const postAccountList = (params?: AccountParams) =>
  defHttp.post({ url: Api.AccountList, params });

export const getDeptList = (params?: DeptListItem) =>
  defHttp.get<DeptListGetResultModel>({ url: Api.DeptList, params });

export const getMenuList = (params?: MenuParams) =>
  defHttp.get<MenuListGetResultModel>({ url: Api.MenuList, params });

export const postMenuList = (data?: any) => defHttp.post({ url: Api.MenuList, data });

export const getRoleListByPage = (params?: RolePageParams) =>
  defHttp.get<RolePageListGetResultModel>({ url: Api.RolePageList, params });

export const postRoleListByPage = (data?: any) => defHttp.post({ url: Api.RolePageList, data });

export const getAllRoleList = (params?: RoleParams) =>
  defHttp.get<RoleListGetResultModel>({ url: Api.RolePageList, params });

export const setRoleStatus = (params?: any) => defHttp.get({ url: Api.setRoleStatus, params });

export const isAccountExist = (account: string) =>
  defHttp.post({ url: Api.IsAccountExist, params: { account } }, { errorMessageMode: 'none' });
