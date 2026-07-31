import { computed, unref, ref, watch, type ComputedRef } from 'vue';
import type { BaseListProps } from '../types/type';
import { isBoolean } from '@/utils/is';
import { listSetting } from '../const';
import type { PaginationProps } from '../types/pagination';

// @ts-ignore
export function usePagination(refProps: ComputedRef<BaseListProps>, { handleListChange }) {
  const configRef = ref<any>({});

  watch(
    () => unref(refProps).pagination,
    (pagination) => {
      if (!isBoolean(pagination) && pagination) {
        // @ts-ignore
        configRef.value = {
          ...unref(configRef),
          ...(pagination ?? {}),
        };
      }
    },
  );
  const getPaginationInfo = computed((): PaginationProps | boolean => {
    const { pagination } = unref(refProps);
    if (isBoolean(pagination) && !pagination) return false;

    return {
      onChange: (page, pageSize) => {
        handleListChange({ current: page, pageSize });
      },
      hideOnSinglePage: false,
      current: 1,
      size: 'middle',
      defaultPageSize: listSetting.defaultPageSize,
      // showTotal: (total) => t('component.table.total', { total }),
      // showSizeChanger: true,
      pageSizeOptions: listSetting.pageSizeOptions,
      //   itemRender: itemRender,
      showQuickJumper: true,
      position: 'bottom',
      ...(isBoolean(pagination) ? {} : pagination),
      ...unref(configRef),
    };
  });
  function setPagination(info: Partial<PaginationProps>) {
    const paginationInfo = unref(getPaginationInfo);
    configRef.value = {
      ...(!isBoolean(paginationInfo) ? paginationInfo : {}),
      ...info,
    };
  }
  function getPagination() {
    return unref(getPaginationInfo);
  }
  return {
    getPaginationInfo,
    setPagination,
    getPagination,
  };
}
