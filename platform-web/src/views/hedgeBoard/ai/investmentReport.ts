/** Report snapshots and explicitly synthetic illustrations. No live-data fallback. */
export type ReportStatus = 'snapshot' | 'demo';
export interface ReportSeries {
  name: string;
  values: (number | null)[];
  right?: boolean;
  bar?: boolean;
}
export interface ReportChart {
  id: string;
  title: string;
  page: string;
  status: ReportStatus;
  asOf: string;
  basis: string;
  unit: string;
  rightUnit?: string;
  labels: string[];
  series: ReportSeries[];
  scatter?: { name: string; x: number; y: number; group: string }[];
  xUnit?: string;
  peg?: boolean;
}
export interface ReportTopic {
  id: number;
  group: string;
  title: string;
  question: string;
  page: string;
  charts: ReportChart[];
  map?: { name: string; items: string[] }[];
}
export const reportSource = {
  title: '兴证策略张启尧团队 ·《策略研究笔记》系列一：AI投资篇',
  published: '2026-08-17',
  // Publication date comes from PDF p.1; 2026-11-09 is the print date only.
};
export const reportGroups = [
  { key: 'capex', name: '资本开支与高频验证', ids: '09—12' },
  { key: 'cycle', name: '历史周期与盈利', ids: '03—08' },
  { key: 'position', name: '全球权重与交易热度', ids: '13—15' },
  { key: 'rotation', name: '日历效应与产业轮动', ids: '16—19' },
  { key: 'valuation', name: '渗透率与估值', ids: '20—22' },
  { key: 'map', name: '产业链与上游材料', ids: '01—02' },
];
const round = (v: number) => Math.round(v * 100) / 100;
function months(year: number, month: number, n: number) {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(Date.UTC(year, month - 1 + i, 1));
    return d.toISOString().slice(0, 7);
  });
}
/** Fixed anchors + deterministic oscillation, used exclusively for Demo charts. */
export function demoCurve(anchors: number[], length: number, amplitude = 0) {
  return Array.from({ length }, (_, i) => {
    const p = (i / (length - 1)) * (anchors.length - 1);
    const j = Math.min(Math.floor(p), anchors.length - 2);
    const t = p - j;
    return round(
      anchors[j] * (1 - t) +
        anchors[j + 1] * t +
        amplitude * Math.sin(i * 1.71) * Math.sin(Math.PI * t),
    );
  });
}
const series = (
  name: string,
  anchors: number[],
  n: number,
  right = false,
  amplitude = 0,
): ReportSeries => ({ name, values: demoCurve(anchors, n, amplitude), right });
function demo(
  id: string,
  title: string,
  page: string,
  labels: string[],
  unit: string,
  lines: ReportSeries[],
  basis: string,
  rightUnit?: string,
): ReportChart {
  return {
    id,
    title,
    page,
    labels,
    unit,
    series: lines,
    basis,
    rightUnit,
    status: 'demo',
    asOf: '模拟区间：' + labels[0] + ' 至 ' + labels.at(-1),
  };
}
function snapshot(
  id: string,
  title: string,
  page: string,
  asOf: string,
  labels: string[],
  values: number[],
  basis: string,
): ReportChart {
  return {
    id,
    title,
    page,
    asOf,
    labels,
    unit: '%',
    series: [{ name: title, values, bar: true }],
    basis,
    status: 'snapshot',
  };
}
const m13 = months(2013, 1, 162),
  m23 = months(2023, 1, 43),
  m25 = months(2025, 1, 18);
const m94 = months(1994, 1, 96),
  m96 = months(1996, 1, 84),
  m95 = months(1995, 1, 377);
const capex = [8, 35, -12, 40, 12, 30, -5, 21, 45, 82];
const c = (
  id: number,
  group: string,
  title: string,
  question: string,
  page: string,
  charts: ReportChart[],
): ReportTopic => ({ id, group, title, question, page, charts });

