import { ref, type ComputedRef, unref, computed, watch } from 'vue';
import type { BaseListProps } from '../types/type';

export function useLoading(props: ComputedRef<BaseListProps>) {
  const loadingRef = ref(unref(props).loading);

  watch(
    () => unref(props).loading,
    (loading) => {
      loadingRef.value = loading;
    },
  );

  const getLoading = computed(() => unref(loadingRef));

  function setLoading(loading: boolean) {
    loadingRef.value = loading;
  }

  return { getLoading, setLoading };
}
