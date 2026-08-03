import { defHttp } from '@/utils/http/axios';

enum Api {
  DEMO_LIST = '/strategy/target',
}

/**
 * @description: Get sample list value
 */

export const getTarget = () =>
  defHttp.get({
    url: Api.DEMO_LIST,
    headers: {
      // @ts-ignore
      ignoreCancelToken: true,
    },
  });