export const drawdowns = [
  ['科网', '1995-09-13', '1995-10-10', -7.9, 27],
  ['科网', '1996-01-02', '1996-01-10', -6.5, 8],
  ['科网', '1996-06-12', '1996-07-24', -15.6, 42],
  ['科网', '1997-01-22', '1997-04-02', -13.5, 70],
  ['科网', '1997-10-09', '1997-12-04', -7.6, 56],
  ['科网', '1998-04-22', '1998-06-15', -10.5, 54],
  ['科网', '1998-07-20', '1998-10-08', -29.5, 80],
  ['科网', '1999-02-01', '1999-02-10', -8.0, 9],
  ['科网', '1999-07-16', '1999-08-10', -13.1, 25],
  ['科网', '1999-10-11', '1999-10-18', -7.8, 7],
  ['科网', '2000-01-03', '2000-01-06', -9.8, 3],
  ['科网', '2000-01-21', '2000-01-28', -8.2, 7],
  ['AI', '2022-12-01', '2022-12-28', -11.1, 27],
  ['AI', '2023-02-02', '2023-03-10', -8.7, 36],
  ['AI', '2023-07-31', '2023-10-26', -12.2, 87],
  ['AI', '2024-04-11', '2024-04-19', -7.1, 8],
  ['AI', '2024-07-10', '2024-08-05', -13.1, 26],
  ['AI', '2024-08-19', '2024-09-06', -6.6, 18],
  ['AI', '2025-02-20', '2025-04-08', -23.5, 47],
  ['AI', '2025-10-29', '2025-11-20', -7.8, 22],
  ['AI', '2026-01-28', '2026-03-30', -12.8, 61],
] as const;
export function drawdownSummary(cycle: string) {
  const rows = drawdowns.filter((r) => r[0] === cycle);
  const average = (index: 3 | 4) => round(rows.reduce((sum, r) => sum + r[index], 0) / rows.length);
  return { count: rows.length, depth: average(3), days: average(4) };
}
const chain = [
  ['上游 · 网络通信硬件', '光模块 PCB 高速铜缆 光纤光缆 交换机'],
  ['上游 · 芯片存储', 'CPU GPU ASIC 存储芯片 模拟芯片 半导体设备材料 半导体封测'],
  ['上游 · 智算中心AIDC', '算力租赁 服务器 液冷 电力电网 电源设备'],
  ['中游 · 模型算法', '基础大模型 多模态模型 计算机视觉'],
  ['中游 · 软件', '操作系统 数据库 EDA 办公软件 企业软件 工业软件 网络安全'],
  ['中游 · 服务', '云厂商 AI编程 运营商 IT服务'],
  ['下游 · AI端侧', 'AI手机 AIPC AI穿戴设备 人形机器人 VR 卫星通信 智能驾驶 智能家居'],
  [
    '下游 · AI应用',
    '游戏 数字媒体 广告营销 影视视频 出版 金融科技 电商零售 在线教育 智慧医疗 电子政务 军工信息化',
  ],
];
const materials = [
  [
    '半导体',
    '溅射靶材 光刻胶 CMP抛光材料 湿化学品 光掩膜版 玻璃基板 硅片 碳化硅 氮化铝 金刚石 电子特气',
  ],
  [
    'PCB / 覆铜板CCL',
    '电子铜箔 电子布 PPO树脂 PTFE树脂 球形硅微粉 ABF/NBF膜 专用湿化学品 钨棒及钻针 感光干膜',
  ],
  ['光纤', '光纤预制棒 高纯石英砂 四氯化硅 四氯化锗 UV涂覆树脂'],
  ['光模块', '磷化铟 铌酸锂 旋光片'],
  ['MLCC', '介质粉体 掺杂剂 离型膜 银钯浆'],
  ['MLPC / 铝电容', '高纯铝及电极箔 铝粉铝丝'],
  ['电阻 / 电感', '绝缘基板 钌系浆料 磁粉'],
  ['液冷', '电子氟化液 硅基冷却液'],
];

