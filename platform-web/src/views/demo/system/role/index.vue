<template>
  <div class="rounded">
    <BasicTable body-padding="" @register="registerTable">
      <template #toolbar>
        <a-button type="primary" @click="handleCreate"> 新增角色 </a-button>
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

    <RoleDrawer @register="registerDrawer" @success="handleSuccess" />

    <!-- 谷歌验证 -->
    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </div>
</template>
<script lang="ts" setup>
  import { BasicTable, useTable, TableAction } from '@/components/Table';
  import { getRoleListByPage, postRoleListByPage } from '@/api/demo/system';

  import { useDrawer } from '@/components/Drawer';
  import RoleDrawer from './RoleDrawer.vue';
  import { useMessage } from '@/hooks/web/useMessage';

  import { columns, searchFormSchema } from './role.data';
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { ref } from 'vue';
  import { useApiBasic } from '@/hooks/web/useApi';
  // 谷歌验证
  const visibleGoogle = ref(false);
  const refGoogle = ref();
  let curParams = {};
  const handleClickConfirm = (params) => {
    const _params = { ...curParams, ...params };
    postRoleListByPageFn(_params);
  };

  defineOptions({ name: 'RoleManagement' });
  const { createMessage } = useMessage();

  const [registerDrawer, { openDrawer }] = useDrawer();
  const [registerTable, { reload, setLoading }] = useTable({
    title: '角色列表',
    api: getRoleListByPage,
    columns: columns(onChangeStatus as any),
    formConfig: {
      labelWidth: 120,
      schemas: searchFormSchema,
    },
    useSearchForm: false,
    showTableSetting: true,
    bordered: false,
    size: 'small',
    showIndexColumn: false,
    actionColumn: {
      width: 80,
      title: '操作',
      dataIndex: 'action',
      // slots: { customRender: 'action' },
      fixed: undefined,
    },
  });

  function onChangeStatus(params: any) {
    console.log('params===', params);
    curParams = { ...params, status: !params.status };
    visibleGoogle.value = true;
  }
  function handleCreate() {
    openDrawer(true, {
      isUpdate: false,
    });
  }

  function handleEdit(record: Recordable) {
    openDrawer(true, {
      record,
      isUpdate: true,
      action: 'update',
    });
  }

  function handleDelete(record: Recordable) {
    console.log(record);
    curParams = { action: 'delete', id: record.id };
    visibleGoogle.value = true;
    // postRoleListByPageFn({ action: 'delete', id: record.id });
  }
  async function postRoleListByPageFn(params: any) {
    setLoading(true);
    useApiBasic({
      apiFn: postRoleListByPage(params),
      successFn() {
        reload();
        visibleGoogle.value = false;
      },
      finallyFn() {
        setLoading(false);
        if (refGoogle.value) refGoogle.value.loading = false;
      },
    });
  }
  function handleSuccess() {
    reload();
  }
</script>
