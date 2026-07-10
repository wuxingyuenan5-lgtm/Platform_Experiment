import type { FetchSetting } from './types/type';
import { listSetting } from './const';

import type { ColumnProps } from 'ant-design-vue/es/table';

export const baseListProps = {
  api: {
    type: [Function as PropType<(...arg: any[]) => Promise<any>>, Function as PropType<any>],
    default: null,
  },
  beforeFetch: {
    type: Function as PropType<Fn>,
    default: null,
  },
  afterFetch: {
    type: Function as PropType<Fn>,
    default: null,
  },
  dataSource: {
    type: Array as PropType<Recordable[]>,
    default: null,
  },
  // 额外的请求参数
  searchInfo: {
    type: Object as PropType<Recordable>,
    default: null,
  },
  isHandle: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  immediate: {
    type: Boolean,
    default: true,
  },
  fetchSetting: {
    type: Object as PropType<FetchSetting>,
    default: () => {
      return listSetting.fetchSetting;
    },
  },
};
