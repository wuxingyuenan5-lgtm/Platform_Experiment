import { BasicResult } from './baseModel';

export interface HistoryOrderModel {
  orderType: string;
  orderStatus: string;
  orderId: string;
  createdTime: string;
  value: string;
  qty: string;
  price: string;
  cumExecValue: string;
  cumExecQty: string;
  avgPrice: string;
  side: string;
  category: string;
  symbol: string;
}

export type HistoryOrderListResultModel = BasicResult<HistoryOrderModel>;
