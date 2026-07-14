import type { StrategyDeskKey, StrategyTableSection, StrategyTableTab } from '../types';

export interface StrategyOrderProfile {
  label: string;
  tabs: StrategyTableTab[];
  tables: Record<string, StrategyTableSection>;
}

export const strategyDeskOrder: StrategyDeskKey[] = [
  'funding',
  'crossSpread',
  'domesticOverseas',
  'dip',
  'shortLineTraderL',
  'shortLineTraderW',
];

const commonTabs: StrategyTableTab[] = [
  { key: 'positions', label: '当前持仓' },
  { key: 'history', label: '历史订单' },
  { key: 'fills', label: '成交记录' },
  { key: 'logs', label: '执行记录' },
];

const fundingTabs: StrategyTableTab[] = [
  { key: 'positions', label: '当前持仓' },
  { key: 'spotHistory', label: '历史订单-现货' },
  { key: 'contractHistory', label: '历史订单-合约' },
  { key: 'fills', label: '成交记录' },
  { key: 'logs', label: '执行记录' },
];

const twoLegTabs: StrategyTableTab[] = [
  { key: 'positions', label: '当前持仓' },
  { key: 'leftHistory', label: '历史订单-左腿' },
  { key: 'rightHistory', label: '历史订单-右腿' },
  { key: 'fills', label: '成交记录' },
  { key: 'logs', label: '执行记录' },
];

const fundingTables: Record<string, StrategyTableSection> = {
  positions: {
    columns: [
      { key: 'symbol', label: '标的' },
      { key: 'legType', label: '腿类型' },
      { key: 'platform', label: '平台' },
      { key: 'size', label: '持仓数量' },
      { key: 'entry', label: '入场价格' },
      { key: 'mark', label: '当前价格' },
      { key: 'funding', label: '累计资金费' },
      { key: 'status', label: '状态' },
    ],
    rows: [
      { symbol: 'BTCUSDT', legType: '现货实寸', platform: 'Binance', size: '0.5000 BTC', entry: '102,200.00', mark: '102,350.00', funding: '--', status: '正常' },
      { symbol: 'BTCUSDT 永续', legType: '合约实寸', platform: 'Binance', size: '0.5000 BTC', entry: '102,212.00', mark: '102,341.20', funding: '+285.40', status: '正常' },
      { symbol: 'ETHUSDT 永续', legType: '合约实寸', platform: 'OKX', size: '5.0000 ETH', entry: '3,405.00', mark: '3,398.00', funding: '+118.40', status: '正常' },
    ],
  },
  spotHistory: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'price', label: '价格' },
      { key: 'size', label: '数量' },
      { key: 'status', label: '订单状态' },
    ],
    rows: [
      { time: '2026-06-25 10:24:44', symbol: 'BTCUSDT', side: '买入', price: '102,200.00', size: '0.5000 BTC', status: '全部成交' },
      { time: '2026-06-24 15:18:09', symbol: 'ETHUSDT', side: '买入', price: '3,405.00', size: '5.0000 ETH', status: '全部成交' },
    ],
  },
  contractHistory: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'price', label: '价格' },
      { key: 'size', label: '数量' },
      { key: 'status', label: '订单状态' },
    ],
    rows: [
      { time: '2026-06-25 10:24:47', symbol: 'BTCUSDT 永续', side: '卖出', price: '102,212.00', size: '0.5000 BTC', status: '全部成交' },
      { time: '2026-06-24 15:18:14', symbol: 'ETHUSDT 永续', side: '卖出', price: '3,398.00', size: '5.0000 ETH', status: '部分成交' },
    ],
  },
  fills: {
    columns: [
      { key: 'orderId', label: '订单号' },
      { key: 'symbol', label: '标的' },
      { key: 'legType', label: '腿类型' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillSize', label: '成交量' },
      { key: 'fee', label: '手续费' },
      { key: 'time', label: '成交时间' },
    ],
    rows: [
      { orderId: 'FUND-8244', symbol: 'BTCUSDT', legType: '现货', fillPrice: '102,200.00', fillSize: '0.5000 BTC', fee: '12.40', time: '2026-06-25 10:24:44' },
      { orderId: 'FUND-8245', symbol: 'BTCUSDT 永续', legType: '合约', fillPrice: '102,212.00', fillSize: '0.5000 BTC', fee: '8.20', time: '2026-06-25 10:24:47' },
    ],
  },
  logs: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'type', label: '类型' },
      { key: 'content', label: '内容' },
      { key: 'status', label: '状态' },
    ],
    rows: [
      { time: '2026-06-25 10:31:08', type: '执行成功', content: 'BTC 资费套利双腿成交完成。', status: '处理完成' },
      { time: '2026-06-25 09:57:12', type: '执行提醒', content: 'ETH 合约腿部分成交，等待补齐。', status: '处理中' },
    ],
  },
};

