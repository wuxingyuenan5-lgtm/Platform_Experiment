import { BasicResult } from './baseModel';

export interface WalletbalanceSumModel {
  accountName: string;
  exchange: string;
  totalEquity: string;
  totalWalletBalance: string;
  totalPerpUPL: string;
  returnRate: string;
  todayProfit: string;
  cumProfit: string;
}

export type WalletbalanceSumListResultModel = BasicResult<WalletbalanceSumModel>;

export interface WalletbalanceModel {
  todayProfit: string;
  cumProfit: string;
  returnRate: string;
  totalPerpUPL: string;
  totalWalletBalance: string;
  accountMMRate: string;
  accountIMRate: string;
  totalEquity: string;
  exchange: string;
  accountName: string;
}

export type WalletbalanceListResultModel = BasicResult<WalletbalanceModel>;

export interface WalletbalanceCoinModel {
  coin: string;
  equity: string;
  walletBalance: string;
  borrowAmount: string;
  availableToWithdraw: string;
}

export type WalletbalanceCoinListResultModel = BasicResult<WalletbalanceCoinModel>;
