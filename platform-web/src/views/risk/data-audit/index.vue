<template>
  <PageWrapper title="数据审计">
    <main class="audit-page">
      <section class="audit-heading">
        <div
          ><h2>全平台数据健康</h2
          ><p>采集 → 存储 → 更新 → 消费。后台每 5 分钟检查，页面只读取审计结果。</p></div
        >
        <Button :loading="loading" @click="refresh">刷新结果</Button>
      </section>
      <Alert v-if="error" type="error" show-icon :message="error" />
      <Alert
        type="info"
        show-icon
        message="来源：本平台数据库、研究文件与 Runtime 状态接口。正常数量仅代表已列出的检查项，不代表全库每条数据均已验证。"
      />
      <Alert
        v-if="report?.monitorStale"
        type="error"
        show-icon
        message="审计后台未按时报告：当前结果不能代表最新状态"
      />
      <div class="audit-summary">
        <button
          v-for="item in states"
          :key="item.key"
          :class="['audit-stat', item.key, { selected: filter === item.key }]"
          @click="filter = filter === item.key ? '' : item.key"
        >
          <span>{{ item.label }}</span
          ><strong>{{ report?.summary[item.key] ?? '—' }}</strong>
        </button>
      </div>
      <section class="audit-panel">
        <div class="audit-toolbar"
          ><div
            ><h3>检查项与证据</h3><small>最近审计 {{ displayTime(report?.checkedAt) }}</small></div
          >
          <Input
            v-model:value="search"
            placeholder="搜索数据集、模块或问题"
            allow-clear
            style="max-width: 300px"
          />
        </div>
        <Table
          :columns="columns"
          :data-source="rows"
          row-key="key"
          :pagination="{ pageSize: 15, showSizeChanger: true }"
          :scroll="{ x: 760 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'evidence'"
              ><Button
                size="small"
                @click="selected = report?.checks.find((item) => item.key === record.key)"
                >查看证据</Button
              ></template
            >
            <template v-if="column.key === 'freshness'">
              <div
                >数据：{{
                  evidenceDate(
                    record.evidence.sourceDate ?? record.evidence.end ?? record.evidence.observedAt,
                  )
                }}</div
              >
              <small
                >更新：{{
                  evidenceDate(record.evidence.lastSuccessAt ?? record.evidence.fetched)
                }}</small
              >
              <small class="audit-key" v-if="record.evidence.deadlineHours != null"
                >更新时限 {{ record.evidence.deadlineHours }} 小时</small
              >
            </template>
            <template v-if="column.key === 'status'"
              ><Tag :color="tones[record.status]">{{ labels[record.status] }}</Tag></template
            >
            <template v-else-if="column.key === 'name'"
              ><b>{{ record.name }}</b
              ><small class="audit-key">{{ record.key }}</small></template
            >
          </template>
        </Table>
      </section>
      <section class="audit-panel">
        <h3>异常与恢复记录</h3
        ><p>同一问题合并提醒；检查恢复后自动关闭。未验证的覆盖边界不会标成正常。</p>
        <Table
          :columns="alertColumns"
          :data-source="report?.alerts ?? []"
          row-key="id"
          :pagination="{ pageSize: 8 }"
          :scroll="{ x: 700 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'"
              ><Tag :color="record.status === 'closed' ? 'green' : 'red'">{{
                record.status === 'closed'
                  ? '已恢复'
                  : record.status === 'acknowledged'
                  ? '已确认 · 未恢复'
                  : '待处理'
              }}</Tag></template
            >
            <template v-else-if="column.key === 'last_seen_at'">{{
              displayTime(record.last_seen_at)
            }}</template>
          </template>
        </Table>
      </section>
    </main>
    <Modal :visible="!!selected" title="检查证据" :footer="null" @cancel="selected = undefined">
      <div v-if="selected" class="audit-evidence"
        ><b>{{ selected.name }}</b
        ><p>本项检查时间 {{ displayTime(selected.checkedAt) }}</p
        ><p>{{ selected.message }}</p
        ><p v-if="selected.evidence.rows != null">历史记录 {{ selected.evidence.rows }} 条</p
        ><pre>{{ JSON.stringify(selected.evidence, null, 2) }}</pre>
      </div>
    </Modal>
  </PageWrapper>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import { Alert, Button, Input, Modal, Table, Tag } from 'ant-design-vue';
  import { PageWrapper } from '@/components/Page';
  import { useKeepAliveActive } from '@/hooks/web/useKeepAliveActive';
  import { getDataAudit, type DataAuditReport, type DataCheck } from '@/api/platform/dataAudit';

  const report = ref<DataAuditReport>();
  const loading = ref(false);
  const error = ref('');
  const filter = ref('');
  const search = ref('');
  const active = useKeepAliveActive();
  const selected = ref<DataCheck>();
  const labels = {
    healthy: '检查通过',
    error: '异常',
    warning: '需关注 / 未验证',
    info: '停用 / 归档',
  };
  const tones = { healthy: 'green', error: 'red', warning: 'orange', info: 'default' };
  const states = Object.entries(labels).map(([key, label]) => ({ key, label }));
  const rows = computed(() =>
    (report.value?.checks ?? [])
      .filter(
        (item) =>
          (!filter.value || item.status === filter.value) &&
          `${item.name} ${item.key} ${item.group} ${item.message}`
            .toLowerCase()
            .includes(search.value.toLowerCase()),
      )
      .sort(
        (a, b) =>
          ['error', 'warning', 'healthy', 'info'].indexOf(a.status) -
          ['error', 'warning', 'healthy', 'info'].indexOf(b.status),
      ),
  );
  const columns = [
    { title: '证据', key: 'evidence', width: 110 },
    { title: '状态', key: 'status', width: 150 },
    { title: '模块', dataIndex: 'group', width: 130 },
    { title: '检查项', key: 'name', width: 270 },
    { title: '数据时间与更新依据', key: 'freshness', width: 260 },
    { title: '结果', dataIndex: 'message' },
  ];
  const alertColumns = [
    { title: '状态', key: 'status', width: 150 },
    { title: '问题', dataIndex: 'message' },
    { title: '最近发现', key: 'last_seen_at', width: 190 },
    { title: '发现次数', dataIndex: 'occurrence_count', width: 100 },
  ];
  const displayTime = (value?: string | null) =>
    value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '尚未完成';
  const evidenceDate = (value: unknown) => {
    if (value == null || value === '') return '此项无时间证据';
    const raw = String(value);
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    const date = new Date(typeof value === 'number' ? value : raw);
    return Number.isNaN(date.getTime()) ? raw : date.toLocaleString('zh-CN', { hour12: false });
  };
  async function refresh() {
    if (loading.value) return;
    loading.value = true;
    try {
      report.value = await getDataAudit();
      error.value = '';
    } catch {
      error.value = '无法读取审计结果，请检查平台 API；不能据此判断数据正常。';
    } finally {
      loading.value = false;
    }
  }
  let timer: ReturnType<typeof setInterval> | undefined;
  watch(active, (value) => {
    clearInterval(timer);
    if (value) {
      void refresh();
      timer = setInterval(() => {
        if (!document.hidden) void refresh();
      }, 60000);
    }
  });
  onBeforeUnmount(() => clearInterval(timer));
