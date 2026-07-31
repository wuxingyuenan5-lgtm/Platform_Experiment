import { defHttp } from '@/utils/http/axios';
import { FundingModel } from './model/fundingModel';
import { SymbolListResultModel } from './model/symbolModel';

enum Api {
  FUNDING_SYMBOLS = '/funding/symbols/',
  FUNDING_ADD = '/funding/add/',
}

export const getFundingSymbols = () =>
  defHttp.get<SymbolListResultModel>({ url: Api.FUNDING_SYMBOLS });

export const postFundingAdd = (data: FundingModel) => defHttp.post({ url: Api.FUNDING_ADD, data });