function makeTwoLegTables(leftLabel: string, rightLabel: string): Record<string, StrategyTableSection> {
  return {
    positions: {
      columns: [
        { key: 'symbol', label: '标的' },
        { key: 'legType', label: '腿类型' },
        { key: 'platform', label: '平台' },
        { key: 'size', label: '持仓数量' },
        { key: 'entry', label: '入场价格' },
        { key: 'mark', label: '当前价格' },
        { key: 'pnl', label: '未结盈亏' },
        { key: 'status', label: '状态' },
      ],
      rows: [
        { symbol: 'XAU', legType: leftLabel, platform: 'Gate', size: '5.00', entry: '5,339.06', mark: '5,129.30', pnl: '+0.00', status: '正常' },
        { symbol: 'XAUUSD', legType: rightLabel, platform: 'Binance', size: '5.00', entry: '5,361.38', mark: '5,158.18', pnl: '+0.00', status: '正常' },
      ],
    },
    leftHistory: {
      columns: [
        { key: 'time', label: '时间' },
        { key: 'symbol', label: '标的' },
        { key: 'side', label: '方向' },
        { key: 'price', label: '价格' },
        { key: 'size', label: '数量' },
        { key: 'status', label: '订单状态' },
      ],
      rows: [
        { time: '2026-06-25 10:18:16', symbol: 'XAU', side: '买入', price: '5,129.30', size: '5.00', status: '全部成交' },
      ],
    },
    rightHistory: {
      columns: [
        { key: 'time', label: '时间' },
        { key: 'symbol', label: '标的' },
        { key: 'side', label: '方向' },
        { key: 'price', label: '价格' },
        { key: 'size', label: '数量' },
        { key: 'status', label: '订单状态' },
      ],
      rows: [
        { time: '2026-06-25 10:18:20', symbol: 'XAUUSD', side: '卖出', price: '5,158.18', size: '5.00', status: '全部成交' },
      ],
    },
    fills: {
      columns: [
        { key: 'orderId', label: '订单号' },
        { key: 'symbol', label: '标的' },
        { key: 'legType', label: '腿类型' },
        { key: 'fillPrice', label: '成交价' },
        { key: 'fillSize', label: '成交量' },
        { key: 'fee', label: '手续费' },
        { key: 'time', label: '成交时间' },
      ],
      rows: [
        { orderId: 'SPRD-1042', symbol: 'XAU', legType: leftLabel, fillPrice: '5,129.30', fillSize: '5.00', fee: '45.20', time: '2026-06-25 10:18:16' },
        { orderId: 'SPRD-1043', symbol: 'XAUUSD', legType: rightLabel, fillPrice: '5,158.18', fillSize: '5.00', fee: '11.08', time: '2026-06-25 10:18:20' },
      ],
    },
    logs: {
      columns: [
        { key: 'time', label: '时间' },
        { key: 'type', label: '类型' },
        { key: 'content', label: '内容' },
        { key: 'status', label: '状态' },
      ],
      rows: [
        { time: '2026-06-25 10:18:20', type: '双腿成交', content: `${leftLabel} 与 ${rightLabel} 执行完成。`, status: '处理完成' },
        { time: '2026-06-25 09:26:11', type: '人工确认', content: '价差偏离触发人工复核。', status: '处理完成' },
      ],
    },
  };
}

const dipTables: Record<string, StrategyTableSection> = {
  positions: {
    columns: [
      { key: 'symbol', label: '标的' },
      { key: 'size', label: '持仓数量' },
      { key: 'entry', label: '持仓均价' },
      { key: 'mark', label: '当前价格' },
      { key: 'pnl', label: '浮动盈亏' },
      { key: 'stop', label: '止盈/止损' },
      { key: 'status', label: '状态' },
    ],
    rows: [
      { symbol: 'BTC', size: '6.20', entry: '105,220', mark: '107,200', pnl: '+12,276', stop: '109,500 / 103,800', status: '正常' },
      { symbol: 'ETH', size: '92.00', entry: '3,182', mark: '3,398', pnl: '+19,872', stop: '3,620 / 3,050', status: '正常' },
    ],
  },
  history: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'price', label: '价格' },
      { key: 'size', label: '数量' },
      { key: 'status', label: '订单状态' },
    ],
    rows: [
      { time: '2026-06-25 11:02:18', symbol: 'BTC', side: '加仓', price: '106,280', size: '0.80', status: '全部成交' },
      { time: '2026-06-25 10:26:04', symbol: 'SOL', side: '止盈挂单', price: '107.80', size: '300', status: '已提交' },
    ],
  },
  fills: {
    columns: [
      { key: 'orderId', label: '订单号' },
      { key: 'symbol', label: '标的' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillSize', label: '成交量' },
      { key: 'fee', label: '手续费' },
      { key: 'time', label: '成交时间' },
    ],
    rows: [
      { orderId: 'DIP-2061', symbol: 'BTC', fillPrice: '106,280', fillSize: '0.80', fee: '8.10', time: '2026-06-25 11:02:18' },
    ],
  },
  logs: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'type', label: '类型' },
      { key: 'content', label: '内容' },
      { key: 'status', label: '状态' },
    ],
    rows: [
      { time: '2026-06-25 11:02:18', type: '执行成功', content: 'BTC 二次加仓成交完成。', status: '处理完成' },
    ],
  },
};

