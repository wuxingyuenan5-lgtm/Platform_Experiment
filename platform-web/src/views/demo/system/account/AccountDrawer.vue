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
    <BasicForm @register="registerForm">
      <template #account="{ model, field }">
        <BasicTree
          v-model:value="model[field]"
          :treeData="treeData"
          :fieldNames="{ title: 'menuName', key: 'id' }"
          checkable
          :checkStrictly="true"
          toolbar
          title="交易账号"
        />
      </template>
    </BasicForm>
  </BasicDrawer>
</template>
<script lang="ts" setup>
  import { ref, computed, unref } from 'vue';
  import { BasicModal, useModalInner } from '@/components/Modal';
  import { BasicForm, useForm } from '@/components/Form';
  import { accountFormSchema } from './account.data';
  import { postAccounts } from '@/api/quantSystem';
  import { useMessage } from '@/hooks/web/useMessage';
  import { BasicDrawer, useDrawerInner } from '@/components/Drawer';
  import { BasicTree, TreeItem } from '@/components/Tree';

  defineOptions({ name: 'AccountModal' });

  const emit = defineEmits(['success', 'register']);

  const isUpdate = ref(true);
  const treeData = ref<TreeItem[]>([]);
  const rowId = ref('');

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
        productId: Number(data.record.productId),
      });
    }
    console.log('data===', data);

    // const treeData = await getDeptList();
    updateSchema([
      {
        field: 'productId',
        dynamicDisabled: unref(isUpdate),
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
      await postAccountsFn(values);
      // closeModal();
      // emit('success', { isUpdate: unref(isUpdate), values: { ...values, id: rowId.value } });
    } finally {
      setDrawerProps({ confirmLoading: false });
    }
  }
  async function postAccountsFn(params: any) {
    try {
      loading.value = true;
      const res = await postAccounts(params);
      if (res.retCode == 0) {
        createMessage.success({
          content: '操作成功',
          key: 'postAccounts',
          duration: 2,
        });
        closeDrawer();
        emit('success');
      } else {
        createMessage.error({
          content: res.msg || '操作失败',
          key: 'postAccounts',
          duration: 2,
        });
      }
    } finally {
      loading.value = false;
    }
  }
</script>
