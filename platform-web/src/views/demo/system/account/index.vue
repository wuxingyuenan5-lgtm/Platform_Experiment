<template>
  <PageWrapper class="rounded" dense contentFullHeight fixedHeight contentClass="flex">
    <!-- <DeptTree class="w-1/4 xl:w-1/5" @select="handleSelect" /> -->
    <BasicTable body-padding="" @register="registerTable" :searchInfo="searchInfo">
      <template #toolbar>
        <a-button type="primary" @click="handleCreate">新增账号</a-button>
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <TableAction
            :actions="[
              // {
              //   icon: 'clarity:info-standard-line',
              //   tooltip: '查看用户详情',
              //   onClick: handleView.bind(null, record),
              // },
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
    <!-- <AccountModal @register="registerModal" @success="handleSuccess" /> -->
    <AccountDrawer @register="registerDrawer" @success="handleSuccess" />
    <!-- 谷歌验证 -->
    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </PageWrapper>
</template>
<script lang="ts" setup>
  import { reactive, ref } from 'vue';
  import { BasicTable, useTable, TableAction } from '@/components/Table';
  import { getAccounts, postAccounts } from '@/api/quantSystem';
  import { PageWrapper } from '@/components/Page';
  import AccountDrawer from './AccountDrawer.vue';
  import { useDrawer } from '@/components/Drawer';
  import { columns, searchFormSchema } from './account.data';
  import { useGo } from '@/hooks/web/usePage';
  import { useMessage } from '@/hooks/web/useMessage';
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { useApiBasic } from '@/hooks/web/useApi';

  // 谷歌验证
  const visibleGoogle = ref(false);
  const refGoogle = ref();
  let curParams = {};
  const handleClickConfirm = (params) => {
    const _params = { ...curParams, ...params };
    postAccountListFn(_params);
  };

  defineOptions({ name: 'AccountManagement' });
  const { createMessage } = useMessage();

  const go = useGo();
  const [registerDrawer, { openDrawer }] = useDrawer();
  const searchInfo = reactive<Recordable>({});
  const [registerTable, { reload, setLoading, updateTableDataRecord }] = useTable({
    title: '账号列表',
    api: getAccounts,
    // rowKey: 'id',
    columns,
    showIndexColumn: false,
    formConfig: {
      labelWidth: 120,
      schemas: searchFormSchema,
      autoSubmitOnEnter: true,
    },
    useSearchForm: false,
    showTableSetting: true,
    bordered: false,
    size: 'small',
    handleSearchInfoFn(info) {
      console.log('handleSearchInfoFn', info);
      return info;
    },
    actionColumn: {
      width: 120,
      title: '操作',
      dataIndex: 'action',
      // slots: { customRender: 'action' },
    },
  });

  function handleCreate() {
    openDrawer(true, {
      isUpdate: false,
    });
  }

  function handleEdit(record: Recordable) {
    console.log(record);
    openDrawer(true, {
      record,
      isUpdate: true,
    });
  }

  function handleDelete(record: Recordable) {
    console.log(record);
    curParams = { action: 'delete', id: record.id };
    visibleGoogle.value = true;
    // postAccountListFn({ action: 'delete', id: record.id });
  }
  async function postAccountListFn(params: any) {
    setLoading(true);
    try {
      const res = await postAccounts(params);
      if (res.retCode == 0) {
        createMessage.success({
          content: '操作成功',
          key: 'postAccountList',
          duration: 2,
        });
        reload();
      } else {
        createMessage.error({
          content: res.msg || '操作失败',
          key: 'postAccountList',
          duration: 2,
        });
      }
    } finally {
      visibleGoogle.value = false;
      setLoading(false);
    }
  }
  function handleSuccess() {
    // if (isUpdate) {
    //   // 演示不刷新表格直接更新内部数据。
    //   // 注意：updateTableDataRecord要求表格的rowKey属性为string并且存在于每一行的record的keys中
    //   const result = updateTableDataRecord(values.id, values);
    //   console.log(result);
    // } else {
    reload();
    // }
  }

  function handleSelect(deptId = '') {
    searchInfo.deptId = deptId;
    reload();
  }

  function handleView(record: Recordable) {
    go('/system/account_detail/' + record.id);
  }
</script>
