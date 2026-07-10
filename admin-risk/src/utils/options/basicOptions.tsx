import { useI18n } from '@/hooks/web/useI18n';

const { t } = useI18n();

// 快速将数组转换为 LabelValueOptions 格式
export function toLabelValueOptions(arr: any[], params): LabelValueOptions {
  const { label = 'label', value = 'value' } = params;
  return arr.map((item) => ({ ...item, label: item[label], value: item[value] }));
}
/*----------------------------------- 风控 begin ----------------------------------------- */
// 指标代码
export const metricCodeOptions: LabelValueOptions = [
  {
    label: '产品净值',
    value: 'equity',
  },
  {
    label: '期货净值',
    value: 'futureEquity',
  },
  {
    label: 'MT5净值',
    value: 'MT5Equity',
  },
  {
    label: '期货交易时间段回撤',
    value: 'SHFEdrawdown',
  },
  {
    label: '中性平衡',
    value: 'prodNeutralBalance',
  },
  {
    label: '总杠杆率',
    value: 'prodTotalLeverageRatio',
  },
  {
    label: '期货杠杆率',
    value: 'futureLeverageRatio',
  },
  {
    label: 'MT5杠杆率',
    value: 'MT5LeverageRatio',
  },
  {
    label: 'IMR',
    value: 'IMR',
  },
  {
    label: 'MMR',
    value: 'MMR',
  },
  {
    label: '预付款维持率',
    value: 'marginLevel',
  },
  {
    label: '资金使用率',
    value: 'RiskRatio',
  },
];
// 数据类型
export const dataTypeOptions: LabelValueOptions = [
  {
    label: '因子数据',
    value: 'factor',
  },
  {
    label: '净值数据',
    value: 'nav',
  },
  {
    label: '其他数据',
    value: 'other',
  },
];
// 净值曲线-净值类型
export const netValueTypeOptions: LabelValueOptions = [
  {
    label: '实时汇率',
    value: 0,
  },
  {
    label: '固定汇率',
    value: 1,
  },
];
// tradingTimeFilter
export const tradingTimeFilterOptions: LabelValueOptions = [
  {
    label: '产品净值',
    value: 1,
  },
  {
    label: '原始净值',
    value: 0,
  },
];
// 计算器-标的品种
export const targetOptions: LabelValueOptions = [
  {
    label: '金',
    value: 'AU',
  },
  {
    label: '银',
    value: 'AG',
  },
  {
    label: '铜',
    value: 'CU',
  },
];
// 计算器-标的方向
export const directionOptions: LabelValueOptions = [
  {
    label: '期货',
    value: 'futures_to_mt5',
  },
  {
    label: 'MT5',
    value: 'mt5_to_futures',
  },
];
// 净值曲线时间筛选
export const timeOptions3: LabelValueOptions = [
  {
    label: '分钟',
    value: 'M',
  },
  {
    label: '天',
    value: 'D',
  },
];
// 币种单位
export const unitOptions: LabelValueOptions = [
  {
    label: 'USD',
    value: 'USD',
  },
  {
    label: 'CNY',
    value: 'CNY',
  },
];
// 平仓类型
export const closeTypeOptions: LabelValueOptions = [
  {
    label: '单边平仓',
    value: 'single_side',
  },
  {
    label: '双边平仓',
    value: 'double_side',
  },
];
// 站内通知类型
export const noticeTypeOptions: LabelValueOptions = [
  {
    label: '警报提醒',
    value: 'alert',
  },
  {
    label: '系统通知',
    value: 'system',
  },
  {
    label: '调拨提醒',
    value: 'transfer',
  },
  {
    label: '其他',
    value: 'other',
  },
];
// 风险处理状态
export const riskStatusOptions: LabelValueOptions = [
  {
    label: '待处理',
    value: false,
    color: '#FAAD14FF',
  },
  {
    label: '已处理',
    value: true,
    color: '#2FB97BFF',
  },
];
// 平仓日志状态
export const closeLogStatusOptions: LabelValueOptions = [
  {
    label: '待执行',
    value: 'pending',
    color: '#FAAD14FF',
  },
  {
    label: '执行中',
    value: 'running',
    color: '#FAAD14FF',
  },
  {
    label: '已完成',
    value: 'completed',
    color: '#2FB97BFF',
  },
  {
    label: '执行失败',
    value: 'failed',
    color: '#FF4D4FFF',
  },
  {
    label: '已取消',
    value: 'cancelled',
    color: '#EB6E2CFF',
  },
  {
    label: '执行超时',
    value: 'timeout',
    color: '#FF4D4FFF',
  },
];
// 链接情况
export const linkStatusOptions: LabelValueOptions = [
  {
    label: '已连接',
    value: false,
    color: '#2FB97BFF',
  },
  {
    label: '已断开',
    value: true,
    color: '#FF4D4FFF',
  },
];
// 转账类型
export const transferTypeOptions: LabelValueOptions = [
  {
    label: '账号间转账',
    value: 'interTransfer',
  },
  {
    label: '账号内转账',
    value: 'intraTransfer',
  },
];

