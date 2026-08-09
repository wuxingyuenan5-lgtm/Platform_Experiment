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
  import { computed, ref } from 'vue';
  import { Popover, Tabs, Badge } from 'ant-design-vue';
  import { BellOutlined } from '@ant-design/icons-vue';
  import { tabListData } from './data';
  import { useDesign } from '@/hooks/web/useDesign';
  import NoticeExamine from './NoticeExamine.vue';

  const { prefixCls } = useDesign('header-notify');
  const listData = ref(tabListData);
  const active = ref('alert');
  const numberStyle = {};

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
</script>
