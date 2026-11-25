<template>
  <nav class="research-sidebar" :aria-label="`${label}专题`">
    <button
      type="button"
      class="sidebar-toggle"
      :aria-expanded="!collapsed"
      @click="emit('toggle')"
      >{{ collapsed ? '展开' : `${label} ‹` }}</button
    >
    <RouterLink
      v-for="item in items"
      :key="item.key"
      :to="
        item.path || {
          path: route.path,
          query: {
            ...route.query,
            ...(route.path === '/hedge-board/a-share' && active !== item.key
              ? {
                  theme: undefined,
                  themeIndustry: undefined,
                  segment: undefined,
                  themeDate: undefined,
                  stock: undefined,
                }
              : {}),
            view: item.key,
          },
        }
      "
      :class="{ active: active === item.key }"
      :title="item.label"
      :aria-label="item.label"
      :aria-current="active === item.key ? 'page' : undefined"
    >
      <span>{{ collapsed ? item.short || item.label.slice(0, 2) : item.label }}</span
      ><span aria-hidden="true">›</span>
    </RouterLink>
  </nav>
</template>
<script setup lang="ts">
  import { useRoute, RouterLink } from 'vue-router';

  withDefaults(
    defineProps<{
      items: Array<{ key: string; label: string; short?: string; path?: string }>;
      active: string;
      collapsed: boolean;
      label?: string;
    }>(),
    { label: 'A股研究' },
  );
  const emit = defineEmits<{ toggle: [] }>();
  const route = useRoute();
</script>
<style scoped>
  .research-sidebar {
    display: grid;
    position: sticky;
    top: 76px;
    align-self: start;
    padding: 12px 8px;
    border: 1px solid #e1e7ef;
    border-radius: 12px;
    background: white;
    gap: 5px;
    font-family: var(
      --strategy-font-sans,
      'Aptos',
      'PingFang SC',
      'Hiragino Sans GB',
      'Microsoft YaHei UI',
      'Segoe UI',
      sans-serif
    );
    font-weight: 400;
    line-height: 1.5;
  }

  .sidebar-toggle {
    padding: 8px 12px 12px;
    border: 0;
    background: transparent;
    color: #8793a4;
    font-family: inherit;
    font-size: 11px;
    font-weight: 400;
    letter-spacing: 1px;
    line-height: inherit;
    text-align: left;
    cursor: pointer;
  }

  a {
    display: flex;
    justify-content: space-between;
    padding: 11px 12px;
    border-radius: 7px;
    color: #526277;
    font-size: 13px;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  a:hover {
    background: #f5f7fb;
    color: #1d4ed8;
  }

  a.active {
    background: #eaf1ff;
    color: #245dc7;
    font-weight: 600;
  }

  a:focus-visible {
    outline: 2px solid #245dc7;
    outline-offset: 2px;
  }

  @media (max-width: 900px) {
    .research-sidebar {
      display: flex;
      position: static;
      padding: 6px;
      overflow-x: auto;
    }

    .sidebar-toggle {
      display: none;
      border: 0;
      background: transparent;
      text-align: left;
      cursor: pointer;
    }

    a {
      flex: 0 0 auto;
      padding: 9px 12px;
      gap: 10px;
      white-space: nowrap;
      overflow-wrap: normal;
    }

    a > span:last-child {
      display: none;
    }
  }
</style>