// 调拨风险等级
export const riskLevelOptions2: LabelValueOptions = [
  {
    label: '低风险',
    value: 'low',
    color: '#22B573',
  },
  {
    label: '中风险',
    value: 'medium',
    color: '#FAAD14FF',
  },
  {
    label: '高风险',
    value: 'high',
    color: '#C1272D',
  },
];
// 调拨审核状态
export const auditStatusOptions: LabelValueOptions = [
  {
    label: '待处理',
    value: 'pending',
    color: '#FAAD14FF',
  },
  {
    label: '已批准',
    value: 'approved',
    color: '#2FB97BFF',
  },
  {
    label: '已拒绝',
    value: 'rejected',
    color: '#EB6E2CFF',
  },
  {
    label: '已完成',
    value: 'completed',
    color: '#2FB97BFF',
  },
  {
    label: '失败',
    value: 'failed',
    color: '#FF4D4FFF',
  },
  {
    label: '错误',
    value: 'error',
    color: '#FF4D4FFF',
  },
];
// 持仓方向
export const positionSideOptions: LabelValueOptions = [
  {
    label: '买入',
    value: 'Buy',
    color: '#22B573',
  },
  {
    label: '卖出',
    value: 'Sell',
    color: '#C1272D',
  },
];

// 服务器连接状态
export const serverStatusOptions: LabelValueOptions = [
  {
    label: '健康',
    value: 'healthy',
    color: '#2FB97BFF',
  },
  {
    label: '不健康',
    value: 'unhealthy',
    color: '#FF4D4FFF',
  },
  {
    label: '错误',
    value: 'error',
    color: '#FF4D4FFF',
  },
];

// 风险等级
export const riskLevelOptions: LabelValueOptions = [
  {
    label: '一级风险',
    value: 'level1',
    color: '#2FB97BFF',
    grade: '一级',
  },
  {
    label: '二级风险',
    value: 'level2',
    color: '#2C97EBFF',
    grade: '二级',
  },
  {
    label: '三级风险',
    value: 'level3',
    color: '#FAAD14FF',
    grade: '三级',
  },
  {
    label: '四级风险',
    value: 'level4',
    color: '#EB6E2CFF',
    grade: '四级',
  },
  {
    label: '五级风险',
    value: 'level5',
    color: '#FF4D4FFF',
    grade: '五级',
  },
];

