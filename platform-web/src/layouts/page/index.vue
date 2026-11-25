<template>
  <RouterView>
    <template #default="{ Component, route }">
      <keep-alive v-if="openCache" :include="getCaches">
        <component :is="Component" :key="getPageKey(route)" class="min-h-190" />
      </keep-alive>
      <component v-else :is="Component" :key="getPageKey(route)" class="min-h-190" />
    </template>
  </RouterView>
  <FrameLayout v-if="getCanEmbedIFramePage" />
</template>

<script lang="ts" setup>
  import { computed, unref } from 'vue';

  import FrameLayout from '@/layouts/iframe/index.vue';

  import { useRootSetting } from '@/hooks/setting/useRootSetting';

  import { useMultipleTabSetting } from '@/hooks/setting/useMultipleTabSetting';
  import { getPageKey } from './transition';

  import { useMultipleTabStore } from '@/store/modules/multipleTab';

  defineOptions({ name: 'PageLayout' });

  const { getShowMultipleTab } = useMultipleTabSetting();
  const tabStore = useMultipleTabStore();

  const { getOpenKeepAlive, getCanEmbedIFramePage } = useRootSetting();

  const openCache = computed(() => unref(getOpenKeepAlive) && unref(getShowMultipleTab));

  const getCaches = computed((): string[] => {
    if (!unref(getOpenKeepAlive)) {
      return [];
    }
    return tabStore.getCachedTabList;
  });
</script>
