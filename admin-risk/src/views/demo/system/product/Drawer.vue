<template>
  <BasicDrawer
    v-bind="$attrs"
    @register="registerDrawer"
    showFooter
    :title="getTitle"
    width="500px"
    :confirm-loading="loading"
    @ok="handleSubmit"
  >
    <BasicForm @register="registerForm">
      <template #menu="{ model, field }">
        <BasicTree
          v-model:value="model[field]"
          :treeData="treeData"
          :fieldNames="{ title: 'name', key: 'id' }"
          checkable
          :checkStrictly="true"
          toolbar
          title="菜单分配"
        />
      </template>
    </BasicForm>
  </BasicDrawer>
</template>
<script lang="ts" setup>
  import { ref, computed, unref } from 'vue';
  import { BasicForm, useForm } from '@/components/Form';
  import { formSchema } from './data';
  import { BasicDrawer, useDrawerInner } from '@/components/Drawer';
  import { useMessage } from '@/hooks/web/useMessage';
  import { BasicTree, TreeItem } from '@/components/Tree';

  import { postProducts, getMenuList } from '@/api/demo/system';

  const emit = defineEmits(['success', 'register']);
  const isUpdate = ref(true);
  const treeData = ref<TreeItem[]>([]);
  let curId: any = null;
  const loading = ref(false);
  const { createMessage } = useMessage();
  const [registerForm, { resetFields, setFieldsValue, validate }] = useForm({
    labelWidth: 90,
    baseColProps: { span: 24 },
    schemas: formSchema,
    showActionButtonGroup: false,
  });

  const [registerDrawer, { setDrawerProps, closeDrawer }] = useDrawerInner(async (data) => {
    curId = null;
    resetFields();
    setDrawerProps({ confirmLoading: false });
    // 需要在setFieldsValue之前先填充treeData，否则Tree组件可能会报key not exist警告
    if (unref(treeData).length === 0) {
      getMenuList().then((res) => {
        if (res?.data?.length > 0) {
          treeData.value =
            (res?.data?.find((item) => item.route === '/product')?.children as any as TreeItem[]) ||
            [];
        }
      });
    }
    isUpdate.value = !!data?.isUpdate;
    if (unref(isUpdate)) {
      curId = data.record.id;
      setFieldsValue({
        ...data.record,
      });
    }
  });

  const getTitle = computed(() => (!unref(isUpdate) ? '新增' : '编辑'));

  async function handleSubmit() {
    try {
      const values = await validate();
      setDrawerProps({ confirmLoading: true });
      // TODO custom api
      console.log(values);
      // const _params = values
      if (curId) {
        values.id = curId;
        values.action = 'update';
      }
      postProductsFn(values);
    } finally {
      setDrawerProps({ confirmLoading: false });
    }
  }
  async function postProductsFn(params: any) {
    try {
      const _params = JSON.parse(JSON.stringify(params));
      if (_params?.menuIds?.checked) {
        _params.menuIds = _params?.menuIds?.checked;
      }
      console.log('params===', _params);
      loading.value = true;
      const res = await postProducts(_params);
      if (res.retCode == 0) {
        createMessage.success({
          content: '操作成功',
          key: 'postRoleListByPage',
          duration: 2,
        });
        closeDrawer();
        emit('success');
      } else {
        createMessage.error({
          content: res.msg || '操作失败',
          key: 'postRoleListByPage',
          duration: 2,
        });
      }
    } finally {
      loading.value = false;
    }
  }
</script>
