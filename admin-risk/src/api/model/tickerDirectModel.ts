import { BasicResult } from './baseModel';

export interface TickerDirectSpotModel {
  askImpactDepth: string;
  bidImpactDepth: string;
  lastPrice: string;
  symbol: string;
  category: string;
}

export type TickerDirectSpotListResultModel = BasicResult<TickerDirectSpotModel>;

export interface TickerDirectFutureModel {
  APR: string;
  basisRate: string;
  askImpactDepth: string;
  bidImpactDepth: string;
  maxLeverage: string;
  markPrice: string;
  lastPrice: string;
  symbol: string;
  category: string;
}

export type TickerDirectFutureListResultModel = BasicResult<TickerDirectFutureModel>;