const shortLineTables: Record<string, StrategyTableSection> = {
  positions: {
    columns: [
      { key: 'symbol', label: '标的' },
      { key: 'category', label: '品类' },
      { key: 'direction', label: '方向' },
      { key: 'size', label: '持仓数量' },
      { key: 'entry', label: '入场价格' },
      { key: 'mark', label: '当前价格' },
      { key: 'pnl', label: '当日盈亏' },
      { key: 'status', label: '状态' },
    ],
    rows: [
      { symbol: 'IF2609', category: '股指期货', direction: '多', size: '2手', entry: '4,128.6', mark: '4,146.2', pnl: '+10,560', status: '正常' },
      { symbol: 'XAUUSD', category: '黄金', direction: '空', size: '1.20', entry: '2,418.4', mark: '2,412.1', pnl: '+7,560', status: '正常' },
      { symbol: 'BTCUSDT', category: '币', direction: '多', size: '0.80', entry: '104,820', mark: '105,420', pnl: '+3,840', status: '正常' },
    ],
  },
  history: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'symbol', label: '标的' },
      { key: 'side', label: '方向' },
      { key: 'price', label: '价格' },
      { key: 'size', label: '数量' },
      { key: 'status', label: '订单状态' },
    ],
    rows: [
      { time: '2026-06-25 10:48:12', symbol: 'IF2609', side: '开多', price: '4,128.6', size: '2手', status: '全部成交' },
      { time: '2026-06-25 10:12:33', symbol: 'XAUUSD', side: '开空', price: '2,418.4', size: '1.20', status: '全部成交' },
    ],
  },
  fills: {
    columns: [
      { key: 'orderId', label: '订单号' },
      { key: 'symbol', label: '标的' },
      { key: 'fillPrice', label: '成交价' },
      { key: 'fillSize', label: '成交量' },
      { key: 'fee', label: '手续费' },
      { key: 'time', label: '成交时间' },
    ],
    rows: [
      { orderId: 'L-9281', symbol: 'IF2609', fillPrice: '4,128.6', fillSize: '2手', fee: '36.00', time: '2026-06-25 10:48:12' },
      { orderId: 'L-9276', symbol: 'XAUUSD', fillPrice: '2,418.4', fillSize: '1.20', fee: '18.40', time: '2026-06-25 10:12:33' },
    ],
  },
  logs: {
    columns: [
      { key: 'time', label: '时间' },
      { key: 'type', label: '类型' },
      { key: 'content', label: '内容' },
      { key: 'status', label: '状态' },
    ],
    rows: [
      { time: '2026-06-25 13:12:33', type: '风控提醒', content: 'BTC 追单后波动放大，触发一次减仓提醒。', status: '处理完成' },
      { time: '2026-06-25 10:18:44', type: '人工复核', content: '黄金止盈单撤回，已发送人工复核消息。', status: '处理完成' },
    ],
  },
};

export const strategyOrderProfiles = {
  funding: {
    label: '资费',
    tabs: fundingTabs,
    tables: fundingTables,
  },
  spread: {
    label: '价差',
    tabs: twoLegTabs,
    tables: makeTwoLegTables('A腿', 'B腿'),
  },
  crossSpread: {
    label: '跨所价差',
    tabs: twoLegTabs,
    tables: makeTwoLegTables('交易所A腿', '交易所B腿'),
  },
  domesticOverseas: {
    label: '海内外价差',
    tabs: twoLegTabs,
    tables: makeTwoLegTables('国内腿', '海外腿'),
  },
  dip: {
    label: '抄底',
    tabs: commonTabs,
    tables: dipTables,
  },
  shortLineTraderL: {
    label: '短线交易员L',
    tabs: commonTabs,
    tables: shortLineTables,
  },
} as Record<StrategyDeskKey, StrategyOrderProfile>;

strategyOrderProfiles.shortLineTraderW = {
  label: '短线交易员W',
  tabs: commonTabs,
  tables: shortLineTables,
};
