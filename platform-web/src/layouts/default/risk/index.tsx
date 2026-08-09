import { ref } from 'vue';
import { ExclamationCircleFilled } from '@ant-design/icons-vue';
import { useGo } from '@/hooks/web/usePage';

export function riskInit() {
  const dataSource: any = ref([]);
  const go = useGo();
  const msgKeyMax: any = 1;
  function renderItem(key?: any, params?: any) {
    // console.log('key---', params);

    return (
      <span class="flex justify-between  text-sm">
        <div class="flex items-center">
          <ExclamationCircleFilled style="color: #FF4D4F;" class="mr-2" />
          <div class="text-left">{key}</div>
        </div>
        {params?.riskType != 'OTHER' && (
          <div
            onClick={() => jump(params)}
            class="text-#EB6E2C cursor-pointer text-nowrap flex items-center ml-4"
          >
            去处理
          </div>
        )}
      </span>
    );
  }
  function jump(params?: any) {
    console.log('jump', params);
    go(`/product/index/${params?.productId}?active=${2}`);
  }
  function renderMsg() {
    if (dataSource.value?.length) {
      // console.log('renderMsg---', dataSource);
      return (
        <div class="risk-msg">
          {dataSource.value?.slice(0, msgKeyMax)?.map((item: any) => {
            const _content = `${item?.productName}/${item?.accountCode}，风险因子：【${item?.riskFactor}】，当前为【${item?.triggerData}】，触发了【${item?.riskLevelDisplay}风险】`;
            const _otherKey = `风险因子：【${item?.riskFactor}】，当前为【${item?.triggerData}】，触发了【${item?.riskLevelDisplay}风险】`;
            // const _key = item?.id || index;
            return (
              <div class="risk-msg_item">
                {renderItem(item?.riskType == 'OTHER' ? _otherKey : _content, item)}
              </div>
            );
          })}
        </div>
      );
    }
    return <div></div>;
  }
  return {
    renderMsg,
  };
}
