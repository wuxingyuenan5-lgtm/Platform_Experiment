<template>
  <SimpleContainer title="风险等级配置">
    <BasicTable @register="registerTable" body-padding="">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div class="flex items-center gap-4">
            <div @click="handleEdit(record)" class="text-#2C97EB cursor-pointer">编辑</div>
          </div>
        </template>
      </template>
    </BasicTable>
    <!-- 编辑 -->
    <EditModal ref="editModal" @success="editSuccess" :record="curCreate" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { ref } from 'vue';
  import { BasicTable, useTable } from '@/components/Table';
  import { SimpleContainer } from '@/components/Container';
  import { getColumns } from './data';
  import { getGlobalConfig } from '@/api/risk/settings';
  import EditModal from './components/Edit.vue';

  const curCreate = ref<any>();
  const editModal = ref();
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getGlobalConfig,
    columns: getColumns(),
    showIndexColumn: false,
    actionColumn: {
      width: 200,
      title: '操作',
      dataIndex: 'action',
      // slots: { customRender: 'action' },
    },
  });
  function editSuccess(params: any) {
    reload();
    editModal.value.openModal(false);
  }
  function handleEdit(record: Recordable | null) {
    curCreate.value = record;
    editModal.value.openModal(true);
  }
</script>
