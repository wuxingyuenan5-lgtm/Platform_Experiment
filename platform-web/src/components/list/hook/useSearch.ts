import {
  computed,
  unref,
  ref,
  watch,
  reactive,
  onMounted,
  type ComputedRef,
  type Ref,
  watchEffect,
  isRef,
  toRaw,
} from 'vue';
import type { BaseTableProps, SorterResult, FetchParams } from '../types/type';
import { isFunction } from '@/utils/is';
import { watchDebounced } from '@vueuse/core';
// 类似useTableForm
export function useSearch(
  propsRef: ComputedRef<BaseTableProps>,
  fetch: (opt?: FetchParams | undefined) => Promise<Recordable<any>[] | undefined>,
) {
  const searchInfo = computed(() => propsRef.value?.searchInfo);
  // 是否手动筛选
  const isHandle = computed(() => propsRef.value?.isHandle);
  watchDebounced(
    searchInfo,
    (curV) => {
      if (!isHandle.value) {
        handleSearchInfoChange(toRaw(curV));
      }
    },
    { deep: true, debounce: 1000, maxWait: 3000 },
  );
  function handleSearchInfoChange(info: Recordable) {
    const { handleSearchInfoFn } = unref(propsRef);
    if (handleSearchInfoFn && isFunction(handleSearchInfoFn)) {
      info = handleSearchInfoFn(info) || info;
    }
    fetch({ pageIndex: 1 });
  }
  return {
    handleSearchInfoChange,
  };
}
