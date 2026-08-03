import { BasicResult } from './baseModel';

export interface PositionDirectModel {
  category: string;
  symbol: string;
  size: string;
  positionValue: string;
  markPrice: string;
  avgPrice: string;
  side: string;
}

export type PositionListResultModel = BasicResult<PositionDirectModel>;