/*------------------------------------ 风控 end ------------------------------------ */
// 交易平台
export const platformOptions: LabelValueOptions = [
  {
    label: t('common.platform.future'),
    value: 'futures',
  },
  {
    label: t('common.platform.mt5'),
    value: 'MT5',
  },
  {
    label: t('common.platform.crypto'),
    value: 'crypto',
  },
];
// 进出场
export const inOutOptions: LabelValueOptions = [
  {
    label: '进场',
    value: '0',
  },
  {
    label: '出场',
    value: '1',
  },
  {
    label: '反转',
    value: '2',
  },
  {
    label: '减仓',
    value: '3',
  },
];
// 折现图时间筛选
export const timeOptions2: LabelValueOptions = [
  {
    label: '1分钟',
    value: '1m',
  },
  {
    label: '5',
    value: '5m',
  },
  {
    label: '15',
    value: '15m',
  },
  {
    label: '30',
    value: '30m',
  },
  {
    label: '60',
    value: '60m',
  },
  {
    label: '日线',
    value: '24h',
  },
  // {
  //   label: '周线',
  //   value: '5m',
  // },
  // {
  //   label: '月线',
  //   value: '5m',
  // },
];
// mt5订单类型
export const orderTypeMt5Options: LabelValueOptions = [
  {
    label: '市价买',
    value: '0',
    // color: '#52C41A',
  },
  {
    label: '市价卖',
    value: '1',
    // color: '#FF4D4F',
  },
  {
    label: '限价买',
    value: '2',
  },
  {
    label: '限价卖',
    value: '3',
  },
  {
    label: '触发条件市价买',
    value: '4',
  },
  {
    label: '触发条件市价卖',
    value: '5',
  },
  {
    label: '触发条件限价买',
    value: '6',
  },
  {
    label: '触发条件限价卖',
    value: '7',
  },
  {
    label: '平仓',
    value: '8',
  },
];
// 交易方式类型
export const transactionMethodOptions: LabelValueOptions = [
  {
    label: '手动',
    value: 1,
  },
  {
    label: '自动策略',
    value: 2,
  },
];
// 时间范围筛选
export const timeRangeOptions: LabelValueOptions = [
  {
    label: '近7天',
    value: '7',
  },
  {
    label: '近30天',
    value: '30',
  },
  {
    label: '近180天',
    value: '180',
  },
];
// 策略执行方式
export const strategyExecuteTypeOptions: LabelValueOptions = [
  {
    label: '手动',
    value: 0,
  },
  {
    label: '自动',
    value: 1,
  },
];
// 策略指令执行状态
export const strategyStatusOptions: LabelValueOptions = [
  {
    label: '待执行',
    value: 0,
  },
  {
    label: '执行中',
    value: 1,
  },
  {
    label: '已完成',
    value: 2,
    color: '#52C41A',
  },
  {
    label: '已取消',
    value: 3,
    color: '#FAAD14',
  },
  {
    label: '执行失败',
    value: 4,
    color: '#FF4D4F',
  },
];
// 日志状态
export const logStatusOptions: LabelValueOptions = [
  {
    label: '成功',
    value: 1,
    color: '#52C41A',
  },
  {
    label: '失败',
    value: 0,
    color: '#FF4D4F',
  },
];
// 开平仓状
export const openCloseOptions: LabelValueOptions = [
  {
    label: '开仓',
    value: 'OPEN',
  },
  {
    label: '平仓',
    value: 'CLOSE',
  },
  {
    label: '平昨仓',
    value: 'CLOSEYESTERDAY',
  },
  {
    label: '平今仓',
    value: 'CLOSETODAY',
  },
];
// 项目类型
export const projectOptions: LabelValueOptions = [
  {
    label: '返佣宝',
    value: 'fyb',
  },
  {
    label: '基金',
    value: 'fund',
  },
  {
    label: '定投宝',
    value: 'dtb',
  },
  {
    label: '对冲基金',
    value: 'hedgeFund',
  },
];
// 多空方向
export const bullishDirOptions: LabelValueOptions = [
  {
    label: '仅正向',
    value: '1',
  },
  {
    label: '仅反向',
    value: '2',
  },
  {
    label: '双向',
    value: '3',
  },
];

// 策略所属类型
export enum strategyType {
  pricedif = 'diff',
  funding = 'funding',
  bltp = 'bltp',
  sjx = 'sjx',
}
// 策略操作类型
export const strategyOperateTypeOptions: LabelValueOptions = [
  {
    label: '执行',
    value: 'restart',
  },
  {
    label: '编辑',
    value: 'update',
  },
  {
    label: '停止',
    value: 'stop',
  },
  {
    label: '新增',
    value: 'add',
  },
];
// 策略所属类型(树结构)
export const strategyTypeOptions: LabelValueOptions = [
  {
    label: '套利',
    value: 'arbitrage',
    children: [
      {
        label: '期现价差套利',
        value: strategyType.pricedif,
      },
      {
        label: '资金费率套利',
        value: strategyType.funding,
      },
    ],
  },
  {
    label: 'CTA',
    value: 'CTA',
    disabled: true,
    children: [
      {
        label: '布林突破',
        value: strategyType.bltp,
      },
      {
        label: '双均线',
        value: strategyType.sjx,
      },
    ],
  },
  {
    label: '主观',
    value: '3',
    disabled: true,
  },
];

