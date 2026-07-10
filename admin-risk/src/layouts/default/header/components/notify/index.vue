<template>
  <div :class="prefixCls">
    <Popover :destroyTooltipOnHide="true" title="" placement="bottomRight">
      <div class="w-full h-full flex items-center">
        <Badge :count="count" dot :numberStyle="numberStyle">
          <BellOutlined class="text-20px" />
        </Badge>
      </div>
      <template #content>
        <Tabs size="small" v-model:activeKey="active">
          <template v-for="item in listData" :key="item.key">
            <Tabs.TabPane>
              <template #tab>
                {{ item.name }}
                <span v-if="item.list.length !== 0">({{ item.list.length }})</span>
              </template>
              <!-- 绑定title-click事件的通知列表中标题是“可点击”的-->
              <div class="w-120">
                <NoticeExamine :dataSource="item.list" :loading="loading" :tabKey="active" />
              </div>
            </Tabs.TabPane>
          </template>
        </Tabs>
      </template>
    </Popover>
  </div>
</template>
<script lang="tsx" setup>
  import { computed, ref, onMounted } from 'vue';
  import { Popover, Tabs, Badge, message } from 'ant-design-vue';
  import { BellOutlined, ExclamationCircleFilled } from '@ant-design/icons-vue';
  import { tabListData, ListItem } from './data';
  import { useDesign } from '@/hooks/web/useDesign';
  import { useMessage } from '@/hooks/web/useMessage';
  import NoticeExamine from './NoticeExamine.vue';
  import { getNtification } from '@/api/notifications';
  import { useGo } from '@/hooks/web/usePage';

  const { prefixCls } = useDesign('header-notify');
  const { createMessage } = useMessage();
  const listData = ref(tabListData);
  const active = ref('alert');
  const numberStyle = {};
  const go = useGo();

  const count = computed(() => {
    let count = 0;
    for (let i = 0; i < listData.value.length; i++) {
      count += listData.value[i].list.length;
    }
    return count;
  });

  // function onNoticeClick(record: ListItem) {
  //   createMessage.success('你点击了通知，ID=' + record.id);
  //   // 可以直接将其标记为已读（为标题添加删除线）,此处演示的代码会切换删除线状态
  //   record.titleDelete = !record.titleDelete;
  // }
  const loading = ref(false);
  async function getNtificationFn() {
    loading.value = true;
    try {
      const res = await getNtification({ isRead: false, pageSize: 99 });
      listData.value[0].list = res?.data?.list || [];
    } finally {
      loading.value = false;
    }
  }
  // function dealNtification() {
  //   go({
  //     path: '/dashboard',
  //     query: {
  //       scrollBottom: true,
  //     },
  //   });
  //   message.destroy();
  // }
  onMounted(() => {
    getNtificationFn();
  });
</script>
