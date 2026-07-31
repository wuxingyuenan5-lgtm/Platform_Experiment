<template>
  <SimpleContainer>
    <template #title>
      <div class="flex gap-2">
        <div class="text-base font-500">定时任务</div>
        <Tooltip :overlayInnerStyle="{ width: '300px' }">
          <template #title>
            <div>
              minute="*/5", hour="*"<br />
              # 执行时间: 00:00, 00:05, 00:10, ..., 23:55 <br />s minute="30", hour="9,17" <br />
              # 执行时间: 09:30, 17:30 <br />
              minute="*/15", hour="9-18" <br />
              # 执行时间: 09:00, 09:15, 09:30, ..., 17:45<br />
              minute="0", hour="2,4" <br />
              # 执行时间: 02:00, 04:00<br />
              minute="0", hour="*/1"<br />
              # 执行时间:00:00, 01:00, 02:00, ..., 23:00
            </div>
          </template>
          <Icon class="cursor-pointer text-#FAAD14" icon="ant-design:exclamation-circle-outlined" />
        </Tooltip>
      </div>
    </template>
    <!-- <div class="flex justify-end pb-2">
      <Button type="primary" @click="handleEdit(null)">新增</Button>
    </div> -->
    <BasicTable @register="registerTable" body-padding="">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div class="flex items-center gap-4">
            <div
              @click="handleToggle(record)"
              v-if="!record?.isActivate"
              class="cursor-pointer text-#2FB97B"
              >启用</div
            >
            <div @click="handleToggle(record)" v-else class="cursor-pointer text-#FF4D4F">禁用</div>

            <div @click="handleEdit(record)" class="text-#2C97EB cursor-pointer">编辑</div>
            <!-- <Popconfirm @confirm="handleDelete(record)">
              <template #title>
                <p>是否确认删除?</p>
              </template>
              <div class="text-#ff4d4f cursor-pointer">删除</div>
            </Popconfirm> -->
          </div>
        </template>
      </template>
    </BasicTable>
    <!-- 编辑 -->
    <EditModal ref="editModal" @success="editSuccess" :record="curCreate" />
    <!-- 谷歌验证 -->
    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { ref } from 'vue';
  import { Button, Popconfirm, Tooltip } from 'ant-design-vue';
  import { BasicTable, useTable } from '@/components/Table';
  import { getBasicColumns } from './data';
  import { getSchedulerList, postSchedulerList } from '@/api/risk/scheduler';
  import EditModal from './components/Edit.vue';
  import { SimpleContainer } from '@/components/Container';
  import Icon from '@/components/Icon/Icon.vue';
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { useApiBasic } from '@/hooks/web/useApi';
  // 谷歌验证
  const visibleGoogle = ref(false);
  const refGoogle = ref();
  let curParams = {};
  const handleClickConfirm = (params) => {
    const _params = { ...curParams, ...params };
    console.log(_params);
    useApiBasic({
      apiFn: postSchedulerList(_params),
      successFn() {
        reload();
        visibleGoogle.value = false;
      },
      finallyFn() {
        if (refGoogle.value) refGoogle.value.loading = false;
      },
    });
  };
  const curCreate = ref<any>();
  const editModal = ref();
  const [registerTable, { reload }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getSchedulerList,
    columns: getBasicColumns(),
    showIndexColumn: false,
    actionColumn: {
      width: 200,
      title: '操作',
      dataIndex: 'action',
    },
    pagination: false,
  });
  function editSuccess(params: any) {
    reload();
    editModal.value.openModal(false);
  }
  function handleEdit(record: Recordable | null) {
    curCreate.value = record;
    editModal.value.openModal(true);
  }
  function handleDelete(record: Recordable) {
    console.log(record);
    curParams = { action: 'delete', jobId: record.jobId };
    visibleGoogle.value = true;
  }
  function handleToggle(record: Recordable) {
    curParams = { action: 'toggle', jobId: record.jobId };
    visibleGoogle.value = true;
  }
</script>