</script>
<style scoped>
  .audit-page {
    padding: 4px 16px 28px;
    color: #183444;
  }

  .audit-heading,
  .audit-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 18px;
  }

  h2 {
    margin: 0 0 8px;
    font-size: 22px;
    font-weight: 650;
  }

  h3 {
    margin: 0 0 8px;
    font-size: 16px;
    font-weight: 600;
  }

  p,
  small {
    color: #687d8c;
  }

  .audit-summary {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 20px 0;
  }

  .audit-stat {
    padding: 20px;
    border: 1px solid #dce5eb;
    border-radius: 14px;
    background: white;
    text-align: left;
    cursor: pointer;
  }

  .audit-stat strong {
    display: block;
    margin-top: 10px;
    font-size: 30px;
    font-variant-numeric: tabular-nums;
  }

  .audit-stat.selected {
    outline: 2px solid #497cba;
  }

  .audit-stat.error strong {
    color: #c93940;
  }

  .audit-stat.warning strong {
    color: #a16c17;
  }

  .audit-stat.healthy strong {
    color: #23816c;
  }

  .audit-panel {
    margin-bottom: 18px;
    padding: 20px;
    border: 1px solid #dce5eb;
    border-radius: 16px;
    background: white;
  }

  .audit-key {
    display: block;
    font-size: 11px;
    font-weight: normal;
    overflow-wrap: anywhere;
  }

  .audit-evidence pre {
    max-height: 280px;
    margin: 12px 0;
    overflow: auto;
    font-size: 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  @media (max-width: 760px) {
    .audit-summary {
      grid-template-columns: repeat(2, 1fr);
    }

    .audit-heading,
    .audit-toolbar {
      flex-direction: column;
      align-items: flex-start;
    }

    .audit-page {
      padding: 8px;
    }
  }
</style>