export const strategyTypeOptionsArbitrage: LabelValueOptions = [
  {
    label: '期现价差套利',
    value: strategyType.pricedif,
  },
  {
    label: '资金费率套利',
    value: strategyType.funding,
  },
];

// 累计费率
export const cumulativeFeeRateOptions: LabelValueOptions = [
  {
    label: '当前',
    value: 'current',
  },
  {
    label: '1日费率累计',
    value: 'day',
  },
  {
    label: '7日费率累计',
    value: 'week',
  },
  {
    label: '30日费率累计',
    value: 'month',
  },
  {
    label: '1年费率累计',
    value: 'year',
  },
];

export const cumulativeFeeRateOptions2: LabelValueOptions = [
  {
    label: '当前',
    value: 'current',
  },
  {
    label: '7日费率累计',
    value: 'week',
  },
  {
    label: '30日费率累计',
    value: 'month',
  },
  {
    label: '1年费率累计',
    value: 'year',
  },
];

// 累计费率(借贷利率)
export const cumulativeBorrowRateOptions: LabelValueOptions = [
  {
    label: '当前',
    value: 'current',
  },
  {
    label: '日利率累计',
    value: 'day',
  },
  {
    label: '年利率累计',
    value: 'year',
  },
];

// 交易所
export const exchangeOptions: LabelValueOptions = [
  {
    label: 'Bybit',
    value: 'bybit',
  },
  {
    label: 'Okx',
    value: 'okx',
  },
  {
    label: 'Binance',
    value: 'binance',
  },
];
export const exchangeTransferOptions: LabelValueOptions = [
  {
    label: 'Bybit',
    value: '1',
  },
  {
    label: 'Okx',
    value: '2',
  },
];
// 时间颗粒度
export const timeOptions: LabelValueOptions = [
  {
    label: '天',
    value: 'day',
  },
  {
    label: '月',
    value: 'month',
  },
  {
    label: '季度',
    value: 'quarter',
  },
  {
    label: '半年',
    value: 'helfYear',
  },
  {
    label: '年',
    value: 'year',
  },
  {
    label: '全部',
    value: 'all',
  },
];

// 时间颗粒度2
export const time2Options: LabelValueOptions = [
  {
    label: '时',
    value: 'hour',
  },
  {
    label: '天',
    value: 'day',
  },
  {
    label: '周',
    value: 'week',
  },
  {
    label: '月',
    value: 'month',
  },
];
// 时间颗粒度3
export const time3Options: LabelValueOptions = [
  {
    label: '时',
    value: 'hour',
  },
  {
    label: '天',
    value: 'day',
  },
];
// 仓位情况
export const positionOptions: LabelValueOptions = [
  {
    label: '全仓',
    value: 'full',
  },
  {
    label: '逐仓',
    value: 'warehouse',
  },
];

// 交易币种
export const tradeCurrencyOptions: LabelValueOptions = [
  {
    label: 'BTC',
    value: 'BTC',
  },
  {
    label: 'USDT',
    value: 'USDT',
  },
];
export const tradeCurrencyOptions2: LabelValueOptions = [
  {
    label: 'USDT',
    value: 'USDT',
  },
  {
    label: 'BTC',
    value: 'BTC',
  },
  {
    label: 'ETH',
    value: 'ETH',
  },
  {
    label: 'SOL',
    value: 'SOL',
  },
];
// 价单类型
export const orderTypeOptions: LabelValueOptions = [
  {
    label: '限价单',
    value: 'Limit',
  },
  {
    label: '市价单',
    value: 'Market',
  },
];
export const orderTypeOptions2: LabelValueOptions = [
  {
    label: '限价单',
    value: '1',
  },
  {
    label: '市价单',
    value: '0',
  },
];

