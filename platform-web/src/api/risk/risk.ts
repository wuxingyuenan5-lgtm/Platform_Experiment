import { defHttp } from '@/utils/http/axios';

enum Api {
  RISK_RECORDS = '/risk/api/v1/risk-records/',
  RISK_RECORDS_EXPORT = '/risk/api/v1/risk-records/export/',
}
export const getRiskRecords = (params?: any) => defHttp.get({ url: Api.RISK_RECORDS, params });
export const postRiskRecords = (params?: any) => defHttp.post({ url: Api.RISK_RECORDS, params });
export const postRiskRecordsExport = (data?: any) =>
  defHttp.post(
    {
      url: Api.RISK_RECORDS_EXPORT,
      data,
      responseType: 'blob',
    },
    {
      isReturnNativeResponse: true,
    },
  );
