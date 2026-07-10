export interface PricediffModel {
  spotSymbol: number; // 现货标的
  diffSymbol: number; // 对应加差价套利标的
  diffInMin: number; // 入场范围最小值
  diffInMax: number; // 入场范围最大值
  diffOutMin: number; // 出场范围最小值
  diffOutMax: number; // 出场范围最大值
  position: number; // 入场金额
  perPosition: number; // 单位仓位
  isLeverage: boolean; // 是否现货杠杆
  checkCode: string; // 账号验证码
  isTestNet: boolean; // 是否测试网执行
}

export interface PricediffStrategy {
  strategyInMin: number; // 价差开仓下限
  strategyInMax: number; //  价差开仓上限
  strategyOutMin: number; // 价差平仓下限
  strategyOutMax: number; // 价差平仓上限
  position: number; // 策略开仓总仓位（最大持仓规模）
  riskLimitValue: string; // 套利标的风险限额（仅linear和inverse）
  spotSymbolCategory: string; //
  spotSymbol: string; // 现货标的名称
  diffSymbolCategory: string;
  diffSymbol: string; // 价差标的名称
  strategyStatus: boolean; //  策略状态（Ture为正常运行，False为停止）
}
