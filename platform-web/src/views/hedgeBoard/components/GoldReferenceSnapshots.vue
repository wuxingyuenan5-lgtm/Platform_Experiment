<template>
  <details class="reference-snapshots" :open="group === 'options'">
    <summary>原图快照 · {{ group === 'options' ? '未落地' : '待补功能' }}</summary>
    <div class="reference-grid">
      <figure v-for="item in items" :key="item.file">
        <figcaption
          ><strong>{{ item.title }}</strong
          ><span>未落地</span></figcaption
        >
        <p>{{ item.missing }}</p>
        <a
          :href="`/images/gold-references/${item.file}.png`"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="`查看${item.title}原图`"
        >
          <img
            :src="`/images/gold-references/${item.file}.png`"
            :alt="`${item.title}，用户提供的参考截图，未落地`"
            loading="lazy"
          />
        </a>
        <small>参考快照 · 非当前行情 · 点击查看完整原图</small>
      </figure>
    </div>
  </details>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  const props = defineProps<{ group: 'options' | 'factors' | 'cot' }>();
  const catalog = {
    options: [
      {
        file: 'put-call-ema30',
        title: '金银 Put / Call 成交量比',
        missing: '待接通日度期权成交历史与 EMA30。',
      },
      {
        file: 'call-volume-ema30',
        title: '金银 Call 成交量',
        missing: '待接通全部合约月成交量及金银价格对照。',
      },
      {
        file: 'put-volume-ema30',
        title: '金银 Put 成交量',
        missing: '待接通全部合约月成交量及金银价格对照。',
      },
      {
        file: 'max-pain-current',
        title: '近月内在价值与最大痛点',
        missing: '待取得完整期权链、对应期货结算价及多日对比。',
      },
      {
        file: 'max-pain-history',
        title: '最大痛点历史与下一到期月',
        missing: '待补历史期权链、溢折价、ΔIV 及到期月衔接。',
      },
    ],
    factors: [
      {
        file: 'factor-model',
        title: '原报告四因子模型',
        missing: '当前为独立分解；原报告的中周期基准、参数及趋势线尚未复现。',
      },
      {
        file: 'factor-cycles',
        title: '分周期因子贡献',
        missing: '分层走势已实现；原图周期边界、周期重置与标注尚未落地。',
      },
    ],
    cot: [
      {
        file: 'cot-weekly',
        title: 'COT 周度变化与价格对照',
        missing: '持仓变化已实现；原图同期价格端点对照尚未落地。',
      },
      {
        file: 'cot-shares',
        title: '资产管理多空比例参考',
        missing: '比例曲线已实现；原图阈值及历史区间标注尚未落地。',
      },
      {
        file: 'cot-period',
        title: 'COT 区间变化与价格对照',
        missing: '自选报告区间已实现；原图同期价格端点对照尚未落地。',
      },
    ],
  };
  const items = computed(() => catalog[props.group]);
</script>
<style scoped>
  .reference-snapshots {
    margin-top: 20px;
    padding-top: 14px;
    border-top: 1px solid #e0e6eb;
  }

  summary {
    color: #536679;
    font-weight: 600;
    cursor: pointer;
  }

  .reference-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
    gap: 16px;
    margin-top: 14px;
  }

  figure {
    margin: 0;
    padding: 12px;
    border: 1px solid #e0e6eb;
    border-radius: 8px;
    background: #fff;
  }

  figcaption {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    gap: 8px;
  }

  figcaption span {
    flex-shrink: 0;
    padding: 2px 6px;
    border-radius: 4px;
    background: #fff3d8;
    color: #9c711d;
    font-size: 11px;
  }

  p {
    min-height: 40px;
    margin: 8px 0;
    color: #6c7c89;
    font-size: 12px;
    line-height: 1.7;
  }

  img {
    display: block;
    width: 100%;
    height: 240px;
    object-fit: contain;
    object-position: top;
    background: #f3f6f9;
  }

  small {
    display: block;
    margin-top: 8px;
    color: #788793;
    font-size: 11px;
  }

  a:focus-visible {
    outline: 2px solid #426da4;
    outline-offset: 3px;
  }
</style>
