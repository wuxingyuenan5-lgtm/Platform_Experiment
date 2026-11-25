import type { WidgetConfig } from '../nativeData/dashboardClean';

export interface MacroDetailGroup {
  key: string;
  label: string;
  includes: (widget: WidgetConfig) => boolean;
}

const china = (widget: WidgetConfig) => widget.region === '中国';
const regional: MacroDetailGroup[] = [
  { key: 'us', label: '美国', includes: (widget) => widget.region === '美国' },
  { key: 'cn', label: '中国', includes: china },
  {
    key: 'other',
    label: '其他经济体',
    includes: (widget) => !['美国', '中国'].includes(widget.region || ''),
  },
];
const volatility = (widget: WidgetConfig) =>
  ['macro-vix', 'macro-move', 'macro-vxeem'].includes(widget.localKey || '');
const overseasRates = (widget: WidgetConfig) =>
  ['macro-jp10y', 'macro-europe-yields', 'macro-europe-spreads'].includes(widget.localKey || '');
const fxFunding = (widget: WidgetConfig) =>
  ['macro-cross-currency-basis', 'macro-fx-swap-points'].includes(widget.localKey || '');

export const macroDetailGroups: Record<string, readonly MacroDetailGroup[]> = {
  'macro-liquidity': [
    { key: 'global', label: '全球与美元', includes: (widget) => !china(widget) },
    { key: 'cn', label: '中国', includes: china },
  ],
  'macro-rates': regional.slice(0, 2),
  'macro-growth': regional,
  'macro-inflation': regional,
  'macro-risk-appetite': [
    { key: 'volatility', label: '波动率', includes: volatility },
    {
      key: 'credit',
      label: '信用与金融状况',
      includes: (widget) => !china(widget) && !volatility(widget),
    },
    { key: 'cn', label: '中国', includes: china },
  ],
  'macro-fx': [
    {
      key: 'fx',
      label: '汇率',
      includes: (widget) => !overseasRates(widget) && !fxFunding(widget),
    },
    { key: 'rates', label: '海外利率', includes: overseasRates },
    { key: 'funding', label: '跨币种融资', includes: fxFunding },
  ],
};

// The existing weekly-report batch is mostly Chinese high-frequency data.
// Its global/overseas exceptions are explicit so each indicator has one home.
const overseasGrowth = new Set([
  'bdi',
  'global_manufacturing_pmi',
  'global_composite_pmi',
  'kr_gdp_quarter_yoy',
  'jp_gdp_quarter_yoy',
]);
const overseasInflation = new Set(['crb', 'lme_copper_stocks', 'lme_copper_3m']);
export function weeklyDetailGroup(section: string, id: string): string {
  switch (section) {
    case 'macro-liquidity':
      return ['us_m2_yoy', 'jp_m2_yoy', 'ea_m2_yoy', 'gb_m2_yoy', 'kr_m2_yoy'].includes(id)
        ? 'global'
        : 'cn';
    case 'macro-growth':
      return overseasGrowth.has(id) ? 'other' : 'cn';
    case 'macro-inflation':
      return overseasInflation.has(id) ? 'other' : 'cn';
    case 'macro-risk-appetite':
      return id === 'us_epu' || id === 'euronext_report' ? 'credit' : 'cn';
    case 'macro-fx':
      return 'fx';
    default:
      return '';
  }
}

export function hasWeeklyDetail(section: string, group: string): boolean {
  return (
    (
      {
        'macro-liquidity': ['global', 'cn'],
        'macro-growth': ['cn', 'other'],
        'macro-inflation': ['cn', 'other'],
        'macro-risk-appetite': ['credit', 'cn'],
        'macro-fx': ['fx'],
      } as Record<string, string[]>
    )[section]?.includes(group) || false
  );
}
