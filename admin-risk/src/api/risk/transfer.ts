import { defHttp } from '@/utils/http/axios';

enum Api {
  MANUAL_REVIEW = '/transfer/api/v1/manual-review/',
  REQUESTS = '/transfer/api/v1/transfer-requests/',
  THRESHOLDS = '/transfer/api/v1/thresholds/',
}

export const getTransferRequests = (params?: any) => defHttp.get({ url: Api.REQUESTS, params });
export const postTransferRequests = (data?: any) =>
  defHttp.post(
    {
      url: Api.REQUESTS,
      data,
      responseType: 'blob',
    },
    {
      isReturnNativeResponse: true,
    },
  );
export const getThresholds = (params?: any) => defHttp.get({ url: Api.THRESHOLDS, params });
export const postThresholds = (data?: any) => defHttp.post({ url: Api.THRESHOLDS, data });
export const postManualReview = (data?: any) => defHttp.post({ url: Api.MANUAL_REVIEW, data });
