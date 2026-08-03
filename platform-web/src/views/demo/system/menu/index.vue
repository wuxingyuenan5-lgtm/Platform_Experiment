<template>
  <div class="rounded">
    <BasicTable body-padding="" @register="registerTable" @fetch-success="onFetchSuccess">
      <template #toolbar>
        <a-button type="primary" @click="handleCreate"> 新增菜单 </a-button>
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <TableAction
            :actions="[
              {
                icon: 'clarity:note-edit-line',
                onClick: handleEdit.bind(null, record),
              },
              {
                icon: 'ant-design:delete-outlined',
                color: 'error',
                popConfirm: {
                  title: '是否确认删除',
                  placement: 'left',
                  confirm: handleDelete.bind(null, record),
                },
              },
            ]"
          />
        </template>
      </template>
    </BasicTable>
    <MenuDrawer @register="registerDrawer" @success="handleSuccess" />
  </div>
</template>
<script lang="ts" setup>
  import { nextTick } from 'vue';

  import { BasicTable, useTable, TableAction } from '@/components/Table';
  import { getMenuList, postMenuList } from '@/api/demo/system';

  import { useDrawer } from '@/components/Drawer';
  import MenuDrawer from './MenuDrawer.vue';
  import { useMessage } from '@/hooks/web/useMessage';

  import { columns, searchFormSchema } from './menu.data';

  defineOptions({ name: 'MenuManagement' });
  const { createMessage } = useMessage();

  const [registerDrawer, { openDrawer }] = useDrawer();
  const [registerTable, { reload, setLoading, expandAll }] = useTable({
    title: '菜单列表',
    api: getMenuList,
    columns,
    formConfig: {
      labelWidth: 120,
      schemas: searchFormSchema,
    },
    isTreeTable: true,
    pagination: true,
    striped: false,
    useSearchForm: false,
    showTableSetting: true,
    bordered: false,
    size: 'small',
    showIndexColumn: false,
    canResize: false,
    actionColumn: {
      width: 80,
      title: '操作',
      dataIndex: 'action',
      // slots: { customRender: 'action' },
      fixed: undefined,
    },
  });

  function handleCreate() {
    openDrawer(true, {
      isUpdate: false,
    });
  }

  function handleEdit(record: Recordable) {
    openDrawer(true, {
      record,
      isUpdate: true,
    });
  }

  function handleDelete(record: Recordable) {
    console.log(record);
    postMenuListFn({ action: 'delete', id: record.id });
  }
  async function postMenuListFn(params: any) {
    setLoading(true);
    try {
      const res = await postMenuList(params);
      if (res.retCode == 0) {
        createMessage.success({
          content: '操作成功',
          key: 'postMenuList',
          duration: 2,
        });
        reload();
      } else {
        createMessage.error({
          content: res.msg || '操作失败',
          key: 'postMenuList',
          duration: 2,
        });
      }
    } finally {
      setLoading(false);
    }
  }
  function handleSuccess() {
    reload();
  }

  function onFetchSuccess() {
    // 演示默认展开所有表项
    nextTick(expandAll);
  }
</script>
