<template>
  <RouterView>
    <template #default="{ Component, route }">
      <transition
        :css="getEnableTransition && !route.path.startsWith('/hedge-board/')"
        :name="
          getTransitionName({
            route,
            openCache,
            enableTransition: getEnableTransition,
            cacheTabs: getCaches,
            def: getBasicTransition,
          })
        "
        :mode="
          getEnableTransition && !route.path.startsWith('/hedge-board/') ? 'out-in' : undefined
        "
        appear
      >
        <keep-alive v-if="openCache" :include="getCaches">
          <component :is="Component" :key="getPageKey(route)" class="min-h-190" />
        </keep-alive>
        <component v-else :is="Component" :key="getPageKey(route)" class="min-h-190" />
      </transition>
    </template>
  </RouterView>
  <FrameLayout v-if="getCanEmbedIFramePage" />
</template>

<script lang="ts" setup>
  import { computed, unref } from 'vue';

  import FrameLayout from '@/layouts/iframe/index.vue';

  import { useRootSetting } from '@/hooks/setting/useRootSetting';

  import { useTransitionSetting } from '@/hooks/setting/useTransitionSetting';
  import { useMultipleTabSetting } from '@/hooks/setting/useMultipleTabSetting';
  import { getPageKey, getTransitionName } from './transition';

  import { useMultipleTabStore } from '@/store/modules/multipleTab';

  defineOptions({ name: 'PageLayout' });

  const { getShowMultipleTab } = useMultipleTabSetting();
  const tabStore = useMultipleTabStore();

  const { getOpenKeepAlive, getCanEmbedIFramePage } = useRootSetting();

  const { getBasicTransition, getEnableTransition } = useTransitionSetting();

  const openCache = computed(() => unref(getOpenKeepAlive) && unref(getShowMultipleTab));

  const getCaches = computed((): string[] => {
    if (!unref(getOpenKeepAlive)) {
      return [];
    }
    return tabStore.getCachedTabList;
  });
</script>