export const reportTopics: ReportTopic[] = [
  {
    ...c(
      1,
      'map',
      'AI产业链细分方向',
      '按基础设施、模型服务与终端应用定位研究对象。分类来自报告，不等于公司收入暴露。',
      '2—3',
      [],
    ),
    map: chain.map(([name, items]) => ({ name, items: items.split(' ') })),
  },
  {
    ...c(
      2,
      'map',
      'AI上游材料图谱',
      '沿芯片、互联、供电与散热寻找材料需求。原图不可辨识的单元不补造名称。',
      '3',
      [],
    ),
    map: materials.map(([name, items]) => ({ name, items: items.split(' ') })),
  },
  c(
    3,
    'cycle',
    '科网行情与AI行情走到哪里？',
    '以事件发生月归一化，比较时间和幅度；历史类比不表示本轮将复现同一路径。',
    '3—4',
    [
      demo(
        'cycle-path',
        'Netscape与ChatGPT发布后的纳指路径',
        '4',
        Array.from({ length: 73 }, (_, i) => 'T+' + i + '月'),
        '起点=1',
        [
          series('科网周期 · Demo', [1, 1.4, 1.7, 2.3, 3.1, 6.8, 3.4], 73),
          {
            name: 'AI周期 · Demo',
            values: [...demoCurve([1, 1.25, 1.6, 1.8, 2.25], 44, 0.1), ...Array(29).fill(null)],
          },
        ],
        '两轮起点分别为1994-12与2022-11；AI仅画至T+43月，之后为空，不推演未来。',
      ),
    ],
  ),
  c(
    4,
    'cycle',
    '加息与科技行情的转折',
    '同时观察通胀、政策利率与股价，区分先后关系和因果解释。',
    '4',
    [
      demo(
        'rates',
        '1996—2002：CPI、联邦基金利率与纳指',
        '4',
        m96,
        '%',
        [
          series('CPI同比', [2.7, 3.2, 1.4, 2.2, 3.5, 1.2, 2.3], 84),
          series('联邦基金目标利率', [5.5, 5.25, 5.5, 4.75, 6.5, 1.75, 1.25], 84),
          series('纳斯达克指数', [1000, 1300, 1700, 2200, 5000, 1800, 1300], 84, true, 150),
        ],
        '历史区间为结构示意，政策利率折线不是逐次议息记录。',
        '点',
      ),
    ],
  ),
  c(
    5,
    'cycle',
    '流动性收紧与景气溢价',
    '比较行业盈利预期与相对排名；报告关于资金集中于高景气行业的解释属于历史研究。',
    '5',
    [
      demo(
        'sector-eps',
        '行业未来12个月EPS增速预期',
        '5',
        [
          '能源',
          '原材料',
          '工业',
          '医疗保健',
          '电信',
          '金融',
          '科技',
          '公用事业',
          '可选消费',
          '必需消费',
          '房地产',
        ],
        '%',
        [
          {
            name: '1998年底预期 · Demo',
            values: [-1, 23, 36, 22, 32, 21, 73, 27, -6, 26, 12],
            bar: true,
          },
        ],
        '按原图结构构造的示例值，未从FactSet取得原始预期。',
      ),
      demo(
        'sector-ranking',
        '科技与其他行业：年度涨幅排名',
        '5',
        ['1995', '1996', '1997', '1998', '1999', '2000Q1'],
        '名次（1最高）',
        [
          series('科技硬件', [13, 1, 5, 3, 3, 2], 6),
          series('软件与计算机服务', [8, 4, 13, 2, 1, 7], 6),
          series('医疗服务', [10, 6, 2, 5, 8, 10], 6),
        ],
        '精选三类行业的排名示意，未复原原表全行业排序。',
      ),
    ],
  ),
  c(
    6,
    'cycle',
    '历史回撤的时间与空间',
    '保留报告选取的21段调整；这是事件样本，不是完整回撤分布，也不是止损阈值。',
    '5—6',
    [
      {
        id: 'drawdowns',
        title: '回撤幅度与持续天数',
        page: '5—6',
        status: 'snapshot',
        asOf: '2026-06-30',
        unit: '回撤 %',
        xUnit: '持续天数',
        labels: [],
        series: [],
        basis: '逐行转录报告表格；天数沿用原表，不重新解释为交易日。',
        scatter: drawdowns.map((r) => ({
          name: r[1] + ' → ' + r[2],
          x: r[4],
          y: r[3],
          group: r[0],
        })),
      },
    ],
  ),
  c(
    7,
    'cycle',
    '科技牛市：盈利水平还是增速？',
    '分开观察EPS水平和同比增速，避免盈利仍增长就等同于景气未转弱。',
    '6',
    [
      demo(
        'eps-level',
        '科技股指数与EPS水平',
        '6',
        months(1985, 1, 252),
        '指数点',
        [
          series('科技股指数', [250, 260, 400, 600, 3000, 700, 1300], 252),
          series('EPS', [8, 7, 10, 15, 48, 18, 49], 252, true),
        ],
        '报告历史关系的模拟示意。',
        'EPS',
      ),
      demo(
        'eps-growth',
        'EPS同比与科技股价格同比',
        '6',
        m94,
        '%',
        [
          series('EPS同比', [20, 60, 15, 45, 15, 40, -65, -40], 96),
          series('股价同比', [10, 50, 5, 65, 25, 90, -50, -60], 96),
        ],
        '两条同比曲线均为Demo；不是可回测信号。',
      ),
    ],
  ),
  c(
    8,
    'cycle',
    '龙头增速回落与估值门槛',
    '报告用微软历史说明“增速回落”与“跌破估值隐含增长”不同；30%只是当时案例。',
    '6—7',
    [
      demo(
        'msft-cycle',
        '微软EPS增速与股价：两次增速高点',
        '6—7',
        months(1996, 1, 66),
        '%',
        [
          series('EPS TTM同比', [10, 72, 32, 36, 65, -5], 66),
          series('股价', [6, 12, 23, 40, 58, 25], 66, true),
        ],
        '股价与EPS均为模拟值；不将30%阈值应用于今天。',
        '美元',
      ),
      demo(
        'pe-history',
        '主要科技指数历史PE均值',
        '7',
        [
          '纳斯达克',
          '纳指100',
          '费城半导体',
          'MSCI世界科技',
          'MSCI美国科技',
          'MSCI全球科技',
          'MSCI欧洲科技',
          'MSCI中国科技',
          'MSCI新兴科技',
        ],
        '倍',
        [{ name: '历史PE · Demo', values: [28, 26, 35, 38, 34, 31, 26, 37, 23], bar: true }],
        '原图未提供完整样本起止与逐点值，仅复刻比较形式。',
      ),
    ],
  ),
  c(
    9,
    'capex',
    '科技股盈利的核心观察：云厂商Capex',
    '把半导体和科技硬件盈利预期，与北美云厂商资本开支增速并列观察。',
    '7',
    [
      demo(
        'sox-capex',
        '半导体盈利预期 × 北美云厂商Capex',
        '7',
        m13,
        '%',
        [
          series('SOX未来12个月EPS同比', [10, 28, -9, 42, 15, 26, -20, 16, 37, 66], 162, false, 7),
          series('云厂商Capex同比', capex, 162, true, 5),
        ],
        'EPS为未来12个月一致预期，Capex为公司整体资本开支；本图均为模拟序列。',
        '%',
      ),
      demo(
        'hardware-capex',
        '科技硬件盈利预期 × 北美云厂商Capex',
        '7',
        m13,
        '%',
        [
          series('科技硬件EPS同比', [5, 12, -5, 25, 4, 15, -8, 6, 21, 32], 162, false, 3),
          series('云厂商Capex同比', capex, 162, true, 5),
        ],
        '相同时间轴用于对照，不声称预测能力或因果。',
        '%',
      ),
    ],
  ),
  c(
    10,
    'capex',
    '资本开支预期如何被持续上修？',
    '区分年初预期、实际增速与不同目标年份的预期修订。',
    '7—8',
    [
      demo(
        'capex-surprise',
        '资本开支：年初预期与报告时点估计',
        '8',
        ['2024', '2025', '2026E'],
        '%',
        [
          { name: '年初预期 · Demo', values: [19, 22, 36], bar: true },
          { name: '实际/报告时点估计 · Demo', values: [55, 74, 90], bar: true },
        ],
        '2026E仍为预测，其他年度亦为示例值；不作为最新资本开支指引。',
      ),
      demo(
        'capex-revision',
        '2026—2029年资本开支一致预期修订',
        '8',
        m25,
        '亿美元',
        [
          series('2026E', [3000, 3400, 3800, 5200, 6000, 7200], 18),
          series('2027E', [3100, 3600, 4000, 5900, 6500, 8800], 18),
          series('2028E', [3200, 3700, 4100, 6200, 6800, 9200], 18),
          series('2029E', [3300, 3800, 4200, 6400, 7200, 9800], 18),
        ],
        '横轴是预期观察月，线条是目标年份；为Demo，不接入FactSet一致预期。',
      ),
    ],
  ),
  c(
    11,
    'capex',
    '模型收入与资本开支回报',
    '跟踪模型商业化和云厂商投入预期，但ARR不等同于会计收入或已实现利润。',
    '8',
    [
      demo(
        'model-arr',
        'OpenAI与Anthropic ARR轨迹',
        '8',
        m23.slice(0, 42),
        '十亿美元/年',
        [
          series('OpenAI ARR · Demo', [0.5, 1.7, 3.5, 8, 12, 22], 42),
          series('Anthropic ARR · Demo', [0.1, 0.3, 1, 3, 8, 48], 42),
        ],
        '仅为报告图形结构模拟；未独立核验非上市公司的ARR口径与披露值。',
      ),
      demo(
        'arr-event',
        'ARR披露前后：未来一年Capex预期变化',
        '8',
        Array.from({ length: 61 }, (_, i) => 'T' + (i < 20 ? i - 20 : '+' + (i - 20))),
        'T0=1',
        [
          {
            name: 'OpenAI事件 · Demo',
            values: demoCurve([0.97, 1, 1.01, 1.04, 1.07], 61, 0.01).map((v, _, arr) =>
              round(v / arr[20]),
            ),
          },
          {
            name: 'Anthropic事件 · Demo',
            values: demoCurve([0.98, 1, 1.03, 1.07, 1.13], 61, 0.01).map((v, _, arr) =>
              round(v / arr[20]),
            ),
          },
        ],
        'T为相对观察日；模拟事件窗口，不代表真实事件样本平均或因果检验。',
      ),
    ],
  ),
  c(
    12,
    'capex',
    '高频跟踪：GPU租赁与韩国出口',
    '价格、出口与资本开支分别对应算力供需、硬件出货和投入计划，不能相互替代。',
    '8—9',
    [
      demo(
        'gpu-rental',
        'H100/H200租赁价格与Capex增速',
        '9',
        m25,
        '美元/小时',
        [
          series('GPU租赁价格 · Demo', [2.4, 2.8, 2.5, 2.15, 2.05, 2.95, 2.6], 18),
          series('Capex同比', [72, 78, 74, 76, 74, 88], 18, true),
        ],
        'GPU规格、地区、租期会改变价格；本图未接入实时租赁报价。',
        '%',
      ),
      demo(
        'korea-export',
        '韩国前20日出口同比 × Capex',
        '9',
        months(2016, 4, 123),
        '%',
        [
          series('出口金额同比', [0, 30, -10, 15, -15, 45, -10, 20, 55], 123, false, 12),
          series('Capex同比', [0, 120, -10, 40, -20, 40, 10, 60, 95], 123, true, 8),
        ],
        '前20日快报与全月口径不同；本图为模拟。',
        '%',
      ),
      demo(
        'korea-chip',
        '韩国前20日半导体出口同比 × Capex',
        '9',
        months(2017, 1, 114),
        '%',
        [
          series('半导体出口同比', [10, 80, -30, 20, 5, 35, -40, 50, 200], 114, false, 16),
          series('Capex同比', [20, 140, -10, 40, 10, 60, -5, 65, 100], 114, true, 10),
        ],
        '半导体子项独立于出口总额，不混用季节调整口径。',
        '%',
      ),
    ],
  ),
  c(
    13,
    'position',
    '全球科技板块市值占比',
    '横向比较市场结构，历史序列与报告单点快照分别标记。',
    '9',
    [
      snapshot(
        'market-cap',
        '全球主要市场科技市值占比',
        '9',
        '2026-05',
        ['中国台湾', '韩国', '美国', 'A股', '日本', '中国香港', '欧洲', '印度'],
        [77, 56, 45, 31, 21, 20, 14, 14],
        '按报告柱状图整数标签转录；行业分类与指数成分按报告原口径，未独立重算。',
      ),
      demo(
        'market-cap-history',
        '科技市值占比：历史对照',
        '9',
        m95,
        '%',
        [
          series('美国', [25, 44, 22, 20, 26, 32, 45], 377),
          series('韩国', [20, 35, 48, 45, 44, 42, 56], 377),
          series('A股', [7, 20, 12, 18, 25, 20, 31], 377),
          series('日本', [10, 32, 15, 11, 18, 19, 21], 377),
        ],
        '历史路径均为Demo，与上方转录快照分开；末点相同不意味着历史已核验。',
      ),
    ],
  ),
  c(
    14,
    'position',
    '全球科技板块成交占比',
    '成交占比衡量交易集中度，需要结合市值占比理解。不同观察日不直接相除。',
    '10',
    [
      snapshot(
        'turnover',
        '全球主要市场科技成交占比',
        '10',
        '2026-06-02',
        ['中国台湾', '韩国', '美国', '日本', 'A股', '中国香港'],
        [78, 62, 57, 51, 45, 44],
        '按报告图中标签转录；分母为各市场总成交，未独立重算。',
      ),
      demo(
        'turnover-history',
        '科技成交占比：历史对照',
        '10',
        m95,
        '%',
        [
          series('美国', [40, 55, 38, 32, 40, 44, 57], 377),
          series('韩国', [44, 65, 28, 35, 40, 41, 62], 377),
          series('A股', [7, 24, 12, 23, 29, 32, 45], 377),
          series('日本', [20, 35, 20, 22, 28, 32, 51], 377),
        ],
        '模拟各市场历史路径，不将图中长期高低点当作已核实记录。',
      ),
    ],
  ),
  c(
    15,
    'position',
    'TMT成交与市值占比',
    '同时观察成交热度、市场权重与价格；高集中度本身不是反转信号。',
    '10—11',
    [
      demo(
        'tmt',
        'TMT成交占比、市值占比与指数',
        '10—11',
        months(2010, 1, 198),
        '%',
        [
          series('成交占比', [12, 18, 48, 20, 40, 25, 50], 198, false, 6),
          series('市值占比', [9, 14, 28, 18, 26, 22, 31], 198),
          series('TMT指数', [1200, 1800, 7000, 2800, 5100, 3300, 6800], 198, true, 250),
        ],
        'A股TMT口径；三条曲线均为Demo，不与现有实时板块数据混接。',
        '点',
      ),
    ],
  ),
  c(
    16,
    'rotation',
    '财报窗口与日历效应',
    '把月度收益分布与产业相对强弱并列；不能用两个案例推断稳定季节规律。',
    '11',
    [
      demo(
        'calendar',
        '新能源与光模块：月度表现对比',
        '11',
        Array.from({ length: 12 }, (_, i) => i + 1 + '月'),
        '%',
        [
          {
            name: '2020—2021新能源月均 · Demo',
            values: [12, 1, 4, 9, 14, 18, 7, 2, -3, 5, 12, 3],
            bar: true,
          },
          {
            name: '2024年以来光模块月均 · Demo',
            values: [-6, 14, 1, 11, 6, 10, 3, 7, 0, 13, 2, 5],
            bar: true,
          },
        ],
        '仅为月度分布示意；未使用真实日收益计算，非季节性回测。',
      ),
      demo(
        'calendar-relative',
        '财报窗口附近的相对强弱',
        '11',
        m25,
        '起点=1',
        [
          series('光模块相对市场', [1, 1.3, 0.9, 1.15, 1.4, 1.9], 18),
          series('科技硬件相对软件', [1, 1.08, 0.95, 1.1, 1.28, 1.55], 18),
        ],
        '财报月份取决于市场与公司；图中关系不构成固定择时规则。',
      ),
    ],
  ),
  c(
    17,
    'rotation',
    '海外映射与产业链轮动',
    '对比中美上中下游，以及通信硬件/半导体与海外/国产算力的相对表现。',
    '11—12',
    [
      demo(
        'cross-market',
        '中美AI产业链：上游相对中下游',
        '11—12',
        m23,
        '起点=1',
        [
          series('美国AI上游/中下游', [1, 1.4, 1.15, 1.6, 2.1, 2.75], 43),
          series('A股AI上游/中下游', [1, 1.2, 1.03, 1.35, 1.75, 2.3], 43, true),
        ],
        '比值先分别归一化；成分与权重缺少原始定义，本图为Demo。',
        '起点=1',
      ),
      demo(
        'hardware-mapping',
        '通信硬件/半导体 × 海外/国产算力',
        '12',
        m23,
        '起点=1',
        [
          series('美股通信硬件/半导体', [1, 1.1, 1.25, 1.35, 1.6, 1.9], 43),
          series('A股海外/国产算力', [1, 1.08, 1.2, 1.32, 1.9, 2.6], 43, true),
        ],
        '两市场比值不代表同一资产；不以同步走势断言领先关系。',
        '起点=1',
      ),
      demo(
        'mapping-short',
        '短窗口观察：映射关系的偏离',
        '12',
        months(2026, 1, 7),
        '起点=1',
        [
          series('美国通信硬件/半导体', [1, 1.04, 0.99, 0.94, 0.83, 0.78, 0.8], 7),
          series('A股海外/国产算力', [1, 1.02, 1.13, 1.07, 0.99, 0.88, 0.91], 7, true),
        ],
        '独立短窗口Demo，不用于计算统计相关性。',
        '起点=1',
      ),
    ],
  ),
  c(
    18,
    'rotation',
    '海外算力与国产算力',
    '观察结构相对变化，并检查组合成员、行业权重及估值差异。',
    '12',
    [
      demo(
        'overseas-domestic',
        'A股：海外算力/国产算力',
        '12',
        m25,
        '相对比值',
        [series('海外/国产算力 · Demo', [1, 0.78, 1.05, 1.42, 1.02, 1.43, 0.95], 18, false, 0.08)],
        '海外：光模块、光纤、PCB等；国产：半导体材料设备、存储、服务器等。具体组合未复现。',
      ),
    ],
  ),
  c(
    19,
    'rotation',
    '产业轮动的盈利验证',
    '把上游/中下游相对表现与盈利增速差对照，区分价格变化和基本面变化。',
    '12—13',
    [
      demo(
        'rotation-us',
        '美股：产业链比值与盈利增速差',
        '13',
        m23,
        '起点=1',
        [
          series('上游/中下游', [1, 1.5, 1.3, 1.7, 2.1, 2.6], 43),
          series('业绩增速差', [0, 20, -45, 30, 160, 50], 43, true),
        ],
        '右轴是上游增速减中下游增速，单位为百分点；模拟值。',
        '百分点',
      ),
      demo(
        'rotation-cn',
        'A股：算力/软件与净利润增速差',
        '13',
        m23,
        '起点=1',
        [
          series('上游算力/中下游应用', [1, 1.08, 1.05, 1.2, 1.45, 2.3], 43),
          series('净利润增速差', [-10, -20, 15, 20, 30, 95], 43, true),
        ],
        '价格比值与增速差口径分开；不计算或暗示因果系数。',
        '百分点',
      ),
    ],
  ),
  c(
    20,
    'valuation',
    'AI渗透率：研究覆盖广度',
    '报告的渗透率是研报识别的相关公司数量占比，不是AI收入占比或用户采用率。',
    '13',
    [
      snapshot(
        'penetration',
        'A股主题渗透率比较',
        '13',
        '各柱所列年份；AI最新为2026-07',
        ['互联网+ 2015', '新能源+ 2022', 'AI+ 2026-07', 'AI+ 2025', 'AI+ 2024', 'AI+ 2023'],
        [36, 32, 28, 26, 13, 10],
        '原图标签转录；跨主题关键词和覆盖范围不同，不当作完全同口径时间序列。',
      ),
      demo(
        'sector-penetration',
        '各行业AI+与互联网+覆盖广度',
        '13',
        [
          '传媒',
          '计算机',
          '电子',
          '通信',
          '电力设备',
          '机械',
          '家电',
          '建筑',
          '汽车',
          '医药',
          '商贸',
          '金融',
          '食品饮料',
          '纺织',
          '煤炭',
        ],
        '%',
        [
          series(
            'AI+（2026-07）· Demo',
            [90, 85, 80, 52, 48, 40, 35, 32, 28, 24, 20, 12, 4, 2, 0],
            15,
          ),
          series(
            '互联网+（2013—2015）· Demo',
            [80, 72, 83, 40, 55, 25, 42, 58, 25, 52, 15, 35, 48, 32, 24],
            15,
          ),
        ],
        '保留行业横向比较形式，未转录小图全部31行业的精确值。',
      ),
    ],
  ),
  c(
    21,
    'valuation',
    '全球科技估值与盈利增速',
    '把估值和增长放在同一平面；PEG=1仅作参照，不能自动定义便宜或贵。',
    '13—14',
    [
      {
        id: 'global-peg',
        title: '全球科技板块 PE—G',
        page: '14',
        status: 'demo',
        asOf: '模拟截面：2026-07-10',
        unit: '未来12个月EPS增速 %',
        xUnit: '未来12个月PE（倍）',
        labels: [],
        series: [],
        peg: true,
        basis: '坐标为模拟假设，非原始一致预期；增长以百分数输入，参考线G=PE。',
        scatter: [
          ['韩国科技', 8, 260],
          ['费城半导体', 30, 105],
          ['日本科技', 24, 75],
          ['恒生科技', 17, 50],
          ['创业板指', 32, 65],
          ['全球科技', 26, 52],
          ['纳斯达克100', 29, 35],
          ['科创50', 78, 132],
          ['欧洲科技', 24, 28],
          ['中国台湾科技', 22, 43],
        ].map(([name, x, y]) => ({
          name: String(name),
          x: Number(x),
          y: Number(y),
          group: '全球科技',
        })),
      },
    ],
  ),
  c(
    22,
    'valuation',
    'AI细分环节的估值比较',
    '结合增长可持续性、现金回报和周期位置阅读PE—G；单一截面不生成买卖建议。',
    '14—15',
    [
      {
        id: 'segments-peg',
        title: 'AI细分板块 PE—G',
        page: '14—15',
        status: 'demo',
        asOf: '模拟截面：2026-07-10',
        unit: '2026年净利润增速 %',
        xUnit: 'PE（倍）',
        labels: [],
        series: [],
        peg: true,
        basis: 'PE与年度利润增速使用不同时间口径，仅复刻原图形式；所有点为Demo。',
        scatter: [
          ['湿化学品', 145, 280, '上游材料'],
          ['钨棒及钻针', 80, 185, '上游材料'],
          ['磷化铟', 18, 96, '上游材料'],
          ['溅射靶材', 130, 113, '上游材料'],
          ['MLCC', 70, 78, '上游材料'],
          ['电子特气', 50, 65, '上游材料'],
          ['光纤光缆', 145, 222, '海外算力'],
          ['光模块', 110, 145, '海外算力'],
          ['PCB', 80, 95, '海外算力'],
          ['交换机', 65, 105, '海外算力'],
          ['电源设备', 90, 115, '海外算力'],
          ['GPU', 260, 79, '国产算力'],
          ['模拟芯片', 270, 66, '国产算力'],
          ['存储芯片', 100, 145, '国产算力'],
          ['服务器', 65, 61, '国产算力'],
          ['电力电网', 25, 28, '国产算力'],
          ['云厂商', 28, 42, '中下游应用'],
          ['工业软件', 40, 50, '中下游应用'],
          ['办公软件', 34, 88, '中下游应用'],
        ].map(([name, x, y, group]) => ({
          name: String(name),
          x: Number(x),
          y: Number(y),
          group: String(group),
        })),
      },
    ],
  ),
];

export function chartRows(chart: ReportChart): (string | number | null)[][] {
  if (chart.scatter) return chart.scatter.map((p) => [p.name, p.group, p.x, p.y]);
  return chart.labels.map((label, i) => [label, ...chart.series.map((s) => s.values[i] ?? null)]);
}
export function chartHeaders(chart: ReportChart): string[] {
  return chart.scatter
    ? ['对象', '分组', chart.xUnit || 'X', chart.unit]
    : [
        '观察期 / 分类',
        ...chart.series.map((s) => s.name + '（' + (s.right ? chart.rightUnit : chart.unit) + '）'),
      ];
}
export function chartCsv(chart: ReportChart): string {
  const quote = (v: unknown) => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  return [
    ['图表', chart.title],
    ['数据状态', chart.status === 'demo' ? 'Demo · 模拟数据' : '报告快照 · 未独立复核'],
    ['观察日期', chart.asOf],
    ['来源', reportSource.title + '；PDF第' + chart.page + '页'],
    ['口径', chart.basis],
    chartHeaders(chart),
    ...chartRows(chart),
  ]
    .map((row) => row.map(quote).join(','))
    .join('\r\n');
}
