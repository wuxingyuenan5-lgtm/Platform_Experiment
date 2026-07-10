<template>
  <BasicDrawer
    v-bind="$attrs"
    @register="registerDrawer"
    showFooter
    :title="getTitle"
    width="50%"
    :confirm-loading="loading"
    @ok="handleSubmit"
  >
    <BasicForm @register="registerForm" />
  </BasicDrawer>
</template>
<script lang="ts" setup>
  import { ref, computed, unref } from 'vue';
  import { BasicForm, useForm } from '@/components/Form';
  import { formSchema } from './menu.data';
  import { BasicDrawer, useDrawerInner } from '@/components/Drawer';
  import { useMessage } from '@/hooks/web/useMessage';

  import { getMenuList, postMenuList } from '@/api/demo/system';

  defineOptions({ name: 'MenuDrawer' });

  const emit = defineEmits(['success', 'register']);

  const isUpdate = ref(true);

  let curId: any = null;
  const loading = ref(false);
  const { createMessage } = useMessage();
  const [registerForm, { resetFields, setFieldsValue, updateSchema, validate }] = useForm({
    labelWidth: 100,
    schemas: formSchema,
    showActionButtonGroup: false,
    baseColProps: { lg: 12, md: 24 },
  });

  const [registerDrawer, { setDrawerProps, closeDrawer }] = useDrawerInner(async (data) => {
    curId = null;
    resetFields();
    setDrawerProps({ confirmLoading: false });
    isUpdate.value = !!data?.isUpdate;

    if (unref(isUpdate)) {
      curId = data.record.id;
      setFieldsValue({
        ...data.record,
      });
    }
    const treeData = await getMenuList();
    // console.log("treeData===",treeData);
    console.log('data===', data);

    updateSchema({
      field: 'parentId',
      componentProps: { treeData: treeData?.data },
    });
  });

  const getTitle = computed(() => (!unref(isUpdate) ? '新增菜单' : '编辑菜单'));

  async function handleSubmit() {
    try {
      const values = await validate();
      setDrawerProps({ confirmLoading: true });
      // TODO custom api
      // console.log(values);
      if (curId) {
        values.id = curId;
        values.action = 'update';
      }
      await postMenuListFn(values);
    } finally {
      setDrawerProps({ confirmLoading: false });
    }
  }
  async function postMenuListFn(params: any) {
    try {
      loading.value = true;
      const res = await postMenuList(params);
      if (res.retCode == 0) {
        createMessage.success({
          content: '操作成功',
          key: 'postMenuList',
          duration: 2,
        });
        closeDrawer();
        emit('success');
      } else {
        createMessage.error({
          content: res.msg || '操作失败',
          key: 'postMenuList',
          duration: 2,
        });
      }
    } finally {
      loading.value = false;
    }
  }
</script>
