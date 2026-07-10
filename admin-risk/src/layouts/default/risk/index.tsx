import { message, notification } from 'ant-design-vue';
import { nextTick, onMounted, ref, watch } from 'vue';
import { ExclamationCircleFilled } from '@ant-design/icons-vue';
import { getRiskRecords } from '@/api/risk/risk';
import { useGo } from '@/hooks/web/usePage';
import { useEventBus, useIntervalFn } from '@vueuse/core';
import { useRoute } from 'vue-router';
import { AxiosCanceler } from '@/utils/http/axios/axiosCancel';

export function riskInit() {
  const route = useRoute();
  const dataSource: any = ref();
  const go = useGo();
  const { on } = useEventBus('riskChange');
  const msgKeyList: any = [];
  const msgKeyMax: any = 1;
  const canceler = new AxiosCanceler();
  function initData() {
    getRiskRecordsFn();
  }
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
  function close(key?: any) {
    // message.destroy(key);
    // 删除指定id 数据
    const index = dataSource.value.findIndex((item: any) => item.id == key);
    if (index > -1) {
      dataSource.value.splice(index, 1);
    }
  }
  function getRiskRecordsFn() {
    getRiskRecords({ isProcessed: false, pageSize: 5 }).then((res) => {
      if (res.retCode == 0) {
        dataSource.value = res?.data?.list;
      }
    });
  }
  function renderMsg() {
    if (dataSource.value?.length) {
      // console.log('renderMsg---', dataSource);
      return (
        <div class="risk-msg">
          {dataSource.value?.slice(0, msgKeyMax)?.map((item: any, index: number) => {
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
  const { pause, resume } = useIntervalFn(
    () => {
      initData();
    },
    60000,
    { immediate: false },
  );
  onMounted(() => {
    initData();
    resume();
  });
  on((key) => close(key));
  watch(
    () => route.path,
    (cur) => {
      if (cur.includes('/home')) {
        // 首页时间间隔重新计算
        canceler?.removeAllPending();
        initData();
        pause();
        nextTick(() => {
          resume();
        });
      }
    },
  );
  return {
    renderMsg,
  };
}
