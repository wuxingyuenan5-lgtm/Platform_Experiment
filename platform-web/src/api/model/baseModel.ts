export interface BasicPageParams {
  page: number;
  pageSize: number;
}

export interface BasicFetchResult<T> {
  items: T[];
  total: number;
}

export interface BasicResult<T> {
  data: T[];
  retCode: number;
  retMsg: string;
}
