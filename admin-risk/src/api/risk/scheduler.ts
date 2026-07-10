import { defHttp } from '@/utils/http/axios';

enum Api {
  SCHEDULER_LIST = '/scheduler/api/v1/list/',
}
export const getSchedulerList = (params?: any) => defHttp.get({ url: Api.SCHEDULER_LIST, params });
export const postSchedulerList = (data?: any) => defHttp.post({ url: Api.SCHEDULER_LIST, data });
