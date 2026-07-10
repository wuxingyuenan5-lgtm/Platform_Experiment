import type { SpreadExecutionConfig, SpreadWorkspaceVariant } from '../types';

export const spreadExecutionConfigs: Record<SpreadWorkspaceVariant, SpreadExecutionConfig> = {
  crossVenue: {
    variant: 'crossVenue',
    deskLabel: '跨所价差',
    eyebrow: 'CROSS EXCHANGE TERMINAL',
    title: '黄金跨所价差交易终端',
    pairLabel: 'XAUTUSDT.P - XAUUSD',
    sceneLabel: '交易场景',
    sceneValue: '数字黄金对冲现货黄金',
    defaultVenue: 'Bybit',
    strategyOptions: [
      { label: '黄金跨所价差 / XAUT_SPREAD', value: 'xaut-spread' },
      { label: '黄金跨所移仓 / XAUT_ROLLOVER', value: 'xaut-rollover' },
    ],
    actionPresets: [
      { key: 'open', label: '开仓' },
      { key: 'rollover', label: '移仓' },
    ],
    actionButtons: [
      { key: 'openLong', label: '开多价差', tone: 'primary' },
      { key: 'openShort', label: '开空价差', tone: 'default' },
      { key: 'close', label: '平仓价差', tone: 'default' },
    ],
    metricCards: [
      { label: '可用资金率', value: '92.69% -> 92.44%', tone: 'positive' },
      { label: '整体杠杆', value: '1.49X -> 1.56X', tone: 'neutral' },
      { label: '预估滑点', value: '0.18%', tone: 'negative' },
      { label: 'USDT/USD Basis', value: '-0.02%', tone: 'negative' },
    ],
    leftLegTitle: '主腿 / 永续合约',
    rightLegTitle: '对冲腿 / 现货黄金',
    leftLegMetrics: [
      { label: '标的', value: 'XAUTUSDT.P' },
      { label: '方向', value: '空', tone: 'negative' },
      { label: '最新价', value: '2,353.60' },
      { label: '触发阈值', value: '>= 17.50', tone: 'positive' },
      { label: '可成交价差', value: '18.70', tone: 'positive' },
      { label: '延迟', value: '18 ms', tone: 'positive' },
    ],
    rightLegMetrics: [
      { label: '标的', value: 'XAUUSD' },
      { label: '方向', value: '多', tone: 'positive' },
      { label: '最新价', value: '2,334.90' },
      { label: '对冲比', value: '1 : 0.992' },
      { label: '可成交价差', value: '18.10', tone: 'positive' },
      { label: '延迟', value: '22 ms', tone: 'positive' },
    ],
    exposureMetrics: [
      { label: '建议方向', value: '空主腿 / 多现货', tone: 'positive' },
      { label: '当前价差', value: '18.70', tone: 'positive' },
      { label: '预设止盈', value: '12.20', tone: 'neutral' },
      { label: '预设止损', value: '23.80', tone: 'negative' },
    ],
    logs: [
      { time: '10:16:28', text: '主腿报价更新完成，滑点估算已重算。', tone: 'neutral' },
      { time: '10:12:10', text: 'USDT 偏离保持轻微折价，仍可执行。', tone: 'positive' },
      { time: '10:08:41', text: '对冲腿深度回升，价差触达观察区间。', tone: 'positive' },
    ],
    tabs: [
      { key: 'positions', label: '当前持仓' },
      { key: 'orders', label: '历史订单' },
      { key: 'fills', label: '成交记录' },
      { key: 'logs', label: '执行记录' },
    ],
    tables: {
      positions: {
        columns: [
          { key: 'symbol', label: '标的' },
          { key: 'direction', label: '方向' },
          { key: 'size', label: '数量' },
          { key: 'entry', label: '开仓价差' },
          { key: 'mark', label: '当前价差' },
          { key: 'pnl', label: '未实现盈亏' },
        ],
        rows: [
          { symbol: 'XAUTUSDT.P / XAUUSD', direction: '空 / 多', size: '100 盎司', entry: '17.86', mark: '18.70', pnl: '+84.00' },
        ],
      },
      orders: {
        columns: [
          { key: 'time', label: '时间' },
          { key: 'action', label: '动作' },
          { key: 'spread', label: '触发价差' },
          { key: 'status', label: '状态' },
        ],
        rows: [
          { time: '10:16:12', action: '开空价差', spread: '18.70', status: '待确认' },
          { time: '09:58:42', action: '止盈保护', spread: '12.20', status: '监控中' },
        ],
      },
      fills: {
        columns: [
          { key: 'orderId', label: '订单号' },
          { key: 'leg', label: '腿别' },
          { key: 'price', label: '成交价' },
          { key: 'size', label: '成交量' },
          { key: 'time', label: '时间' },
        ],
        rows: [
          { orderId: 'XAUT-1042', leg: '主腿', price: '2,353.60', size: '100', time: '09:42:10' },
          { orderId: 'XAU-1042', leg: '对冲腿', price: '2,334.90', size: '99.20', time: '09:42:11' },
        ],
      },
      logs: {
        columns: [
          { key: 'time', label: '时间' },
          { key: 'type', label: '类别' },
          { key: 'content', label: '内容' },
        ],
        rows: [
          { time: '10:16:28', type: '监控', content: '重新计算可成交价差与保护阈值。' },
          { time: '10:08:41', type: '机会', content: '价差回到开仓观察区间。' },
        ],
      },
    },
  },
  domesticOverseas: {
    variant: 'domesticOverseas',
    deskLabel: '海内外价差',
    eyebrow: 'DOMESTIC VS OFFSHORE',
    title: '海内外黄金价差执行平台',
    pairLabel: 'SHFE.au2606 - XAUUSD',
    sceneLabel: '交易场景',
    sceneValue: '沪金对冲伦敦金',
    defaultVenue: 'SHFE',
    strategyOptions: [
      { label: '沪金伦敦金多空 / SHFE_XAU', value: 'shfe-xau' },
      { label: '海内外移仓 / SHFE_ROLLOVER', value: 'shfe-rollover' },
    ],
    actionPresets: [
      { key: 'open', label: '开仓' },
      { key: 'rollover', label: '移仓' },
    ],
    actionButtons: [
      { key: 'strategyOpen', label: '策略开仓', tone: 'primary' },
      { key: 'strategyClose', label: '策略平仓', tone: 'default' },
      { key: 'takeProfit', label: '止盈保护', tone: 'default' },
    ],
    metricCards: [
      { label: '可用资金率', value: '92.69% -> 92.59%', tone: 'positive' },
      { label: '整体杠杆', value: '1.4971 -> 1.5171', tone: 'neutral' },
      { label: '预付款比例', value: '0.0000% -> 0.0020%', tone: 'negative' },
      { label: '当前价差', value: '0.1115% / 1.18 CNY', tone: 'positive' },
    ],
    leftLegTitle: '国内腿 / 沪金',
    rightLegTitle: '海外腿 / 伦敦金',
    leftLegMetrics: [
      { label: '标的', value: 'SHFE.au2606' },
      { label: '方向', value: '多', tone: 'positive' },
      { label: '最新价', value: '1,058.50' },
      { label: '可开手数', value: '约 62 手', tone: 'neutral' },
      { label: '盎司换算', value: '100 盎司 / 手', tone: 'neutral' },
      { label: '可用余额', value: '10,485,527 CNY', tone: 'positive' },
    ],
    rightLegMetrics: [
      { label: '标的', value: 'XAUUSD' },
      { label: '方向', value: '空', tone: 'negative' },
      { label: '最新价', value: '4,820.01' },
      { label: '自动配平', value: '0.64 手' },
      { label: '汇率', value: '6.82' },
      { label: '价差', value: '0.1115%', tone: 'positive' },
    ],
    exposureMetrics: [
      { label: '建议动作', value: '国内多 / 海外空', tone: 'positive' },
      { label: '执行模式', value: '克数配平', tone: 'neutral' },
      { label: '预估冲击', value: '轻微', tone: 'neutral' },
      { label: '风险提示', value: '关注汇率腿偏移', tone: 'negative' },
    ],
    logs: [
      { time: '10:21:56', text: '沪金估值与伦敦金价差重新计算完成。', tone: 'neutral' },
      { time: '10:18:33', text: '配平手数更新为 0.64，确认执行按钮已可用。', tone: 'positive' },
      { time: '10:14:09', text: '汇率腿轻微波动，尚未突破预警阈值。', tone: 'negative' },
    ],
    tabs: [
      { key: 'positions', label: '当前持仓' },
      { key: 'orders', label: '历史订单' },
      { key: 'fills', label: '成交记录' },
      { key: 'logs', label: '执行记录' },
    ],
    tables: {
      positions: {
        columns: [
          { key: 'symbol', label: '标的' },
          { key: 'direction', label: '方向' },
          { key: 'size', label: '数量' },
          { key: 'entry', label: '持仓价差' },
          { key: 'mark', label: '当前价差' },
          { key: 'pnl', label: '未实现盈亏' },
        ],
        rows: [
          { symbol: 'SHFE.au2606 / XAUUSD', direction: '多 / 空', size: '2.00 手 / 0.64 手', entry: '1.06 CNY', mark: '1.18 CNY', pnl: '+3,870 CNY' },
        ],
      },
      orders: {
        columns: [
          { key: 'time', label: '时间' },
          { key: 'action', label: '动作' },
          { key: 'spread', label: '价差' },
          { key: 'status', label: '状态' },
        ],
        rows: [
          { time: '10:18:30', action: '策略开仓', spread: '1.18 CNY', status: '待确认' },
          { time: '09:52:15', action: '策略平仓', spread: '0.82 CNY', status: '监控中' },
        ],
      },
      fills: {
        columns: [
          { key: 'orderId', label: '订单号' },
          { key: 'leg', label: '腿别' },
          { key: 'price', label: '成交价' },
          { key: 'size', label: '成交量' },
          { key: 'time', label: '时间' },
        ],
        rows: [
          { orderId: 'SHFE-2606', leg: '国内腿', price: '1,058.50', size: '2.00', time: '09:35:21' },
          { orderId: 'XAU-2606', leg: '海外腿', price: '4,820.01', size: '0.64', time: '09:35:22' },
        ],
      },
      logs: {
        columns: [
          { key: 'time', label: '时间' },
          { key: 'type', label: '类别' },
          { key: 'content', label: '内容' },
        ],
        rows: [
          { time: '10:21:56', type: '刷新', content: '价差、汇率、配平手数已同步。' },
          { time: '10:14:09', type: '预警', content: '汇率腿偏移接近预警阈值。' },
        ],
      },
    },
  },
};
