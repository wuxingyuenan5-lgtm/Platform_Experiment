import type { AxiosRequestConfig, AxiosResponse } from 'axios';
import componentSetting from '@/settings/componentSetting';
// 用于存储每个请求的标识和响应数据
const resultCacheMap = new Map<string, Object>();

const getResultUrl = (config: AxiosRequestConfig): string => {
  let _url;
  const regexdefault = /.com\/(.+?)\/$/;
  const regex = /"\/(.+?)\/"/;
  if (config.url?.toString().includes('.com/')) {
    _url = config.url?.toString().match(regexdefault)?.[1];
  } else {
    _url = config.url?.toString().match(regex)?.[1];
  }
  return [_url, getParams(config.params)].join('&');
};

// 根据请求方法、URL、参数和请求体生成请求的唯一标识
// 先将参数中的时间戳移除
const getParams = (params: any): string => {
  const { table } = componentSetting;
  const _params = {};
  const whitelist = [
    '_t',
    table.fetchSetting.pageField,
    table.fetchSetting.sizeField,
    table.fetchSetting.totalField,
  ];
  if (params) {
    for (const key in params) {
      if (!whitelist.includes(key)) {
        _params[key] = params[key];
      }
    }
  }
  return JSON.stringify(_params);
};

export class AxiosCache {
  /**
   * 添加请求
   * @param config 请求配置
   */
  public addResult(res: AxiosResponse): void {
    const { config, data } = res;
    const { table } = componentSetting;
    // console.log('config----', config, table.fetchSetting.pageField);

    if (
      config.method === 'get' &&
      Object.prototype.hasOwnProperty.call(config?.params, table.fetchSetting.pageField)
    ) {
      this.removeResult(config);
      const url = getResultUrl(config);
      if (!resultCacheMap.has(url)) {
        // 如果当前请求不在等待中，将其添加到等待中
        resultCacheMap.set(url, data);
      }
      // console.log('resultCacheMap----', resultCacheMap);
    }
  }

  /**
   * 获取请求
   */
  public getResult(api: string, params: any): Object | undefined {
    let data;
    const url = getResultUrl({ url: api, params });
    if (resultCacheMap.has(url)) {
      data = resultCacheMap.get(url);
    }
    return data;
  }
  /**
   * 移除请求
   * @param config 请求配置
   */
  public removeResult(config: AxiosRequestConfig): void {
    const url = getResultUrl(config);
    if (resultCacheMap.has(url)) {
      resultCacheMap.delete(url);
    }
  }

  /**
   * 重置
   */
  public removeAllresult(): void {
    resultCacheMap.clear();
  }
}