// 加密-订单类型
export const orderTypeOptions3: LabelValueOptions = [
  // {
  //   label: '条件单',
  //   value: '1',
  // },
  {
    label: '追逐限价单',
    value: 'follow',
  },
  {
    label: '冰山委托单',
    value: 'ice',
  },
  {
    label: '百分比限价单',
    value: 'percentage',
  },
];
// 期货-订单类型
export const orderTypeOptions4: LabelValueOptions = [
  {
    label: '限价单',
    value: 'Limit',
  },
  {
    label: '追逐限价单',
    value: 'follow',
  },
  {
    label: '冰山委托单',
    value: 'ice',
  },
  {
    label: '百分比限价单',
    value: 'percentage',
  },
];

// 订单成交类型
export const orderDealTypeOptions: LabelValueOptions = [
  // {
  //   label: 'FOK（全数执行或立即取消）',
  //   value: '0',
  // },
  {
    label: 'IOC（立即执行或取消）',
    value: '1',
  },
  {
    label: 'RETURN（部分成交，剩余不取消）',
    value: '2',
  },
  // {
  //   label: 'BOC（全部成功挂单或取消）',
  //   value: '3',
  // },
];
// 订单到期类型
export const orderExpireTypeOptions: LabelValueOptions = [
  {
    label: 'GTC（持续直到取消订单）',
    value: '0',
  },
  {
    label: 'specified（持续直到指定时间）',
    value: '2',
  },
];
// 标的类型
export const categoryTypeOptions: LabelValueOptions = [
  {
    label: '现货',
    value: 'spot',
    color: '#2c97ebff',
  },
  {
    label: '期货',
    value: 'linear',
    color: '#eb6e2cff',
  },
  {
    label: '期货',
    value: 'futures',
    color: '#eb6e2cff',
  },
  {
    label: '期货',
    value: 'mt5_cfd',
    color: '#eb6e2cff',
  },
];

// 订单状态
export const orderStatusOptions: LabelValueOptions = [
  {
    label: '完全成交',
    value: 'Filled',
    color: '#52C41A',
  },
  {
    label: '取消',
    value: 'Cancelled',
    color: '#FF4D4F',
  },
  {
    label: '部分成交',
    value: 'PartiallyFilledCanceled',
    color: '#32EFD1',
  },
  {
    label: '拒绝',
    value: 'Rejected',
    color: '#FF4D4F',
  },
  {
    label: '已触发',
    value: 'Triggered',
    color: '#32EFD1',
  },
  {
    label: '触发前取消',
    value: 'Deactivated',
    color: '#32EFD1',
  },
];

// 订单状态
export const orderStatusOptions2: LabelValueOptions = [
  {
    label: '未开始',
    value: 0,
  },
  {
    label: '进行中',
    value: 1,
  },
  {
    label: '已完成',
    value: 2,
  },
  {
    label: '已超时',
    value: 3,
  },
  {
    label: '参数错误',
    value: 4,
  },
  {
    label: '交易所错误',
    value: 5,
  },
  {
    label: '手动停止',
    value: 6,
  },
];
// 订单状态
export const orderStatusOptions3: LabelValueOptions = [
  {
    label: '待成交',
    value: 'New',
  },
  {
    label: '部分成交',
    value: 'PartiallyFilled',
  },
];

// 订单状态
export const orderStatusOptions4: LabelValueOptions = [
  {
    label: '部分成交',
    value: 'Alive',
  },
  {
    label: '完全成交',
    value: 'Finished',
  },
  {
    label: '已撤单',
    value: 'Cancel',
  },
  {
    label: '挂单中',
    value: 'Registration',
  },
  {
    label: '错单',
    value: 'Error',
  },
  {
    label: '未知',
    value: 'Unknown',
  },
];
// 期货-订单状态
export const orderStatusOptions5: LabelValueOptions = [
  {
    label: '未开始',
    value: '0',
  },
  {
    label: '进行中',
    value: '1',
  },
  {
    label: '已完成',
    value: '2',
  },
  {
    label: '已超时',
    value: '3',
  },
  {
    label: '参数错误',
    value: '4',
  },
  {
    label: '交易所错误',
    value: '5',
  },
  {
    label: '手动停止',
    value: '6',
  },
];

// 持仓方向
export const positionSideOptions2: LabelValueOptions = [
  {
    label: '买入',
    value: 'BUY',
    color: '#22B573',
  },
  {
    label: '卖出',
    value: 'SELL',
    color: '#C1272D',
  },
];
export const positionSideOptions3: LabelValueOptions = [
  {
    label: '买入',
    value: '0',
    color: '#22B573',
  },
  {
    label: '卖出',
    value: '1',
    color: '#C1272D',
  },
];

