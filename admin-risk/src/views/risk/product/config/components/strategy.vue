<template>
  <div>
    <SimpleContainer>
      <template #title>
        <div class="color-secondary text-sm pt-1">全局风险因子</div>
      </template>
      <!-- <template #action>
      <Button size="small" type="primary" @click="() => handleAdd()">新增</Button>
    </template> -->
      <BasicTable :is-scroll="false" @register="registerTable" body-padding="">
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
    </SimpleContainer>
    <!-- 编辑 -->
    <EditModal ref="editModal" @success="editSuccess" :record="curCreate" :productId="productId" />
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
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getStrategyColumns } from '../data';
  import { Button } from 'ant-design-vue';
  import EditModal from './strategyEdit.vue';
  import { ref } from 'vue';
  import { getProductConfig, postProductConfig } from '@/api/risk/settings';
  import { useApiBasic } from '@/hooks/web/useApi';
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';

  const props = defineProps({
    productId: {
      type: [String, Number],
      default: '',
    },
  });
  const visibleGoogle = ref(false); // google验证码
  const refGoogle = ref();
  let curParams = {};

  const curCreate = ref<any>();
  const editModal = ref();
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getProductConfig,
    columns: getStrategyColumns(),
    beforeFetch: (params) => {
      params.productId = props.productId;
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
      apiFn: postProductConfig(_params),
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
</script>
