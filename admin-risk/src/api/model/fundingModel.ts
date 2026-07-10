export interface FundingModel {
  spotSymbol: number | any[]; // 现货标的
  fundSymbol: number; // 对应资金费率标的
  fundingInMin: number; // 入场范围最小值
  fundingInMax: number; // 入场范围最大值
  fundingOutMin: number; // 出场范围最小值
  fundingOutMax: number; // 出场范围最大值
  position: number; // 入场金额
  perPosition: number; // 单位仓位
  isLeverage: boolean; // 是否现货杠杆
  checkCode: string; // 账号验证码
  isTestNet: boolean; // 是否测试网执行
}