// 成交类别
export const execTypeOptions: LabelValueOptions = [
  {
    label: '交易',
    value: 'Trade',
  },
  {
    label: '资金费率',
    value: 'Funding',
  },
  {
    label: '强制平仓',
    value: 'BustTrade',
  },
];

// 是否
export const yesNoOptions: LabelValueOptions = [
  {
    label: '是',
    value: true,
    color: '#22B573',
  },
  {
    label: '否',
    value: false,
    color: '#C1272D',
  },
];
export const yesNoOptions2: LabelValueOptions = [
  {
    label: '是',
    value: true,
    color: '#C1272D',
  },
  {
    label: '否',
    value: false,
    color: '#22B573',
  },
];

// 交易类型
export const tradeTypeOptions: LabelValueOptions = [
  {
    label: '更快成交',
    value: 'mq',
  },
  {
    label: '价格更优',
    value: 'mp',
  },
  {
    label: '固定价格',
    value: 're',
  },
];
export const tradeTypeOptions2: LabelValueOptions = [
  {
    label: '买入',
    value: '0',
    color: '#22B573',
  },
  {
    label: '卖出',
    value: '1',
    color: '#C1272D',
  },
];

// 调试账户类型
export const debugAccountTypeOptions: LabelValueOptions = [
  {
    label: 'Fund',
    value: 'FUND',
  },
  // {
  //   label: 'Trade',
  //   value: 'Trade',
  // },
];

export const debugAccountTypeOptions2: LabelValueOptions = [
  {
    label: 'Fund',
    value: 'FUND',
  },
  {
    label: 'Unified',
    value: 'UNIFIED',
  },
];

// 划转状态
export const transferStatusOptions: LabelValueOptions = [
  {
    label: '待划转',
    value: 0,
  },
  {
    label: '进行中',
    value: 1,
  },
  {
    label: '划转成功',
    value: 2,
    color: '#52C41A',
  },
  {
    label: '划转失败',
    value: 3,
    color: '#FF4D4F',
  },
];

// 订单执行策略
export const orderExecStrategyOptions: LabelValueOptions = [
  {
    label: 'FOK',
    value: 'FOK',
  },
  {
    label: 'IOC',
    value: 'IOC',
  },
  {
    label: 'GTC',
    value: 'GTC',
  },
];

