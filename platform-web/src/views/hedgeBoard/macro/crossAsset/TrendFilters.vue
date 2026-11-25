<template>
  <details class="screening-card trend-builder">
    <summary
      >周期条件与排序
      <span>{{
        active.length
          ? active.map((f) => FRAME_NAMES[f] + '：' + conditionSummary(filters.rules[f])).join('；')
          : '不限周期'
      }}</span></summary
    >
    <div class="screening-controls">
      <label
        >周期关系<select
          :value="filters.match"
          @change="setFilters({ match: value($event) as 'all' | 'any' })"
          ><option value="all">全部满足</option
          ><option value="any">任一满足</option></select
        ></label
      >
      <label
        ><input
          type="checkbox"
          :checked="filters.stillCurrent"
          @change="setFilters({ stillCurrent: checked($event) })"
        />本轮转向仍有效</label
      >
      <button @click="emit('reset')">清除趋势条件</button>
    </div>
    <div class="screening-table"
      ><table
        ><thead
          ><tr
            ><th>周期</th><th>当前方向</th><th>转向事件</th><th>此前方向</th><th>回看根数</th
            ><th>操作</th></tr
          ></thead
        ><tbody>
          <tr v-for="f in FRAMES" :key="f"
            ><th>{{ FRAME_NAMES[f] }}</th>
            <td
              ><select
                :aria-label="FRAME_NAMES[f] + '当前方向'"
                :value="filters.rules[f].state"
                @change="rule(f, { state: value($event) as FrameCondition['state'] })"
                ><option value="any">不限</option
                ><option v-for="d in directions" :key="d" :value="d">{{
                  directionLabel(d)
                }}</option></select
              ></td
            >
            <td
              ><select
                :aria-label="FRAME_NAMES[f] + '转向事件'"
                :value="filters.rules[f].turn"
                @change="rule(f, { turn: value($event) as FrameCondition['turn'] })"
                ><option value="any">不限</option
                ><option value="changed">任意转向</option
                ><option value="多">转多</option
                ><option value="空">转空</option
                ><option value="震荡">转中性</option></select
              ></td
            >
            <td
              ><select
                :aria-label="FRAME_NAMES[f] + '此前方向'"
                :disabled="filters.rules[f].turn === 'any'"
                :value="filters.rules[f].from"
                @change="rule(f, { from: value($event) as FrameCondition['from'] })"
                ><option value="any">不限</option
                ><option value="多">偏多</option
                ><option value="空">偏空</option
                ><option value="震荡">中性</option></select
              ></td
            >
            <td
              ><input
                type="number"
                min="0"
                max="1000"
                :aria-label="FRAME_NAMES[f] + '回看根数'"
                :value="filters.rules[f].lookback"
                :disabled="filters.rules[f].turn === 'any'"
                @change="
                  rule(f, {
                    lookback: Math.max(0, Math.min(1000, Math.trunc(Number(value($event))))),
                  })
                "
              /><small>0为全部历史</small></td
            >
            <td
              ><button
                :aria-label="'清除' + FRAME_NAMES[f] + '条件'"
                :disabled="!activeCondition(filters.rules[f])"
                @click="rule(f, defaultCondition())"
                >清除</button
              ></td
            >
          </tr>
        </tbody></table
      ></div
    >
    <p v-if="conflicts.length" role="status" class="screening-warning"
      >{{ conflicts.map((f) => FRAME_NAMES[f]).join('、') }}的方向条件冲突，该周期无法匹配。</p
    >
    <div class="screening-controls">
      <label
        >排序<select :value="sort.by" @change="setSort({ by: value($event) as TrendSort['by'] })"
          ><option value="event">最近转向</option
          ><option value="priority">周期分歧优先</option
          ><option value="symbol">标的代码</option></select
        ></label
      >
      <label
        >排序周期<select
          :value="sort.frame"
          @change="setSort({ frame: value($event) as TrendSort['frame'] })"
          ><option value="matched">命中周期</option
          ><option v-for="f in FRAMES" :key="f" :value="f">{{ FRAME_NAMES[f] }}</option></select
        ></label
      >
      <label
        >顺序<select
          :value="sort.order"
          @change="setSort({ order: value($event) as TrendSort['order'] })"
          ><option value="desc">降序</option
          ><option value="asc">升序</option></select
        ></label
      >
      <label>方案名称<input v-model="presetName" maxlength="40" placeholder="保存当前条件" /></label
      ><button
        :disabled="!presetName.trim()"
        @click="
          emit('save', presetName.trim());
          presetName = '';
        "
        >保存为新方案</button
      >
    </div>
  </details>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { FRAMES, FRAME_NAMES, type Direction, type Frame } from './engine';
  import { directionLabel } from './rules';
  import {
    activeCondition,
    defaultCondition,
    conditionSummary,
    impossibleCondition,
    type FrameCondition,
    type TrendFilters,
    type TrendSort,
  } from './filters';

  const props = defineProps<{ filters: TrendFilters; sort: TrendSort }>();
  const emit = defineEmits<{
    change: [filters: TrendFilters, sort: TrendSort];
    reset: [];
    save: [name: string];
  }>();
  const presetName = ref('');
  const directions: Direction[] = ['多', '空', '震荡', '不足'];
  const value = (event: Event) => (event.target as HTMLInputElement).value;
  const checked = (event: Event) => (event.target as HTMLInputElement).checked;
  const active = computed(() => FRAMES.filter((f) => activeCondition(props.filters.rules[f])));
  const conflicts = computed(() =>
    active.value.filter((f) =>
      impossibleCondition(props.filters.rules[f], props.filters.stillCurrent),
    ),
  );
  const setFilters = (patch: Partial<TrendFilters>) =>
    emit('change', { ...props.filters, ...patch }, props.sort);
  const setSort = (patch: Partial<TrendSort>) =>
    emit('change', props.filters, { ...props.sort, ...patch });
  const rule = (frame: Frame, patch: Partial<FrameCondition>) =>
    setFilters({
      rules: { ...props.filters.rules, [frame]: { ...props.filters.rules[frame], ...patch } },
    });
</script>
