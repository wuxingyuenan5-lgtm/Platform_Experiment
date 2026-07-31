<template>
  <SimpleContainer title="调拨配置">
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
  import { ref, reactive } from 'vue';
  import { BasicTable, useTable } from '@/components/Table';
  import { SimpleContainer } from '@/components/Container';
  import { getColumns } from './data';
  import { Select, RangePicker, Button } from 'ant-design-vue';
  import { getThresholds } from '@/api/risk/transfer';
  import EditModal from './components/Edit.vue';

  const curCreate = ref<any>();
  const editModal = ref();
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getThresholds,
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
