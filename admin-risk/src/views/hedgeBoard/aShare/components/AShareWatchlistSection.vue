<template>
  <section id="a-share-watchlist" class="research-card">
    <header class="research-card__header">
      <div>
        <p class="research-card__eyebrow">WATCHLIST</p>
        <h2>自选股</h2>
      </div>
      <button type="button" class="toolbar-button" @click="addExpanded = !addExpanded">
        {{ addExpanded ? '收起添加' : '添加自选' }}
      </button>
    </header>

    <form v-if="addExpanded" class="add-form" @submit.prevent="submitAdd">
      <label><span>股票代码</span><input v-model.trim="form.code" maxlength="6" placeholder="例如 600519" /></label>
      <label><span>股票名称</span><input v-model.trim="form.name" placeholder="例如 贵州茅台" /></label>
      <label><span>分组</span><input v-model.trim="form.group" placeholder="例如 核心观察" /></label>
      <button type="submit" class="primary-button">保存</button>
    </form>

    <div v-if="groups.length" class="watchlist-groups">
      <article v-for="group in groups" :key="group.name" class="watchlist-group">
        <header><h3>{{ group.name }}</h3><span>{{ group.items.length }}项</span></header>
        <div class="watchlist-table">
          <div v-for="item in group.items" :key="item.code" class="watchlist-row">
            <button type="button" class="stock-button" @click="$emit('query', item.code)">
              <strong>{{ item.name }}</strong><span>{{ item.code }}</span>
            </button>
            <input
              :value="item.group"
              class="group-input"
              aria-label="自选股分组"
              @change="$emit('setGroup', item.code, ($event.target as HTMLInputElement).value)"
            />
            <div class="row-actions">
              <button type="button" @click="$emit('move', item.code, 'up')">上移</button>
              <button type="button" @click="$emit('move', item.code, 'down')">下移</button>
              <button type="button" class="is-danger" @click="$emit('remove', item.code)">删除</button>
            </div>
          </div>
        </div>
      </article>
    </div>
    <div v-else class="research-empty">暂无自选股</div>
  </section>
</template>

<script setup lang="ts">
  import { reactive, ref } from 'vue';
  import type { WatchlistItem } from '../useAShareResearch';

  defineProps<{ groups: Array<{ name: string; items: WatchlistItem[] }> }>();
  const emit = defineEmits<{
    (event: 'add', code: string, name: string, group: string): void;
    (event: 'remove', code: string): void;
    (event: 'move', code: string, direction: 'up' | 'down'): void;
    (event: 'setGroup', code: string, group: string): void;
    (event: 'query', code: string): void;
  }>();

  const addExpanded = ref(false);
  const form = reactive({ code: '', name: '', group: '默认分组' });

  function submitAdd() {
    if (!/^\d{6}$/.test(form.code)) return;
    emit('add', form.code, form.name || form.code, form.group || '默认分组');
    form.code = '';
    form.name = '';
  }
</script>

<style scoped lang="less">
  .research-card { padding: 18px; border: 1px solid var(--strategy-border); border-radius: var(--strategy-radius-card); background: var(--strategy-surface); box-shadow: var(--strategy-shadow-soft); }
  .research-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 15px; }
  .research-card__eyebrow { margin: 0 0 3px; color: var(--strategy-text-4); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
  h2, h3 { margin: 0; color: var(--strategy-text-1); }
  h2 { font-size: 18px; }
  h3 { font-size: 14px; }
  button { cursor: pointer; }
  .toolbar-button, .primary-button, .row-actions button { min-height: 34px; padding: 0 11px; border: 1px solid var(--strategy-border); border-radius: 8px; background: var(--strategy-surface-2); color: var(--strategy-text-2); }
  .primary-button { background: var(--strategy-accent-soft); color: var(--strategy-accent-strong); font-weight: 700; }
  .add-form { display: grid; grid-template-columns: 160px minmax(180px, 1fr) minmax(160px, 1fr) auto; align-items: end; gap: 10px; margin-bottom: 14px; padding: 12px; border: 1px solid var(--strategy-border); border-radius: 11px; background: var(--strategy-surface-2); }
  .add-form label { display: grid; gap: 5px; color: var(--strategy-text-3); font-size: 12px; }
  input { min-width: 0; height: 36px; padding: 0 10px; border: 1px solid var(--strategy-border); border-radius: 8px; background: var(--strategy-surface); color: var(--strategy-text-1); }
  .watchlist-groups { display: grid; gap: 12px; }
  .watchlist-group { overflow: hidden; border: 1px solid var(--strategy-border); border-radius: 11px; }
  .watchlist-group > header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: var(--strategy-surface-2); }
  .watchlist-group > header span { color: var(--strategy-text-4); font-size: 12px; }
  .watchlist-row { display: grid; grid-template-columns: minmax(150px, 1fr) minmax(120px, .7fr) auto; align-items: center; gap: 10px; padding: 10px 12px; border-top: 1px solid var(--strategy-border); }
  .stock-button { border: 0; background: transparent; color: var(--strategy-text-1); text-align: left; }
  .stock-button strong, .stock-button span { display: block; }
  .stock-button span { margin-top: 2px; color: var(--strategy-text-4); font-size: 12px; }
  .group-input { height: 32px; }
  .row-actions { display: flex; gap: 5px; }
  .row-actions button { min-height: 30px; padding: 0 8px; font-size: 12px; }
  .row-actions .is-danger { color: #dc2626; }
  .research-empty { padding: 28px; color: var(--strategy-text-3); text-align: center; }
  @media (max-width: 900px) { .add-form { grid-template-columns: 1fr 1fr; } .watchlist-row { grid-template-columns: 1fr; } .row-actions { justify-content: flex-start; } }
  @media (max-width: 560px) { .research-card__header { flex-direction: column; } .add-form { grid-template-columns: 1fr; } }
</style>
