import { defineComponent, computed, ref, unref, toRaw } from 'vue';
import { List } from 'ant-design-vue';
import style from './index.module.less';
import type { BaseListProps } from './types/type';
import { useDataSource } from './hook/useDataSource';
import { useLoading } from './hook/useLoading';
import { useSearch } from './hook/useSearch';
import { usePagination } from './hook/usePagination';
import { baseListProps } from './props';
import { isFunction } from '@/utils/is';

export default defineComponent({
  props: baseListProps,
  emits: ['change', 'fetch-success'],
  setup(props, { attrs, slots, emit, expose }) {
    const listData = ref([]);

    const getProps = computed(() => {
      return {
        ...props,
      };
    });
    const { getLoading, setLoading } = useLoading(getProps);
    const { getPaginationInfo, setPagination } = usePagination(getProps, { handleListChange });
    const {
      handleTableChange: onTableChange,
      getDataSourceRef,
      fetch,
    } = useDataSource(
      getProps,
      {
        setLoading,
        getPaginationInfo,
        listData,
        setPagination,
      },
      emit,
    );
    const { handleSearchInfoChange } = useSearch(getProps, fetch);
    function handleListChange(pagination: any, filters: any, sorter: any, extra: any) {
      onTableChange(pagination, filters, sorter);
      emit('change', pagination, filters, sorter, extra);
      // 解决通过useTable注册onChange时不起作用的问题
      const { onChange } = unref(getProps);
      onChange && isFunction(onChange) && onChange(pagination, filters, sorter, extra);
    }
    const getBindValues = computed(() => {
      const dataSource = unref(getDataSourceRef);
      return {
        ...attrs,
        ...slots,
        ...unref(getProps),
        loading: unref(getLoading),
        pagination: toRaw(unref(getPaginationInfo)),
        dataSource,
      };
    });
    expose({
      fetch,
      listData,
    });
    return () => {
      return <List {...getBindValues.value} class={style.list}></List>;
    };
  },
});
