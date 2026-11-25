import type { FinanceLine, FinanceRow } from './FinancingChart.vue';
import { DEMO_CATALOG, FOREIGN_COMPARISON_IDS, type DemoSpec } from './capitalHandbookDemoCatalog';

export interface DemoColumn {
  key: string;
  label: string;
  unit?: string;
  heat?: boolean;
}
export interface DemoData {
  kind: 'time' | 'bars' | 'table' | 'matrix';
  rows: FinanceRow[];
  lines: FinanceLine[];
  columns: DemoColumn[];
}
export const demoPeriods = [
  '2023-12-31',
  '2024-03-31',
  '2024-06-30',
  '2024-09-30',
  '2024-12-31',
  '2025-03-31',
  '2025-06-30',
  '2025-09-30',
  '2025-12-31',
  '2026-03-31',
  '2026-06-30',
  '2026-09-30',
];
const industries = [
  '电子',
  '通信',
  '计算机',
  '机械设备',
  '电力设备',
  '医药生物',
  '食品饮料',
  '银行',
  '非银金融',
  '公用事业',
  '汽车',
  '有色金属',
  '其他行业',
];
const palette = ['#2563eb', '#0d9488', '#ca8a04', '#8b5cf6', '#e76e55', '#64748b', '#0891b2'];
const round = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;
const sum = (a: number[]) => a.reduce((s, n) => s + n, 0);
const col = (key: string, label: string, unit?: string, heat = false): DemoColumn => ({
  key,
  label,
  unit,
  heat,
});
const line = (
  key: string,
  name: string,
  unit: string,
  i: number,
  bar = false,
  right = false,
  stack?: string,
): FinanceLine => ({ key, name, unit, color: palette[i % palette.length], bar, right, stack });
function hash(s: string) {
  return [...s].reduce((v, c) => (v * 31 + c.charCodeAt(0)) >>> 0, 17);
}
function random(seed: number) {
  let value = seed >>> 0;
  return () => {
    value = (Math.imul(value, 1664525) + 1013904223) >>> 0;
    return value / 4294967296;
  };
}
function weights(raw: number[]): number[] {
  const total = sum(raw);
  const values = raw.map((v) => Math.floor((v / total) * 10000));
  const left = 10000 - sum(values);
  for (let i = 0; i < left; i++) values[i % values.length]++;
  return values.map((v) => v / 100);
}
function months(end: string, count: number) {
  const anchor = new Date(`${end}T00:00:00Z`);
  return Array.from({ length: count }, (_, i) =>
    new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth() - count + i + 2, 0))
      .toISOString()
      .slice(0, 10),
  );
}
function table(rows: FinanceRow[], columns: DemoColumn[], matrix = false): DemoData {
  return { kind: matrix ? 'matrix' : 'table', rows, columns, lines: [] };
}
function chart(rows: FinanceRow[], lines: FinanceLine[], bars = false): DemoData {
  return { kind: bars ? 'bars' : 'time', rows, lines, columns: [] };
}

