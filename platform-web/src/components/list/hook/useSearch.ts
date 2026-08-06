import { computed, toRaw, unref, type ComputedRef } from 'vue';
import { watchDebounced } from '@vueuse/core';
import { isFunction } from '@/utils/is';
import type { BaseListProps, FetchParams } from '../types/type';

// 类似useTableForm
export function useSearch(
  propsRef: ComputedRef<BaseListProps>,
  fetch: (opt?: FetchParams) => Promise<Recordable<any>[] | undefined>,
) {
  const searchInfo = computed(() => propsRef.value?.searchInfo);
  // 是否手动筛选
  const isHandle = computed(() => propsRef.value?.isHandle);
  watchDebounced(
    searchInfo,
    (curV) => {
      if (!isHandle.value) {
        handleSearchInfoChange(toRaw(curV || {}));
      }
    },
    { deep: true, debounce: 1000, maxWait: 3000 },
  );
  function handleSearchInfoChange(info: Recordable) {
    const { handleSearchInfoFn } = unref(propsRef);
    if (handleSearchInfoFn && isFunction(handleSearchInfoFn)) {
      info = handleSearchInfoFn(info) || info;
    }
    void fetch({ pageIndex: 1, searchInfo: info });
  }
  return {
    handleSearchInfoChange,
  };
}
