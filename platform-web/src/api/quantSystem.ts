import { defHttp } from '@/utils/http/axios';

const _baseVersion = '/api/v1';

enum Api {
  QUANTSYSTEM_ACCOUNTS = '/auth_system/api/v1/admin/accounts/',
  QUANTSYSTEM_USERELACCOUNTS = _baseVersion + '/quantSystem/management/userRelAccounts/',
  QUANTSYSTEM_OPERATIONLOGS = '/audit/api/v1/operation-logs/',
  QUANTSYSTEM_PROJECTLOGS = '/audit/api/v1/project-logs/',
  QUANTSYSTEM_QSTRANSFER = '/v1/quantSystem/qsTransfer/',
  QUANTSYSTEM_QSTRANSFERGSLNTERTRANSFER = '/v1/quantSystem/qsInterTransfer/',
}
export const getProjectLogs = (params?: any) =>
  defHttp.get({ url: Api.QUANTSYSTEM_PROJECTLOGS, params });
export const getAccounts = (params?: any) => defHttp.get({ url: Api.QUANTSYSTEM_ACCOUNTS, params });
export const postAccounts = (data?: any) => defHttp.post({ url: Api.QUANTSYSTEM_ACCOUNTS, data });
export const getUserRelAccounts = (params?: any) =>
  defHttp.get({ url: Api.QUANTSYSTEM_USERELACCOUNTS, params });

export const getOperationLogs = (params?: any) =>
  defHttp.get({ url: Api.QUANTSYSTEM_OPERATIONLOGS, params });
export const postOperationLogs = (data?: any) =>
  defHttp.post({ url: Api.QUANTSYSTEM_OPERATIONLOGS, data, responseType: 'blob' });

export const postQuantSystemQsTransfer = (data?: any) =>
  defHttp.post({ url: Api.QUANTSYSTEM_QSTRANSFER, data });

export const postQuantSystemQslnterTransfer = (data?: any) =>
  defHttp.post({ url: Api.QUANTSYSTEM_QSTRANSFERGSLNTERTRANSFER, data });
