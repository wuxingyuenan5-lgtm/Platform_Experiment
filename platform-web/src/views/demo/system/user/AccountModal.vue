<template>
  <BasicModal
    v-bind="$attrs"
    @register="registerModal"
    :confirm-loading="loading"
    :title="getTitle"
    @ok="handleSubmit"
  >
    <BasicForm @register="registerForm" />
  </BasicModal>
</template>
<script lang="ts" setup>
  import { ref, computed, unref } from 'vue';
  import { BasicModal, useModalInner } from '@/components/Modal';
  import { BasicForm, useForm } from '@/components/Form';
  import { accountFormSchema } from './account.data';
  import { getDeptList, postAccountList } from '@/api/demo/system';
  import { useMessage } from '@/hooks/web/useMessage';

  defineOptions({ name: 'AccountModal' });

  const emit = defineEmits(['success', 'register']);

  const isUpdate = ref(true);
  const rowId = ref('');

  let curId: any = null;
  const loading = ref(false);
  const { createMessage } = useMessage();

  const [registerForm, { setFieldsValue, updateSchema, resetFields, validate }] = useForm({
    labelWidth: 100,
    baseColProps: { span: 24 },
    schemas: accountFormSchema,
    showActionButtonGroup: false,
    actionColOptions: {
      span: 23,
    },
  });

  const [registerModal, { setModalProps, closeModal }] = useModalInner(async (data) => {
    curId = null;
    resetFields();
    setModalProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;

    if (unref(isUpdate)) {
      curId = data.record.id;
      // rowId.value = data.record.id;
      setFieldsValue({
        ...data.record,
      });
    }
    console.log('data===', data);

    // const treeData = await getDeptList();
    updateSchema([
      {
        field: 'userName',
        dynamicDisabled: !!curId,
      },
      {
        field: 'password',
        ifShow: !unref(isUpdate),
      },
      // {
      //   field: 'dept',
      //   componentProps: { treeData },
      // },
    ]);
  });

  const getTitle = computed(() => (!unref(isUpdate) ? '新增账号' : '编辑账号'));

  async function handleSubmit() {
    try {
      const values = await validate();
      setModalProps({ confirmLoading: true });
      // TODO custom api
      console.log(values);
      if (curId) {
        values.id = curId;
        values.action = 'update';
      }
      await postAccountListFn(values);
      // closeModal();
      // emit('success', { isUpdate: unref(isUpdate), values: { ...values, id: rowId.value } });
    } finally {
      setModalProps({ confirmLoading: false });
    }
  }
  async function postAccountListFn(params: any) {
    try {
      loading.value = true;
      const res = await postAccountList(params);
      if (res.retCode == 0) {
        createMessage.success({
          content: '操作成功',
          key: 'postAccountList',
          duration: 2,
        });
        closeModal();
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
