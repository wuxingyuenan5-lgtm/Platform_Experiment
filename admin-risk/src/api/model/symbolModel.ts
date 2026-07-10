import { BasicResult } from './baseModel';

export interface SymbolItem {
  id: number;
  symbol: string;
  tradeType: string;
  exchange: string;
}

export type SymbolListResultModel = BasicResult<SymbolItem>;
