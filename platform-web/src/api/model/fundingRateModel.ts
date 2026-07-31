import { BasicResult } from './baseModel';

export interface FundingItemModel {
  exchange: string;
  funding_rate_USDT: string;
  funding_rate_USD: string;
}
export interface FundingRateModel {
  currency: string;
  subData: FundingItemModel[];
  [key: string]: string | any;
}

export interface BorrowItemModel {
  exchange: string;
  borrow_rate: string;
}

export interface BorrowRateModel {
  currency: string;
  subData: FundingItemModel[];
  [key: string]: string | any;
}

export type FundingRateListResultModel = BasicResult<FundingRateModel>;
export type BorrowRateListResultModel = BasicResult<BorrowRateModel>;
