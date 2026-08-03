import { defHttp } from '@/utils/http/axios';

enum Api {
  NOTIFICATION = '/notifications/api/v1/messages/',
}
export const getNtification = (params?: any) => defHttp.get({ url: Api.NOTIFICATION, params });

export const postNtification = (data?: any) => defHttp.post({ url: Api.NOTIFICATION, data });
