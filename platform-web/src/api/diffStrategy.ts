import { defHttp } from '@/utils/http/axios';
import { DiffStrategyModel } from './model/diffStrategyModel';

enum Api {
  DIFF_IN = '/diff_strategy/diff_in/',
  DIFF_OUT = '/diff_strategy/diff_out/',
}

export const getDiffIn = () => defHttp.get({ url: Api.DIFF_IN });

export const postDiffIn = (data: DiffStrategyModel) => defHttp.post({ url: Api.DIFF_IN, data });

export const getDiffOut = () => defHttp.get({ url: Api.DIFF_OUT });
