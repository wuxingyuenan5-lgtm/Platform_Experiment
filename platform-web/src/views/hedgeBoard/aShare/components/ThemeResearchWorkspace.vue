<template>
  <section class="object-workspace" aria-label="主题综合研究">
    <KeepAlive>
      <EquityThemePanel
        v-if="data.themes"
        market="cn"
        view="themes"
        :data="data.themes"
        :industries="data.structure?.industries || []"
        :selected-theme="theme"
        :member-industry="memberIndustry"
        @theme="emit('theme', $event)"
        @clear-member-industry="emit('clear-member-industry')"
      >
        <template #theme-insights="{ theme: current }">
          <EquityObservatoryPanel
            market="cn"
            view="crowding"
            crowding-scope="theme"
            :selected-theme="theme"
            embedded
            :refresh-key="refreshKey"
          />
          <section class="object-card theme-industries">
            <div class="object-heading"
              ><h3>相关行业 · 估值与参与度</h3
              ><p>主题成员按申万一级分类关联；指标为对应行业整体，非主题估值。</p></div
            >
            <div class="object-table" tabindex="0" role="region" aria-label="主题相关行业">
              <table
                ><thead
                  ><tr
                    ><th>行业</th><th>主题内成员</th><th>行业PE中位数</th><th>行业PB中位数</th
                    ><th>行业上涨占比</th></tr
                  ></thead
                >
                <tbody
                  ><tr v-for="row in related(current)" :key="row.code"
                    ><th
                      ><button @click="emit('industry', row.code)">{{ row.name }} →</button></th
                    ><td>{{ row.themeMemberCount }}只</td><td>{{ fmt(row.medianPe) }}</td
                    ><td>{{ fmt(row.medianPb) }}</td
                    ><td>{{ fmt(row.advancingPct) }}%</td></tr
                  >
                  <tr v-if="!related(current).length"
                    ><td colspan="5">当前主题暂无已确认的一级行业关联</td></tr
                  ></tbody
                >
              </table>
            </div>
            <p class="object-source"
              >行业指标 {{ data.structure?.date || '—' }} · 主题成员
              {{ data.themes?.date || '—' }}；点击行业查看对应景气、量能和关联主题。</p
            >
          </section>
        </template>
      </EquityThemePanel>
    </KeepAlive>
  </section>
</template>
<script setup lang="ts">
  import { defineAsyncComponent } from 'vue';
  import type { EquityObservatory, EquityTheme, EquityValue } from '@/api/equityObservatory';
  import { themeIndustries } from './industryResearch';
  import EquityThemePanel from '../../components/EquityThemePanel.vue';

  const EquityObservatoryPanel = defineAsyncComponent(
    () => import('../../components/EquityObservatoryPanel.vue'),
  );
  const props = defineProps<{
    data: EquityObservatory;
    theme: string;
    memberIndustry?: { code: string; name: string };
    refreshKey: number;
  }>();
  const emit = defineEmits<{
    theme: [name: string];
    industry: [code: string];
    'clear-member-industry': [];
  }>();
  const related = (theme: EquityTheme) =>
    themeIndustries(theme, props.data.structure?.industries || []);
  const fmt = (v: EquityValue | undefined) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? '—' : Number(v).toFixed(2);
</script>
<style scoped src="./objectResearch.css"></style>
<style scoped>
  .theme-industries {
    margin-bottom: 18px;
  }

  .theme-industries h3 {
    font-size: 15px;
  }
</style>