// 交易日志类型
export const tradeType2Options: LabelValueOptions = [
  {
    label: 'TRANSFER_IN',
    value: 'TRANSFER_IN',
  },
  {
    label: 'TRANSFER_OUT',
    value: 'TRANSFER_OUT',
  },
  {
    label: 'TRADE',
    value: 'TRADE',
  },
  {
    label: 'SETTLEMENT',
    value: 'SETTLEMENT',
  },
  {
    label: 'DELIVERY',
    value: 'DELIVERY',
  },
  {
    label: 'LIQUIDATION',
    value: 'LIQUIDATION',
  },
  {
    label: 'ADL',
    value: 'ADL',
  },
  {
    label: 'AIRDROP',
    value: 'AIRDROP',
  },
  {
    label: 'BONUS',
    value: 'BONUS',
  },
  {
    label: 'BONUS_RECOLLECT',
    value: 'BONUS_RECOLLECT',
  },
  {
    label: 'FEE_REFUND',
    value: 'FEE_REFUND',
  },
  {
    label: 'INTEREST',
    value: 'INTEREST',
  },
  {
    label: 'CURRENCY_BUY',
    value: 'CURRENCY_BUY',
  },
  {
    label: 'CURRENCY_SELL',
    value: 'CURRENCY_SELL',
  },
  {
    label: 'BORROWED_AMOUNT_INS_LOAN',
    value: 'BORROWED_AMOUNT_INS_LOAN',
  },
  {
    label: 'PRINCIPLE_REPAYMENT_INS_LOAN',
    value: 'PRINCIPLE_REPAYMENT_INS_LOAN',
  },
  {
    label: 'INTEREST_REPAYMENT_INS_LOAN',
    value: 'INTEREST_REPAYMENT_INS_LOAN',
  },
  {
    label: 'AUTO_SOLD_COLLATERAL_INS_LOAN',
    value: 'AUTO_SOLD_COLLATERAL_INS_LOAN',
  },
  {
    label: 'AUTO_BUY_LIABILITY_INS_LOAN',
    value: 'AUTO_BUY_LIABILITY_INS_LOAN',
  },
  {
    label: 'AUTO_PRINCIPLE_REPAYMENT_INS_LOAN',
    value: 'AUTO_PRINCIPLE_REPAYMENT_INS_LOAN',
  },
  {
    label: 'AUTO_INTEREST_REPAYMENT_INS_LOAN',
    value: 'AUTO_INTEREST_REPAYMENT_INS_LOAN',
  },
  {
    label: 'TRANSFER_IN_INS_LOAN',
    value: 'TRANSFER_IN_INS_LOAN',
  },
  {
    label: 'TRANSFER_OUT_INS_LOAN',
    value: 'TRANSFER_OUT_INS_LOAN',
  },
  {
    label: 'SPOT_REPAYMENT_SELL',
    value: 'SPOT_REPAYMENT_SELL',
  },
  {
    label: 'SPOT_REPAYMENT_BUY',
    value: 'SPOT_REPAYMENT_BUY',
  },
  {
    label: 'TOKENS_SUBSCRIPTION',
    value: 'TOKENS_SUBSCRIPTION',
  },
  {
    label: 'TOKENS_REDEMPTION',
    value: 'TOKENS_REDEMPTION',
  },
  {
    label: 'AUTO_DEDUCTION',
    value: 'AUTO_DEDUCTION',
  },
  {
    label: 'FLEXIBLE_STAKING_SUBSCRIPTION',
    value: 'FLEXIBLE_STAKING_SUBSCRIPTION',
  },
  {
    label: 'FLEXIBLE_STAKING_REDEMPTION',
    value: 'FLEXIBLE_STAKING_REDEMPTION',
  },
  {
    label: 'FIXED_STAKING_SUBSCRIPTION',
    value: 'FIXED_STAKING_SUBSCRIPTION',
  },
  {
    label: 'PREMARKET_TRANSFER_OUT',
    value: 'PREMARKET_TRANSFER_OUT',
  },
  {
    label: 'PREMARKET_DELIVERY_SELL_NEW_COIN',
    value: 'PREMARKET_DELIVERY_SELL_NEW_COIN',
  },
  {
    label: 'PREMARKET_DELIVERY_BUY_NEW_COIN',
    value: 'PREMARKET_DELIVERY_BUY_NEW_COIN',
  },
  {
    label: 'PREMARKET_DELIVERY_PLEDGE_PAY_SELLER',
    value: 'PREMARKET_DELIVERY_PLEDGE_PAY_SELLER',
  },
  {
    label: 'PREMARKET_ROLLBACK_PLEDGE_BACK',
    value: 'PREMARKET_ROLLBACK_PLEDGE_BACK',
  },
  {
    label: 'PREMARKET_DELIVERY_PLEDGE_BACK',
    value: 'PREMARKET_DELIVERY_PLEDGE_BACK',
  },
  {
    label: 'PREMARKET_ROLLBACK_PLEDGE_PENALTY_TO_BUYER',
    value: 'PREMARKET_ROLLBACK_PLEDGE_PENALTY_TO_BUYER',
  },
  {
    label: 'CUSTODY_NETWORK_FEE',
    value: 'CUSTODY_NETWORK_FEE',
  },
  {
    label: 'CUSTODY_SETTLE_FEE',
    value: 'CUSTODY_SETTLE_FEE',
  },
  {
    label: 'CUSTODY_LOCK',
    value: 'CUSTODY_LOCK',
  },
  {
    label: 'CUSTODY_UNLOCK',
    value: 'CUSTODY_UNLOCK',
  },
  {
    label: 'CUSTODY_UNLOCK_REFUND',
    value: 'CUSTODY_UNLOCK_REFUND',
  },
  {
    label: 'LOANS_BORROW_FUNDS',
    value: 'LOANS_BORROW_FUNDS',
  },
  {
    label: 'LOANS_PLEDGE_ASSET',
    value: 'LOANS_PLEDGE_ASSET',
  },
];
