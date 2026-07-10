<template>
  <div>
    <div class="flex justify-between items-center pb-2">
      <CurTabs size="small" :options="curAccountTabOptions" v-model:value="curTabVal">
        <template #label="{ item }">{{ item?.platform }}-{{ item?.label }}</template>
      </CurTabs>
      <!-- <Button size="small" type="primary" @click="() => handleAdd()">新增</Button> -->
    </div>

    <BasicTable @register="registerTable" body-padding="">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div class="flex items-center gap-4">
            <div
              @click="handleAdd({ ...record, productId: props.productId })"
              class="text-#2C97EB cursor-pointer"
              >编辑</div
            >
            <div
              @click="handleEdit(record)"
              v-if="!record?.isActive"
              class="cursor-pointer text-#2FB97B"
              >启用</div
            >
            <div @click="handleEdit(record)" v-else class="cursor-pointer text-#FF4D4F">禁用</div>
          </div>
        </template>
      </template>
    </BasicTable>

    <!-- 编辑 -->
    <EditModal ref="editModal" @success="editSuccess" :record="curCreate" :accountId="curTabVal" />
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
  import CurTabs from '@/components/Tabs/src/curTabs.vue';
  import { BasicTable, useTable } from '@/components/Table';
  import { getStrategyColumns } from '../data';
  import { Button } from 'ant-design-vue';
  import EditModal from './accountEdit.vue';
  import { ref, computed, watch, nextTick } from 'vue';
  import { getAccountConfig, postAccountConfig } from '@/api/risk/settings';
  import { useApiBasic } from '@/hooks/web/useApi';
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { useUserStore } from '@/store/modules/user';

  const props = defineProps({
    // productId: {
    //   type: [String, Number],
    //   default: '',
    // },
    account: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
  });
  console.log('account----accountElm', props.account);

  const visibleGoogle = ref(false); // google验证码
  const refGoogle = ref();
  let curParams = {};
  // 当前产品下账号信息
  // const userStore = useUserStore();
  const curTabVal = ref();
  // const curTabOptions = computed(() => {
  //   const _product = userStore.getUserInfoAccount?.filter(
  //     (item) => item.id == props.productId,
  //   )?.[0];
  //   return (
  //     _product?.children?.map((item) => {
  //       return {
  //         label: item.label,
  //         value: item.checkCode,
  //         platform: item.platform,
  //       };
  //     }) || []
  //   );
  // });
  const curAccountTabOptions = computed(() => {
    if (!props.account || JSON.stringify(props.account) === '{}') {
      return [];
    }
    return [
      {
        label: props.account?.checkCode,
        value: props.account?.id,
        platform: props.account?.platform,
      },
    ];
  });
  console.log('curAccountTabOptions---', curAccountTabOptions);

  const curCreate = ref<any>();
  const editModal = ref();
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: false,
    api: getAccountConfig,
    columns: getStrategyColumns(),
    beforeFetch: (params) => {
      params.accountId = curTabVal.value;
      return params;
    },
    showIndexColumn: false,
    actionColumn: {
      width: 240,
      title: '操作',
      dataIndex: 'action',
      // slots: { customRender: 'action' },
    },
  });
  function handleAdd(params?: any) {
    curCreate.value = params;
    editModal.value.openModal(true);
  }
  function editSuccess(params: any) {
    reload();
    editModal.value.openModal(false);
  }
  function handleClickConfirm(params: any) {
    const _params = { ...curParams, ...params, action: 'toggle', isActive: !curParams.isActive };
    useApiBasic({
      apiFn: postAccountConfig(_params),
      successFn() {
        reload();
      },
      finallyFn() {
        visibleGoogle.value = false;
      },
    });
  }
  function handleEdit(params: any) {
    curParams = params;
    visibleGoogle.value = true;
  }
  watch(
    () => curAccountTabOptions.value,
    (val) => {
      if (val && val.length > 0) {
        curTabVal.value = val[0].value;
        nextTick(() => {
          reload();
        });
      }
    },
    { immediate: true, deep: true },
  );
  watch(
    () => curTabVal.value,
    () => {
      reload();
    },
  );
</script>
