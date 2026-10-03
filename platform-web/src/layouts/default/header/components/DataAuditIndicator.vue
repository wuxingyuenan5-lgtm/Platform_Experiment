<template>
  <Tooltip v-if="allowed" :title="title">
    <RouterLink class="data-audit-indicator" to="/risk/data-audit" :aria-label="title">
      <Badge :count="count" :overflow-count="99"><DatabaseOutlined /></Badge>
    </RouterLink>
  </Tooltip>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import { RouterLink } from 'vue-router';
  import { Badge, Tooltip } from 'ant-design-vue';
  import { DatabaseOutlined } from '@ant-design/icons-vue';
  import { usePermissionStore } from '@/store/modules/permission';
  import { getDataAudit } from '@/api/platform/dataAudit';

  const permissions = usePermissionStore();
  const allowed = computed(() =>
    permissions.getPermCodeList.some((value) => value === 'risk.read'),
  );
  const count = ref(0);
  const title = ref('数据审计：等待检查结果');
  let timer: ReturnType<typeof setInterval> | undefined;
  let pending = false;
  async function refresh() {
    if (!allowed.value || pending || document.hidden) return;
    pending = true;
    try {
      const report = await getDataAudit();
      count.value =
        (report.summary.error ?? 0) + (report.summary.warning ?? 0) + Number(report.monitorStale);
      title.value = report.monitorStale
        ? '数据审计：后台未按时报告'
        : `数据审计：${count.value} 项异常或未验证`;
    } catch {
      count.value = 1;
      title.value = '数据审计不可读取，请检查平台服务';
    } finally {
      pending = false;
    }
  }
  watch(
    allowed,
    (value) => {
      clearInterval(timer);
      if (value) {
        void refresh();
        timer = setInterval(refresh, 60000);
      }
    },
    { immediate: true },
  );
  onBeforeUnmount(() => clearInterval(timer));
</script>
<style scoped>
  .data-audit-indicator {
    display: inline-flex;
    align-items: center;
    min-height: 40px;
    padding: 0 16px;
    color: #32506a;
    font-size: 18px;
  }
</style>
