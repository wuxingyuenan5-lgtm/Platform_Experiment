// Transcribed from the supplied observation table dated 2026-11-16.
type Metric = 'PE' | 'PB' | 'DY' | 'PS';
type Reading = [value: number, percentile: number];
type Observation = [
  name: string,
  code: string,
  metric: Metric,
  percentile: number,
  pe: Reading,
  pb: Reading,
  dividend: Reading,
  listedFund: string | null,
  unlistedFund: string | null,
  ps?: number,
];

export const snapshotDate = '2026-11-16';

type SnapshotGroup = { name: string; rows: Observation[] };
export type ObservationGroup = {
  name: string;
  rows: [name: string, code: string, metric: Metric][];
};

// Fund entries use code|display label. A ~ after the code marks an approximate mapping.
export const globalMarketGroup: SnapshotGroup = {
  name: '全球市场主要宽基',
  rows: [
    [
      'MSCI美国50',
      '750108.MI',
      'PE',
      13.8,
      [24.12, 14],
      [6.75, 52],
      [0.74, 21],
      '513850|美国50ETF易方达',
      null,
    ],
    [
      '纳斯达克100',
      'NDX.GI',
      'PE',
      21.5,
      [26.91, 22],
      [8.24, 59],
      [0.47, 6],
      '159941|纳指ETF广发',
      '270042|广发纳斯达克100ET…',
    ],
    [
      '标普500',
      'SPX.GI',
      'PE',
      39.6,
      [23.62, 40],
      [5.29, 89],
      [1.06, 5],
      '513500|标普500ETF博时',
      '050025|博时标普500ETF联…',
    ],
    [
      '道琼斯工业',
      'DJI.GI',
      'PE',
      39.9,
      [23.41, 40],
      [7.66, 81],
      [0.77, 3],
      '513400|道琼斯ETF鹏华',
      null,
    ],
    [
      '德国DAX',
      'GDAXI.GI',
      'PB',
      59.4,
      [19.24, 65],
      [1.78, 59],
      [2.42, 0],
      '513030|德国ETF华安',
      '000614|华安德国(DAX)联接…',
    ],
    [
      '法国CAC40',
      'FCHI.GI',
      'PB',
      90.5,
      [16.95, 41],
      [2.04, 91],
      [3.04, 39],
      '513080|法国ETF华安',
      '021539|华安法国CAC40ETF…',
    ],
    [
      '日经225',
      'N225.GI',
      'PB',
      93.7,
      [20.54, 65],
      [2.52, 94],
      [1.54, 18],
      '513880|日经225ETF华安',
      '020712|华安三菱日联日经2…',
    ],
  ],
};

export const observationGroups: ObservationGroup[] = [
  {
    name: 'A股核心宽基',
    rows: [
      ['中证全指', '000985.CSI', 'PE'],
      ['上证50', '000016.SH', 'PE'],
      ['沪深300', '000300.SH', 'PE'],
      ['创业板指', '399006.SZ', 'PE'],
      ['科创50', '000688.SH', 'PB'],
      ['中证1000', '000852.SH', 'PE'],
      ['国证2000', '399303.SZ', 'PE'],
      ['恒生指数', 'HSI.HI', 'PE'],
      ['恒生国企', 'HSCEI.HI', 'PE'],
      ['深证100', '399330.SZ', 'PE'],
      ['深证成指', '399001.SZ', 'PE'],
      ['中证500', '000905.SH', 'PE'],
      ['中证A500', '000510.CSI', 'PE'],
      ['中证800', '000906.SH', 'PE'],
      ['中证A100', '000903.SH', 'PE'],
      ['北证50', '899050.BJ', 'PB'],
    ],
  },
  {
    name: '红利策略与特色宽基',
    rows: [
      ['红利质量', '931468.CSI', 'PE'],
      ['自由现金流', '932365.CSI', 'PE'],
      ['消费红利', 'H30094.CSI', 'PB'],
      ['深证红利', '399324.SZ', 'DY'],
      ['红利低波100', '930955.CSI', 'DY'],
      ['红利低波', 'H30269.CSI', 'DY'],
      ['中证红利', '000922.CSI', 'DY'],
      ['300红利低波', '930740.CSI', 'DY'],
      ['上证红利', '000015.SH', 'DY'],
      ['港股通红利', '930914.CSI', 'DY'],
      ['央企红利50', '931231.CSI', 'DY'],
    ],
  },
  {
    name: '板块宽基与策略指数',
    rows: [
      ['创业板50', '399673.SZ', 'PE'],
      ['创价值', '399295.SZ', 'PE'],
      ['基本面50', '000925.CSI', 'PE'],
      ['300价值', '000919.CSI', 'PE'],
      ['央视50', '399550.SZ', 'PE'],
      ['创成长', '399296.SZ', 'PB'],
      ['300成长', '000918.CSI', 'PB'],
      ['科创创业50', '931643.CSI', 'PB'],
      ['成长100', '980080.CNI', 'PB'],
      ['价值100', '980081.CNI', 'DY'],
    ],
  },
];

export const industryObservationGroups: ObservationGroup[] = [
  {
    name: '主要行业',
    rows: [
      ['光伏产业', '931151.CSI', 'PB'],
      ['中证中药', '930641.CSI', 'PB'],
      ['全指医药', '000991.SH', 'PB'],
      ['食品饮料', '000807.CSI', 'PB'],
      ['中证白酒', '399997.SZ', 'PB'],
      ['800消费', '000932.SH', 'PB'],
      ['300医药', '000913.SH', 'PB'],
      ['消费龙头', '931068.CSI', 'PB'],
      ['医药50', '931140.CSI', 'PB'],
      ['家用电器', '882449.WI', 'PB'],
      ['中证医疗', '399989.SZ', 'PB'],
      ['科技龙头', '931087.CSI', 'PB'],
      ['恒生消费', 'HSCGSI.HI', 'PB'],
      ['恒生科技', 'HSTECH.HI', 'PS'],
      ['中国互联网50', 'H30533.CSI', 'PS'],
      ['恒生互联网', 'HSIII.HI', 'PS'],
    ],
  },
  {
    name: '细分行业',
    rows: [
      ['医疗器械', 'H30217.CSI', 'PB'],
      ['中证新能', '399808.SZ', 'PB'],
      ['中证传媒', '399971.SZ', 'PB'],
      ['CS创新药', '931152.CSI', 'PB'],
      ['5G通信', '931079.CSI', 'PB'],
      ['机器人', 'H30590.CSI', 'PB'],
      ['国证芯片', '980017.SZ', 'PB'],
      ['半导体', '882121.WI', 'PB'],
    ],
  },
  {
    name: '周期行业',
    rows: [
      ['基建工程', '399995.SZ', 'PB'],
      ['300非银', '000849.SH', 'PB'],
      ['中证旅游', '930633.CSI', 'PB'],
      ['证券精选', '8841357.WI', 'PB'],
      ['国证地产', '399393.SZ', 'PB'],
      ['中证环保', '000827.SH', 'PB'],
      ['细分化工', '000813.CSI', 'PB'],
      ['中证畜牧', '930707.CSI', 'PB'],
      ['港股通非银', '931024.CSI', 'PB'],
      ['中证军工', '399967.SZ', 'PB'],
      ['中证有色', '930708.CSI', 'PB'],
      ['中证银行', '399986.SZ', 'PB'],
      ['中证煤炭', '399998.SZ', 'PB'],
    ],
  },
];
