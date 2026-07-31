<template>
  <div>
    <CurTabs :options="curTabOptions" v-model:value="curTabVal" />
    <div class="flex justify-end pb-2">
      <div @click="go('/log/risk')" class="color-third cursor-pointer">风险处理日志</div>
    </div>
    <BasicTable
      v-show="curTabVal === 0"
      :is-scroll="false"
      @register="registerTable"
      body-padding=""
    />
    <BasicTable
      v-show="curTabVal === 1"
      :scroll="{ x: 1440, y: 'max-content' }"
      @register="registerTable2"
      body-padding=""
    />
    <!-- 谷歌验证 -->
    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </div>
</template>
<script lang="tsx" setup>
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { ref, watch, nextTick } from 'vue';
  import CurTabs from '@/components/Tabs/src/curTabs.vue';
  import { BasicTable, useTable } from '@/components/Table';
  import { getBasicColumns, getBasicColumns2 } from '../data';
  import { getRiskRecords, postRiskRecords } from '@/api/risk/risk';
  import { useApiBasic } from '@/hooks/web/useApi';
  import { useGo } from '@/hooks/web/usePage';
  import { useEventBus, useIntervalFn } from '@vueuse/core';

  const { emit: emitBus } = useEventBus('riskChange');

  const visibleGoogle = ref(false); // google验证码
  const refGoogle = ref();
  let curParams = {};

  const go = useGo();

  const curTabVal = ref(0);
  const curTabOptions = [
    {
      label: '待处理风险',
      value: 0,
    },
    {
      label: '已处理风险',
      value: 1,
    },
  ];

  const [registerTable, { reload }] = useTable({
    useSearchForm: false,
    immediate: false,
    api: getRiskRecords,
    showLoading: false,
    beforeFetch: (params) => {
      params.isProcessed = false;
      return params;
    },
    columns: getBasicColumns(onAction),
    showIndexColumn: false,
  });
  const [registerTable2, { reload: reload2 }] = useTable({
    useSearchForm: false,
    immediate: false,
    api: getRiskRecords,
    showLoading: false,
    beforeFetch: (params) => {
      params.isProcessed = true;
      return params;
    },
    columns: getBasicColumns2(),
    showIndexColumn: false,
  });

  const { pause, resume } = useIntervalFn(
    () => {
      reloadAll();
    },
    60000,
    { immediate: false },
  );
  watch(
    curTabVal,
    () => {
      nextTick(() => {
        pause();
        reloadAll();
        resume();
      });
    },
    { immediate: true },
  );
  function reloadAll() {
    if (curTabVal.value === 0) {
      reload();
    } else {
      reload2();
    }
  }
  function onAction(params: any) {
    console.log('onAction====', params);
    switch (params.type) {
      case 'ignore':
        curParams = {
          id: params?.data?.id,
          action: 'ignore',
        };
        visibleGoogle.value = true;
        break;
      case 'jump':
        go(`/product/index/${params?.data?.productId}?active=${2}`);
        break;
      default:
        break;
    }
  }
  function handleClickConfirm(params: any) {
    const _params = { ...curParams, ...params };
    useApiBasic({
      apiFn: postRiskRecords(_params),
      successFn: () => {
        setTimeout(() => {
          reload();
          emitBus(_params.id);
        }, 1500);
      },
      finallyFn: () => {
        visibleGoogle.value = false;
      },
    });
  }
</script>
