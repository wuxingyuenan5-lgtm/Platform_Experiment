import { computed, defineComponent, h, ref, toRaw, unref } from 'vue';
import type { ListProps } from 'ant-design-vue';
import { List } from 'ant-design-vue';
import { isFunction } from '@/utils/is';
import { useDataSource } from './hook/useDataSource';
import { useLoading } from './hook/useLoading';
import { usePagination } from './hook/usePagination';
import { useSearch } from './hook/useSearch';
import style from './index.module.less';
import { baseListProps } from './props';

export default defineComponent({
  props: baseListProps,
  emits: ['change', 'fetch-success', 'fetch-error'],
  setup(props, { attrs, slots, emit, expose }) {
    const listData = ref<Recordable[]>([]);

    const getProps = computed(() => ({ ...props }));
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
    useSearch(getProps, fetch);

    function handleListChange(pagination: any, filters: any, sorter: any, extra: any) {
      onTableChange(pagination, filters, sorter);
      emit('change', pagination, filters, sorter, extra);
      const { onChange } = unref(getProps);
      if (onChange && isFunction(onChange)) onChange(pagination, filters, sorter, extra);
    }

    const getBindValues = computed<ListProps>(() => ({
      ...attrs,
      ...unref(getProps),
      loading: unref(getLoading),
      pagination: toRaw(unref(getPaginationInfo)),
      dataSource: unref(getDataSourceRef),
      class: style.list,
    }));

    expose({ fetch, listData });
    return () => h(List, getBindValues.value, slots);
  },
});
