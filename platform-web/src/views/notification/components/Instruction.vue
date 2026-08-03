<template>
  <div>
    <BasicList
      ref="listRef"
      :beforeFetch="beforeFetch"
      :pagination="pagination"
      :dataSource="dataSource"
      :loading="loading"
    >
      <template #renderItem="{ item }">
        <div class="border-bottom">
          <div class="h-16 pr-4 pl-22px flex items-center relative">
            <Badge v-if="!item?.isRead" class="absolute left-2" status="error" />
            <div class="flex-1 truncate mr-12">
              <div v-if="!item?.isExpand" class="truncate text-base"> {{ item?.content }}</div>
            </div>
            <div class="mr-4 color-third text-xs">{{ formatToDateTime(item?.createTime) }}</div>
            <div @click="toggleExpand(item)" class="cursor-pointer w-13 text-center">
              <div v-if="item?.isExpand" class="text-[#C1272D]">收起</div>
              <div v-else class="text-[#1677FF]">展开</div>
            </div>
          </div>
          <div v-if="item?.isExpand" class="text-base pb-5 px-4">{{ item?.content }}</div>
        </div>
      </template>
    </BasicList>
  </div>
</template>
<script lang="tsx" setup>
  import { onMounted, ref, nextTick, watch } from 'vue';
  import { BasicList } from '@/components/list';
  import { getNtification, postNtification } from '@/api/notifications';
  import { Badge } from 'ant-design-vue';
  import { formatToDateTime } from '@/utils/dateUtil';

  const props = defineProps({
    tabKey: {
      type: String,
      default: '',
    },
    defaultExpandKey: {
      type: String,
      default: '',
    },
  });
  const emits = defineEmits(['unreadCountChange']);
  const listRef = ref();
  const dataSource = ref([]);
  const defaultExpandKeyCur = ref('');
  const loading = ref(false);
  const unreadCount = ref(0);
  const pagination = ref({
    current: 1,
    pageSize: 10,
    total: 0,
    onChange: (page, pageSize) => {
      getNtificationFn({ pageIndex: page, pageSize });
    },
  });
  async function getNtificationFn(params?: any) {
    loading.value = true;
    try {
      const res = await getNtification(params);
      if (res.retCode == 0) {
        dataSource.value = res.data?.list?.map((item) => {
          item.isExpand = false;
          return item;
        });
        unreadCount.value = res.data?.unreadCount;
        initExpand();
        pagination.value.total = res.data?.total;
        pagination.value.current = res.data?.pageIndex;
        pagination.value.pageSize = res.data?.pageSize;
      }
    } finally {
      loading.value = false;
    }
  }
  function initData() {
    getNtificationFn();
  }
  onMounted(() => {
    initData();
  });
  function toggleExpand(params: any) {
    if (!params.isRead) {
      expandItem({ id: params.id });
      readyMsg(params);
    } else {
      expandItem(params);
    }
  }
  function readyMsg(params: any) {
    console.log('readyMsg----', params);
    const _params = {
      id: params.id,
      action: 'read',
    };
    postNtificationFn(_params);
  }
  async function postNtificationFn(params: any) {
    const res = await postNtification(params);
    if (res.retCode == 0) {
      if (params.action == 'read') {
        readyMsgCb(params);
      } else if (params.action == 'readAll') {
        readAllCb();
      }
    }
    console.log('postNtification----', res);
  }
  function readyMsgCb(params: any) {
    console.log('readyMsgCb----', params);

    const _index = dataSource.value?.findIndex((item: any) => item.id == params.id);
    nextTick(() => {
      if (_index == -1) return;
      // expandItem({ id: dataSource.value[_index].id });
      // dataSource.value[_index].isExpand = true;
      // dataSource.value[_index].isRead = true;
      unreadCount.value && unreadCount.value--;
      console.log('readyMsgCb----444', dataSource.value);
    });
  }
  function readAll() {
    postNtificationFn({ action: 'readAll' });
    getNtificationFn();
  }
  // 全部已读回调functio
  function readAllCb() {
    unreadCount.value = 0;
    dataSource.value.forEach((item: any) => {
      item.isRead = true;
    });
  }
  // 初始化展开数据或者展开数据发生变化（路径参数变化）
  function initExpand() {
    if (props.defaultExpandKey && props.defaultExpandKey != defaultExpandKeyCur.value) {
      defaultExpandKeyCur.value = props.defaultExpandKey;
      const _item = dataSource.value?.find((item: any) => item.id == props.defaultExpandKey);
      if (_item && !_item.isRead) {
        readyMsg({ id: props.defaultExpandKey });
      }
      expandItem({ id: props.defaultExpandKey });
    }
  }
  watch(
    unreadCount,
    (newVal) => {
      emits('unreadCountChange', newVal);
    },
    { immediate: true },
  );
  function beforeFetch(params: any) {
    console.log('beforeFetch', params);
  }
  function expandItem(params) {
    // console.log('expandItem', params);
    dataSource.value = dataSource.value?.map((item: any) => {
      if (item.id == params.id) {
        item.isExpand = !item.isExpand;
        item.isRead = true;
      }
      return item;
    });
  }
  defineExpose({
    readAll,
    readyMsg,
    initData,
    unreadCount,
  });
</script>
