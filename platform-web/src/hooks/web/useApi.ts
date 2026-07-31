import { useMessage } from '@/hooks/web/useMessage';

const { createMessage } = useMessage();

interface ApiBasicConfig {
  apiFn: Promise<any>;
  successFn?: () => void;
  errorFn?: () => void;
  finallyFn?: () => void;
}
// 快速接口调用
export async function useApiBasic(ApiBasicConfig: ApiBasicConfig) {
  let result: any;
  try {
    result = await ApiBasicConfig.apiFn;
    if (result.retCode == 0) {
      ApiBasicConfig?.successFn?.();
      createMessage.success({
        content: '操作成功',
        key: '_save_fake_data',
        duration: 2,
      });
    } else {
      ApiBasicConfig?.errorFn?.();
      createMessage.error({
        content: result?.msg || result?.retMsg || '操作失败',
        key: '_save_fake_data',
        duration: 2,
      });
    }
  } catch (error) {
    // TODO 网络问题居多
    ApiBasicConfig?.errorFn?.();
  } finally {
    ApiBasicConfig?.finallyFn?.();
  }
  return {
    result,
  };
}
