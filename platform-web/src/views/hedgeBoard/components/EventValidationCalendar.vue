<template>
  <section class="event-calendar">
    <header
      ><div><h2>事件日历 · 验证节点</h2><p>记录关注事件、事前判定条件与事后结果</p></div
      ><button @click="edit()">添加事件</button></header
    >
    <p v-if="error" role="alert">{{ error }} <button @click="load">重新载入</button></p>
    <form v-if="draft" @submit.prevent="commit">
      <label>事件<input v-model.trim="draft.title" required maxlength="160" /></label>
      <label>日期<input v-model="draft.date" type="date" required /></label>
      <label
        >时间精度<select v-model="draft.precision"
          ><option value="day">确定日期</option
          ><option value="around">前后</option
          ><option value="month">月份</option></select
        ></label
      >
      <label
        >来源链接<input v-model.trim="draft.sourceUrl" type="url" placeholder="https://"
      /></label>
      <label class="wide"
        >观察与判定条件<textarea
          v-model.trim="draft.criterion"
          rows="3"
          maxlength="1800"
        ></textarea>
      </label>
      <label
        >状态<select v-model="draft.status"
          ><option value="watching">关注中</option
          ><option value="confirmed">已验证</option
          ><option value="cancelled">已取消</option></select
        ></label
      >
      <label class="wide"
        >实际结果<textarea v-model.trim="draft.outcome" rows="2" maxlength="1800"></textarea>
      </label>
      <div class="wide"
        ><button :disabled="saving">保存事件</button
        ><button type="button" @click="draft = null">取消</button></div
      >
    </form>
    <div class="filters"
      ><input v-model="search" aria-label="搜索事件" placeholder="搜索事件或条件" /><label
        ><input v-model="showPast" type="checkbox" />显示过去事件</label
      ></div
    >
    <div class="table-scroll"
      ><table
        ><thead
          ><tr><th>时间</th><th>事件</th><th>观察与判定</th><th>结果</th><th>操作</th></tr></thead
        ><tbody>
          <tr v-for="event in visible" :key="event.id"
            ><td
              >{{ event.precision === 'month' ? event.date.slice(0, 7) : event.date
              }}{{ event.precision === 'around' ? ' 前后' : ''
              }}<small>{{ countdown(event) }}</small></td
            ><td
              ><a
                v-if="event.sourceUrl"
                :href="event.sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                >{{ event.title }} ↗</a
              ><template v-else>{{ event.title }}</template></td
            ><td>{{ event.criterion || '—' }}</td
            ><td
              ><span>{{
                { watching: '关注中', confirmed: '已验证', cancelled: '已取消' }[event.status]
              }}</span
              ><p>{{ event.outcome }}</p></td
            ><td
              ><button @click="edit(event)">编辑</button
              ><button @click="remove(event.id)" :disabled="saving">移除</button></td
            ></tr
          >
          <tr v-if="!visible.length"
            ><td colspan="5">{{
              loading ? '正在加载…' : '暂无事件，可添加关注的验证节点。'
            }}</td></tr
          >
        </tbody></table
      ></div
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
  import { useUserStore } from '@/store/modules/user';
  import { loadWorkspace, saveWorkspace, type CalendarEvent } from '@/api/workspace';

  const events = ref<CalendarEvent[]>([]),
    draft = ref<CalendarEvent | null>(null),
    search = ref(''),
    showPast = ref(false),
    saving = ref(false),
    loading = ref(true),
    error = ref('');
  const user = useUserStore();
  let version = 0,
    generation = 0;
  const today = ref(new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' }));
  const clock = setInterval(() => {
    today.value = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' });
  }, 60000);
  onBeforeUnmount(() => {
    clearInterval(clock);
    generation++;
  });
  const visible = computed(() =>
    events.value
      .filter(
        (e) =>
          (showPast.value ||
            (e.precision === 'month'
              ? e.date.slice(0, 7) >= today.value.slice(0, 7)
              : e.date >= today.value)) &&
          (e.title + e.criterion).toLowerCase().includes(search.value.toLowerCase()),
      )
      .sort((a, b) => a.date.localeCompare(b.date)),
  );
  function countdown(e: CalendarEvent) {
    if (e.precision === 'month') return '月份待定';
    const days = Math.round((Date.parse(e.date) - Date.parse(today.value)) / 86400000);
    return days === 0 ? '今天' : days > 0 ? `${days}天后` : `${-days}天前`;
  }
  async function load() {
    const active = ++generation;
    loading.value = true;
    error.value = '';
    try {
      const r = await loadWorkspace<CalendarEvent>('events');
      if (active !== generation) return;
      events.value = r.items;
      version = r.rowVersion;
    } catch (e) {
      if (active === generation) error.value = String(e);
    } finally {
      if (active === generation) loading.value = false;
    }
  }
  function edit(e?: CalendarEvent) {
    draft.value = e
      ? { ...e }
      : {
          id: crypto.randomUUID(),
          date: today.value,
          precision: 'day',
          title: '',
          criterion: '',
          outcome: '',
          sourceUrl: '',
          status: 'watching',
        };
  }
  async function persist(next: CalendarEvent[]) {
    if (loading.value) return false;
    const active = generation;
    saving.value = true;
    error.value = '';
    try {
      const r = await saveWorkspace('events', next, version);
      if (active !== generation) return false;
      events.value = r.items;
      version = r.rowVersion;
      return true;
    } catch (e) {
      if (active === generation) error.value = String(e);
      return false;
    } finally {
      if (active === generation) saving.value = false;
    }
  }
  async function commit() {
    if (!draft.value) return;
    const next = events.value.filter((e) => e.id !== draft.value!.id);
    next.push({ ...draft.value });
    if (await persist(next)) draft.value = null;
  }
  async function remove(id: string) {
    await persist(events.value.filter((e) => e.id !== id));
  }
  onMounted(load);
  watch(
    () => user.getUserInfo.userId,
    () => {
      events.value = [];
      draft.value = null;
      saving.value = false;
      void load();
    },
  );
</script>
<style scoped>
  .event-calendar {
    margin-bottom: 18px;
    padding: 20px;
    border: 1px solid #dbe4ed;
    border-radius: 12px;
    background: #fff;
    color: #20364b;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h2 {
    margin: 0;
    font-size: 18px;
  }

  header p,
  small {
    color: #708397;
    font-size: 12px;
  }

  small {
    display: block;
    margin-top: 6px;
  }

  button,
  input,
  select,
  textarea {
    padding: 7px 10px;
    border: 1px solid #d7e2ed;
    border-radius: 6px;
    background: #fff;
    color: inherit;
    font: inherit;
  }

  button {
    margin-right: 5px;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.5;
  }

  form {
    display: grid;
    grid-template-columns: 1fr 1fr;
    margin: 14px 0;
    padding: 16px;
    border-radius: 8px;
    background: #f5f8fc;
    gap: 12px;
  }

  label {
    display: grid;
    gap: 5px;
  }

  .wide {
    grid-column: 1/-1;
  }

  .filters {
    display: flex;
    gap: 16px;
    align-items: center;
    margin: 14px 0;
  }

  .filters label {
    display: flex;
    align-items: center;
  }

  .table-scroll {
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  th {
    background: #f3f7fb;
    text-align: left;
  }

  th,
  td {
    padding: 12px;
    border-bottom: 1px solid #e6edf4;
    vertical-align: top;
  }

  td {
    min-width: 110px;
    white-space: pre-wrap;
  }

  td:nth-child(3) {
    min-width: 230px;
  }

  a {
    color: #2864ec;
  }

  input,
  textarea {
    min-width: 0;
  }

  @media (max-width: 600px) {
    form {
      grid-template-columns: 1fr;
    }

    .filters {
      flex-wrap: wrap;
    }
  }
</style>
