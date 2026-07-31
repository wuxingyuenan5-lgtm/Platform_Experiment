import { BasicResult } from './baseModel';

export interface RateModel {
  exchange: string;
  symbol: string;
  currency: string;
  category: string;
  vipLevel: string;
  hourlyBorrowRate: number;
  takerFeeRate: number;
  makerFeeRate: number;
  fundingRate: number;
  createTime: string;
}

export type RateListResultModel = BasicResult<RateModel>;