/** Entirely synthetic fixtures. Never consumes capital API data or calls a provider. */
export function buildCapitalDemo(id: string, period = demoPeriods.at(-1)!): DemoData {
  const spec = DEMO_CATALOG.find((s) => s.id === id);
  if (!spec || !demoPeriods.includes(period)) throw new Error('Unknown handbook demo or period');
  const rand = random(hash(`${id}/${period}`));
  const dates = months(period, 36);
  if (spec.recipe === 'series')
    return series(
      spec,
      id === 'foreign-quarter-flow' ? dates.filter((_, i) => i % 3 === 2) : dates,
    );
  if (spec.recipe === 'flows') {
    const names = ['公募', 'ETF', '险资', '外资', '私募', 'IPO及再融资', '股东减持'];
    const rows = dates
      .filter((_, i) => i % 3 === 2)
      .map((date, i) => {
        const values = names.map((_, j) =>
          j >= 5
            ? -Math.round(450 + rand() * 750)
            : Math.round(200 + Math.sin(i * 0.8 + j) * 450 + rand() * 700),
        );
        return {
          date,
          ...Object.fromEntries(values.map((v, j) => [`v${j}`, v])),
          net: sum(values),
        };
      });
    return chart(rows, [
      ...names.map((name, i) => line(`v${i}`, name, '亿元', i, true, false, 'flows')),
      line('net', '合计净额', '亿元', 0),
    ]);
  }
  if (spec.recipe === 'bridge') {
    let opening = 18000;
    const rows = dates
      .filter((_, i) => i % 3 === 2)
      .map((date) => {
        const newCapital = Math.round(300 + rand() * 900);
        const subscriptions = Math.round((rand() - 0.55) * 1800);
        const valuation = Math.round((rand() - 0.4) * 2200);
        const closing = opening + newCapital + subscriptions + valuation;
        const row = {
          date,
          opening,
          newCapital,
          subscriptions,
          valuation,
          change: newCapital + subscriptions + valuation,
          closing,
        };
        opening = closing;
        return row;
      });
    return table(rows, [
      col('date', '报告期'),
      col('opening', '期初规模', '亿元'),
      col('newCapital', id === 'pension-stock-change' ? '新增持仓' : '新发/新增资金', '亿元'),
      col(
        'subscriptions',
        id === 'fund-nav-bridge' ? '存量净申赎' : '存量持仓净增减',
        '亿元',
        true,
      ),
      col('valuation', '估值变动', '亿元', true),
      col('change', '规模变化', '亿元', true),
      col('closing', '期末规模', '亿元'),
    ]);
  }
  if (spec.recipe === 'companyMatrix') {
    const insurance = id === 'insurance-listed',
      bank = id === 'bank-full-allocation';
    const labels = insurance
      ? ['股票', '证券投资基金', '债券', '其他资产']
      : bank
      ? ['债券', '现金与存款', '非标债权', '权益资产', '基金', '其他资产']
      : industries;
    const names = bank
      ? demoPeriods.slice(0, demoPeriods.indexOf(period) + 1).slice(-6)
      : Array.from(
          { length: 8 },
          (_, i) => `示例${insurance ? '险企' : '基金公司'}${String.fromCharCode(65 + i)}`,
        );
    const columns = names.map((name, i) => col(`c${i}`, name, '%', true));
    const values = names.map(() =>
      weights(labels.map((_, j) => (labels.length - j) * (1 + rand() * 2))),
    );
    return table(
      labels.map((date, j) => ({
        date,
        ...Object.fromEntries(values.map((v, i) => [`c${i}`, v[j]])),
      })),
      [col('date', '行业 / 资产'), ...columns],
      true,
    );
  }
  if (spec.recipe === 'rankHistory') {
    const foreign = id === 'foreign-sector-rank';
    const names = foreign
      ? industries.slice(0, 10)
      : Array.from({ length: 32 }, (_, i) => `示例证券${String(i + 1).padStart(2, '0')}`);
    const periods = demoPeriods.slice(0, demoPeriods.indexOf(period) + 1).slice(-8);
    const ranks = periods.map((_, j) => {
      const shuffled = names
        .map((name, i) => ({ name, i, score: i * 0.35 + rand() * 5 + Math.sin(i + j) * 2 }))
        .sort((a, b) => a.score - b.score);
      return Object.fromEntries(
        shuffled.slice(0, foreign ? 10 : 25).map((x, i) => [x.name, i + 1]),
      );
    });
    return table(
      names.map((date) => ({
        date,
        ...Object.fromEntries(ranks.map((r, i) => [`p${i}`, r[date] ?? null])),
      })),
      [
        col('date', foreign ? '行业' : '示例证券'),
        ...periods.map((p, i) => col(`p${i}`, p, '名', true)),
      ],
      true,
    );
  }
  if (spec.recipe === 'allocation' || spec.recipe === 'attribution') {
    const prev = weights(industries.map((_, i) => 2 + (13 - i) * (1 + rand())));
    const returns = industries.map(() => round((rand() - 0.4) * 38));
    const natural = weights(prev.map((v, i) => v * (1 + returns[i] / 100)));
    const current = weights(natural.map((v) => v * (0.75 + rand() * 0.5)));
    const benchmark = weights(industries.map(() => 4 + rand() * 10));
    const shareWeighted = weights(current.map((v) => v * (0.7 + rand() * 0.6)));
    const rows = industries.map((date, i) => ({
      date,
      previous: prev[i],
      current: current[i],
      change: round(current[i] - prev[i]),
      returnPct: returns[i],
      natural: natural[i],
      residual: round(current[i] - natural[i]),
      benchmark: benchmark[i],
      relative: round(current[i] - benchmark[i]),
      percentile: Math.round(rand() * 100),
      shareWeighted: shareWeighted[i],
      weightingGap: round(shareWeighted[i] - current[i]),
    }));
    return table(
      rows,
      id === 'fund-share-weighted'
        ? [
            col('date', '行业'),
            col('current', '资产加权配置', '%'),
            col('shareWeighted', '份额加权配置', '%'),
            col('weightingGap', '加权方式差异', '百分点', true),
          ]
        : spec.recipe === 'attribution'
        ? [
            col('date', '行业'),
            col('previous', '上期权重', '%'),
            col('returnPct', '期间涨跌', '%', true),
            col('natural', '价格变化后自然权重', '%'),
            col('current', '本期权重', '%'),
            col('residual', '配置残差', '百分点', true),
          ]
        : [
            col('date', '行业'),
            col('current', '本期配置', '%'),
            col('previous', '上期配置', '%'),
            col('change', '环比', '百分点', true),
            col('benchmark', '基准权重', '%'),
            col('relative', '超低配', '百分点', true),
            col('percentile', '样本历史分位', '%', true),
            ...(id === 'etf-sector-weights' ? [col('returnPct', '期间涨跌', '%', true)] : []),
          ],
    );
  }
  if (spec.recipe === 'holdings') {
    const labels = Array.from(
      { length: 20 },
      (_, i) => `示例${id.includes('hk') ? '港股' : '证券'}${String(i + 1).padStart(2, '0')}`,
    );
    const all = weights([...labels.map((_, i) => 30 - i + rand() * 7), 500]);
    const old = weights([...labels.map((_, i) => 30 - i + rand() * 10), 510]);
    return table(
      labels
        .map((date, i) => ({
          date,
          industry: industries[i % 12],
          rank: i + 1,
          amount: round(all[i] * 85),
          weight: all[i],
          previous: old[i],
          change: round(all[i] - old[i]),
          holders: Math.round(350 - i * 9 + rand() * 40),
          returns: round((rand() - 0.4) * 50),
        }))
        .sort((a, b) => b.amount - a.amount)
        .map((r, i) => ({ ...r, rank: i + 1 })),
      [
        col('rank', '排名'),
        col('date', '示例证券'),
        col('industry', '行业'),
        col('amount', '持股金额', '亿元'),
        col('weight', '本期权重', '%'),
        col('previous', '上期权重', '%'),
        col('change', '变化', '百分点', true),
        col('holders', '持有基金数', '只'),
        col('returns', '期间涨跌', '%', true),
      ],
    );
  }
  if (spec.recipe === 'subscription') {
    const rows = Array.from({ length: 25 }, (_, i) => {
      const opening = round(5 + rand() * 70),
        closing = round(opening * (1.05 + rand() * 0.7));
      return {
        date: `示例基金${String(i + 1).padStart(2, '0')}`,
        industry: industries[i % 12],
        opening,
        closing,
        change: round((closing / opening - 1) * 100),
        returns: round((rand() - 0.3) * 35),
        topStock: `示例证券${String((i % 12) + 1).padStart(2, '0')}`,
      };
    }).sort((a, b) => b.change - a.change);
    return table(rows, [
      col('date', '示例基金'),
      col('opening', '期初份额', '亿份'),
      col('closing', '期末份额', '亿份'),
      col('change', '份额变动', '%', true),
      col('returns', '净值收益', '%', true),
      col('industry', '主要行业'),
      col('topStock', '第一重仓'),
    ]);
  }
  if (spec.recipe === 'histogram') {
    const returns = id === 'fund-return-subscriptions';
    const labels = returns
      ? ['＜−20%', '−20%～−10%', '−10%～0%', '0%～10%', '10%～20%', '20%～30%', '≥30%']
      : id === 'bank-return-distribution'
      ? ['＜−2%', '−2%～−1%', '−1%～0%', '0%～1%', '1%～2%', '≥2%']
      : id.startsWith('bank')
      ? ['＜0.97', '0.97～0.99', '0.99～1.00', '1.00～1.02', '1.02～1.05', '≥1.05']
      : ['＜0.6', '0.6～0.8', '0.8～1.0', '1.0～1.2', '1.2～1.5', '1.5～2.0', '≥2.0'];
    const counts = labels.map((_, i) =>
      Math.round(15 + 600 * Math.exp(-((i - 3) ** 2) / 2) * (0.8 + rand() * 0.4)),
    );
    const pct = weights(counts);
    return chart(
      labels.map((date, i) => ({
        date,
        count: counts[i],
        pct: pct[i],
        change: round(18 - i * 8 + rand() * 10),
      })),
      returns
        ? [
            line('change', '平均份额变动', '%', 0, true),
            line('count', '基金数量', '只', 1, false, true),
          ]
        : [line('count', '产品数量', '只', 0, true), line('pct', '数量占比', '%', 1, false, true)],
      true,
    );
  }
  if (spec.recipe === 'holderMix') {
    const labels =
      id === 'etf-holder-history'
        ? demoPeriods.slice(0, demoPeriods.indexOf(period) + 1).slice(-8)
        : ['沪深300', '中证A500', '中证1000', '科创50', '红利', '科技主题', '消费主题'];
    const names = ['银行', '保险', '公募基金', '其他机构', '个人'];
    return table(
      labels.map((date) => ({
        date,
        ...Object.fromEntries(
          weights(names.map(() => 3 + rand() * 15)).map((v, i) => [`v${i}`, v]),
        ),
      })),
      [
        col('date', id === 'etf-holder-history' ? '报告期' : 'ETF分类'),
        ...names.map((n, i) => col(`v${i}`, n, '%', true)),
      ],
      true,
    );
  }
  if (spec.recipe === 'industry') {
    const rate = id === 'margin-broker-rate';
    const labels = rate
      ? Array.from({ length: 12 }, (_, i) => `示例券商${String.fromCharCode(65 + i)}`)
      : id === 'etf-broad-size' || id === 'insurance-etf'
      ? ['沪深300', '中证A500', '中证500', '中证1000', '科创50', '创业板', '红利', '其他']
      : industries;
    const current = labels.map(() => round(rate ? 2.8 + rand() * 1.7 : 400 + rand() * 2700));
    const previous = current.map((v) =>
      round(v * (rate ? 0.95 + rand() * 0.2 : 0.65 + rand() * 0.6)),
    );
    const pct = weights(current);
    return table(
      labels.map((date, i) => ({
        date,
        previous: previous[i],
        current: current[i],
        change: round(current[i] - previous[i]),
        share: pct[i],
      })),
      [
        col('date', rate ? '示例券商' : '行业 / 类别'),
        col('previous', '上期', rate ? '%' : '亿元'),
        col('current', '本期', rate ? '%' : '亿元'),
        col('change', '变化', rate ? '百分点' : '亿元', true),
        ...(rate ? [] : [col('share', '本期占比', '%', true)]),
      ],
    );
  }
  if (spec.recipe === 'accounting') {
    return table(
      dates
        .filter((_, i) => i % 3 === 2)
        .map((date, i) => {
          const fvoci = Math.round(4000 + i * 390 + rand() * 600),
            fvtpl = Math.round(3000 + i * 110 + rand() * 400);
          return {
            date,
            fvoci,
            fvtpl,
            total: fvoci + fvtpl,
            pct: round((fvoci / (fvoci + fvtpl)) * 100),
          };
        }),
      [
        col('date', '报告期'),
        col('fvoci', 'FVOCI股票', '亿元'),
        col('fvtpl', 'FVTPL股票', '亿元'),
        col('total', '合计', '亿元'),
        col('pct', 'FVOCI占比', '%', true),
      ],
    );
  }
  if (spec.recipe === 'stockStyle') {
    return table(
      Array.from({ length: 24 }, (_, i) => ({
        date: `示例证券${String(i + 1).padStart(2, '0')}`,
        direction: i < 12 ? '增持组' : '减持组',
        industry: industries[i % 12],
        dividend: round(2 + rand() * 5),
        pe: round(6 + rand() * 25),
        change: round((i < 12 ? 1 : -1) * (0.1 + rand() * 0.9)),
      })),
      [
        col('date', '示例证券'),
        col('direction', '分组'),
        col('industry', '行业'),
        col('dividend', '股息率', '%'),
        col('pe', 'PE', '倍'),
        col('change', '权重变化', '百分点', true),
      ],
    );
  }
  if (spec.recipe === 'events') {
    const indexEvent = id === 'foreign-msci',
      placard = id === 'insurance-placards';
    return table(
      Array.from({ length: 18 }, (_, i) => ({
        date: dates[dates.length - 18 + i],
        entity: indexEvent
          ? `示例指数调整${i + 1}`
          : `示例${placard ? '险企' : '基金'}${String.fromCharCode(65 + (i % 6))}`,
        security: `示例证券${String((i % 12) + 1).padStart(2, '0')}`,
        event: indexEvent
          ? '纳入因子调整'
          : placard
          ? '持股达到举牌比例'
          : ['原有重仓', '新进重仓', '退出重仓'][i % 3],
        before: !indexEvent && !placard && i % 3 === 1 ? 0 : round(2 + rand() * 2),
        after: !indexEvent && !placard && i % 3 === 2 ? 0 : round(5 + rand() * 2),
        amount: Math.round(10 + rand() * 120),
      })),
      [
        col('date', '日期'),
        col('entity', indexEvent ? '示例事件' : '示例机构'),
        col('security', '示例证券'),
        col('event', '事项'),
        col('before', '调整前比例', '%'),
        col('after', '调整后比例', '%'),
        col('amount', '对应金额', '亿元'),
      ],
    );
  }
  const corporate = id === 'corporate-net';
  const names = corporate
    ? ['股东增持', '股东减持']
    : ['IPO现金募集', '再融资现金募集', '实施回购', '现金分红'];
  return chart(
    dates.map((date) => {
      const values = names.map(
        (_, i) => Math.round(150 + rand() * 700) * (corporate ? (i ? -1 : 1) : i < 2 ? -1 : 1),
      );
      return { date, ...Object.fromEntries(values.map((v, i) => [`v${i}`, v])), net: sum(values) };
    }),
    [
      ...names.map((n, i) => line(`v${i}`, n, '亿元', i, true, false, 'supply')),
      line('net', '合计净额', '亿元', 0),
    ],
  );
}

