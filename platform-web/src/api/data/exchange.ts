import { dataHttp } from '@/utils/http/axios';

enum Api {
  EXCHANGE = '/exchange/',
}
export const getDataExchange = (params?: any) => dataHttp.get({ url: Api.EXCHANGE, params });
