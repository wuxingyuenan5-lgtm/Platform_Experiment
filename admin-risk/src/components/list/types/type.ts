import type { ListProps } from 'ant-design-vue';

export interface FetchSetting {
  // 请求接口当前页数
  pageField: string;
  // 每页显示多少条
  sizeField: string;
  // 请求结果列表字段  支持 a.b.c
  listField: string;
  // 请求结果总数字段  支持 a.b.c
  totalField: string;
}

export interface BaseListProps extends ListProps {
  // 接口请求对象
  api?: (...arg: any) => Promise<any>;
  // 额外的请求参数
  searchInfo?: any;
  // 是否手动筛选
  isHandle?: boolean;
  beforeFetch?: Fn;
  afterFetch?: Fn;
  // 请求接口配置
  fetchSetting?: Partial<FetchSetting>;
  // 是否显示loading动画
  showLoading?: boolean;
  // 立即执行
  immediate?: boolean;
  clearSelectOnPageChange?: boolean;
  // 是否仅对现有数据做操作
  isOnlyCurrentData?: boolean;
  // 查询条件请求之前处理
  handleSearchInfoFn?: Fn;
}

export interface FetchParams {
  searchInfo?: Recordable;
  pageIndex?: number;
  sortInfo?: Recordable;
  filterInfo?: Recordable;
}
