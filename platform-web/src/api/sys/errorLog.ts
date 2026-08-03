import { defHttp } from '@/utils/http/axios';

const ERROR_URL = '/error';

export const fireErrorApi = () => defHttp.get({ url: ERROR_URL });
