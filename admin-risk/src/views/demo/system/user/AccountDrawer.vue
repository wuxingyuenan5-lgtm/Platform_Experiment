<template>
  <BasicDrawer
    v-bind="$attrs"
    @register="registerDrawer"
    :confirm-loading="loading"
    :title="getTitle"
    showFooter
    width="500px"
    @ok="handleSubmit"
  >
    <BasicForm @register="registerForm" />
  </BasicDrawer>
</template>
<script lang="ts" setup>
  import { ref, computed, unref } from 'vue';
  import { BasicForm, useForm } from '@/components/Form';
  import { accountFormSchema } from './account.data';
  import { postAccountList, getProducts } from '@/api/demo/system';
  import { useMessage } from '@/hooks/web/useMessage';
  import { BasicDrawer, useDrawerInner } from '@/components/Drawer';
  import { hasOwn } from '@vueuse/shared';
  // import { BasicTree, TreeItem } from '@/components/Tree';
  // import { getAccounts } from '@/api/quantSystem';

  defineOptions({ name: 'AccountModal' });

  const emit = defineEmits(['success', 'register']);

  const isUpdate = ref(true);
  // const treeData = ref<TreeItem[]>([]);
  // const rowId = ref('');

  let curId: any = null;
  const loading = ref(false);
  const { createMessage } = useMessage();

  const [registerForm, { setFieldsValue, updateSchema, resetFields, validate }] = useForm({
    labelWidth: 90,
    baseColProps: { span: 24 },
    schemas: accountFormSchema,
    showActionButtonGroup: false,
  });
  const [registerDrawer, { setDrawerProps, closeDrawer }] = useDrawerInner(async (data) => {
    curId = null;
    resetFields();
    setDrawerProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;

    if (unref(isUpdate)) {
      curId = data.record.id;
      // rowId.value = data.record.id;
      setFieldsValue({
        ...data.record,
      });
    }
    console.log('data===', data);

    // const _accountsRes = await getProducts();
    // if (_accountsRes?.retCode == 0) {
    //   treeData.value = _accountsRes.data?.map((item: any) => {
    //     return {
    //       ...item,
    //       title: item?.productName + '/' + item?.checkCode,
    //       key: item?.id,
    //     };
    //   });
    // }
    // console.log('treeData===', treeData, curId, !!curId);

    updateSchema([
      {
        field: 'name',
        dynamicDisabled: !!curId,
      },
      {
        field: 'password',
        ifShow: !unref(isUpdate),
      },
    ]);
  });

  const getTitle = computed(() => (!unref(isUpdate) ? '新增' : '编辑'));

  async function handleSubmit() {
    try {
      const values = await validate();
      setDrawerProps({ confirmLoading: true });
      // TODO custom api
      console.log(values);
      if (curId) {
        values.id = curId;
        values.action = 'update';
      }
      if (!hasOwn(values, 'productIds')) {
        values.productIds = [];
      }
      await postAccountListFn(values);
      // closeModal();
      // emit('success', { isUpdate: unref(isUpdate), values: { ...values, id: rowId.value } });
    } finally {
      setDrawerProps({ confirmLoading: false });
    }
  }
  async function postAccountListFn(params: any) {
    try {
      const _params = JSON.parse(JSON.stringify(params));
      loading.value = true;
      const res = await postAccountList(_params);
      if (res.retCode == 0) {
        createMessage.success({
          content: '操作成功',
          key: 'postAccountList',
          duration: 2,
        });
        closeDrawer();
        emit('success');
      } else {
        createMessage.error({
          content: res.msg || '操作失败',
          key: 'postAccountList',
          duration: 2,
        });
      }
    } finally {
      loading.value = false;
    }
  }
</script>
