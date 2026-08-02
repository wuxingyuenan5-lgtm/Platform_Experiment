import type { BasicFetchResult, BasicPageParams } from '@/api/model/baseModel';

import { defHttp } from '@/utils/http/axios';

export type AccountParams = BasicPageParams & {
  account?: string;
  nickname?: string;
  [key: string]: any;
};

export interface AccountListItem {
  id: string;
  account: string;
  email: string;
  nickname: string;
  role: number;
  createTime: string;
  remark: string;
  status: number;
}

export type AccountListGetResultModel = BasicFetchResult<AccountListItem>;

const ACCOUNT_LIST_URL = '/auth_system/api/v1/admin/users/';

export const getAccountList = (params?: AccountParams) =>
  defHttp.get<AccountListGetResultModel>({ url: ACCOUNT_LIST_URL, params });
