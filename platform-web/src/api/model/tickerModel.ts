import { BasicResult } from './baseModel';

export interface TickerModel {
  exchange: string;
  symbol: string;
  tradeType: string;
  category: string;
  lastPrice: number;
  indexPrice: number;
  markPrice: number;
  premiumIndex: number;
  openInterest: number;
  fundingRate: number;
  createTime: string;
}

export type TickerListResultModel = BasicResult<TickerModel>;