function series(spec: DemoSpec, dates: string[]): DemoData {
  const metrics = spec.metrics || [];
  const rand = random(hash(spec.id));
  const phase = rand() * Math.PI;
  const flowPhase = FOREIGN_COMPARISON_IDS.includes(spec.id)
    ? random(hash('foreign-macro-flow'))() * Math.PI
    : phase;
  const rows: FinanceRow[] = dates.map((date, i) => ({
    date,
    ...Object.fromEntries(
      metrics.map((m, j) => {
        const metricPhase = j === 0 ? flowPhase : phase;
        const wave =
          Math.sin(i * 0.48 + metricPhase + j * 1.3) * 0.7 + Math.cos(i * 0.21 + j) * 0.3;
        return [
          `v${j}`,
          round(m.base + wave * (m.amplitude ?? m.base * 0.15) + ((m.trend || 0) * i) / 35),
        ];
      }),
    ),
  }));
  if (spec.id === 'fund-active-passive')
    rows.forEach((r) => {
      r.v1 = round(100 - Number(r.v0));
    });
  if (spec.id === 'etf-full-flow') {
    let running = 0;
    rows.forEach((r) => {
      running = round(running + Number(r.v0));
      r.v1 = running;
    });
  }
  return chart(
    rows,
    metrics.map((m, i) => line(`v${i}`, m.name, m.unit, i, m.bar, m.right)),
  );
}
