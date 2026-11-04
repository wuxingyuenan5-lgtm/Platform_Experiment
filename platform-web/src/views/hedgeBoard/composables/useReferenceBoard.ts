import { ref, shallowRef, onBeforeUnmount } from 'vue';
import { researchRequest } from '@/api/hedgeResearch';
// Public reference documents retain the upstream schema and nullable fields.
export function useReferenceBoard(board: 'liquidity' | 'stocks') {
  const data = shallowRef<Record<string, any>>();
  const error = ref(''),
    loading = ref(false);
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    try {
      const result = await researchRequest<Record<string, any>>({
        method: 'GET',
        url: '/research/reference-boards/' + board,
        signal: current.signal,
      });
      if (!current.signal.aborted) data.value = result;
    } catch {
      if (!current.signal.aborted) error.value = '数据读取失败，请重试';
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  load();
  onBeforeUnmount(() => controller?.abort());
  return { data, error, loading, load };
}
