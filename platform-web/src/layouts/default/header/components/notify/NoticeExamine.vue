<template>
  <Spin :spinning="loading">
    <div class="mt-[-8px]">
      <Empty v-if="!dataSource.length" :image="Empty.PRESENTED_IMAGE_SIMPLE" class="!pt-0" />
      <div v-else class="list">
        <div
          v-for="item in dataSource"
          :key="item.id"
          @click="jump({ tabKey: tabKey, id: item.id })"
          class="list-item"
        >
          <div class="w-1/2 truncate">{{ item?.content }}</div>
          <div class="color-third text-xs">{{ diffTime(item?.createTime) }}</div>
        </div>
      </div>
      <div class="list-footer">
        <!-- <div @click="postNtificationFn({ action: 'readAll' })" class="list-footer-item"
          >全部已读</div
        > -->
        <div @click="jump()" class="list-footer-item">查看全部<RightOutlined class="ml-1" /></div>
      </div>
    </div>
  </Spin>
</template>
<script lang="tsx" setup>
  import { onMounted, ref } from 'vue';
  import { RightOutlined } from '@ant-design/icons-vue';
  import { getNtification } from '@/api/notifications';
  import { useGo } from '@/hooks/web/usePage';
  import { diffTime } from '@/utils/dateUtil';
  import { Empty, Spin } from 'ant-design-vue';

  const props = defineProps({
    tabKey: {
      type: [String, Number],
      default: '',
    },
    dataSource: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  });
  const emit = defineEmits(['close']);
  const go = useGo();
  function jump(params?: any) {
    emit('close');
    go({
      path: '/log/alarm',
      query: params,
    });
  }
</script>
<style lang="less" scoped>
  .list {
    max-height: 280px;
    overflow: auto;

    &-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid @border-color-base;
      color: @text-color-secondary;
      line-height: 54px;
      cursor: pointer;

      &:last-child {
        border-bottom: none;
      }

      &:hover {
        color: inherit;
      }
    }
  }

  .list-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin-top: 16px;
    color: @text-color-third;

    &-item {
      cursor: pointer;

      &:hover {
        color: var(--text-color);
      }
    }
  }
</style>
