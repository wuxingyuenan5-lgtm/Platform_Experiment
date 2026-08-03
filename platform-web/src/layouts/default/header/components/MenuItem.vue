<template>
  <div v-if="routes?.[0]" class="flex break-keep">
    <div class="mr-12 layout-nav-location">{{ t(routes?.[0].name as string) }}</div>
    <div class="flex pt-4 pb-4" v-if="routes?.[0].children?.length">
      <div
        :class="[item.path == routes?.[1]?.path && 'is-active', 'layout-nav-item']"
        v-for="item in routes?.[0].children"
        :key="item.path"
        @click="handleClick(item)"
        >{{ t(item.name as string) }}</div
      >
    </div>
  </div>
</template>
<script lang="ts" setup>
  import type { RouteLocationMatched } from 'vue-router';
  import type { Menu } from '@/router/types';
  import { ref, watchEffect } from 'vue';
  import { useI18n } from '@/hooks/web/useI18n';
  import { useGo } from '@/hooks/web/usePage';
  import { useRouter } from 'vue-router';
  import { getMenus } from '@/router/menus';
  import { REDIRECT_NAME } from '@/router/constant';
  import { getAllParentPath } from '@/router/helper/menuHelper';
  import { filter } from '@/utils/helper/treeHelper';

  const go = useGo();

  const { t } = useI18n();
  const routes = ref<RouteLocationMatched[]>([]);
  const { currentRoute } = useRouter();

  watchEffect(async () => {
    if (currentRoute.value.name === REDIRECT_NAME) return;
    routes.value = [];
    const menus = await getMenus();
    const routeMatched = currentRoute.value.matched;
    const cur = routeMatched?.[routeMatched.length - 1];
    let path = currentRoute.value.path;

    if (cur && cur?.meta?.currentActiveMenu) {
      path = cur.meta.currentActiveMenu as string;
    }

    const parent = getAllParentPath(menus, path);
    const filterMenus = menus.filter((item) => item.path === parent[0]);
    const matched = getMatched(filterMenus, parent) as any;
    if (!matched || matched.length === 0) return;

    const breadcrumbList = filterItem(matched);

    if (currentRoute.value.meta?.currentActiveMenu) {
      breadcrumbList.push({
        ...currentRoute.value,
        name: currentRoute.value.meta?.title || currentRoute.value.name,
      } as unknown as RouteLocationMatched);
    }

    routes.value = breadcrumbList;
  });
  function getMatched(menus: Menu[], parent: string[]) {
    const metched: Menu[] = [];
    menus.forEach((item) => {
      if (parent.includes(item.path)) {
        metched.push({
          ...item,
          name: item.meta?.title || item.name,
        });
      }
      if (item.children?.length) {
        metched.push(...getMatched(item.children, parent));
      }
    });
    return metched;
  }
  function filterItem(list: RouteLocationMatched[]) {
    return filter(list, (item) => {
      const { meta, name } = item;
      if (!meta) {
        return !!name;
      }
      const { title, hideBreadcrumb, hideMenu } = meta;
      if (!title || hideBreadcrumb || hideMenu) {
        return false;
      }
      return true;
    }).filter((item) => !item.meta?.hideBreadcrumb);
  }
  function handleClick(params: any) {
    // console.log(params);
    go(params.path);
  }
</script>
<style lang="less">
  .layout-nav-location {
    color: @primary-color;
  }

  .layout-nav-item {
    padding: 0 16px;
    border-radius: 4px;
    color: #d1d4dc;
    line-height: 32px;
    cursor: pointer;

    &:hover {
      background-color: rgb(255 255 255 / 10%);
      color: #fff;
    }

    &.is-active {
      background-color: @primary-color;
      color: #000;
    }
  }
</style>
