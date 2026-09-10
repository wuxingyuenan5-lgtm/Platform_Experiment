import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
import { Modal } from 'ant-design-vue';
import { hasPermission } from '@/access/userAccess';
import { useUserStore } from '@/store/modules/user';
import { UserSystemApiError } from '@/api/platform/userSystem';
import {
  addPoolCodes,
  getPoolFocus,
  getStockPool,
  removePoolCode,
  savePoolFocus,
  type PoolPayload,
  type Stock,
} from '@/api/platform/aShareStockPool';

export function useStockPool() {
  const user = useUserStore();
  const canEditPool = computed(() =>
    hasPermission(user.getAuthentication?.permissions || [], 'research.write'),
  );
  const canFocus = computed(() =>
    hasPermission(user.getAuthentication?.permissions || [], 'profile.update_self'),
  );
  const data = shallowRef<PoolPayload | null>(null);
  const loading = ref(false);
  const pending = ref(false);
  const error = ref('');
  const operationMessage = ref('');
  const focusCodes = ref<string[]>([]);
  const focusOpen = ref(false);
  const focusInput = ref('');
  const editOpen = ref(false);
  const batchInput = ref('');
  let focusVersion: number | null = null;
  let generation = 0;
  let activeLoad: Promise<void> | null = null;

  function load(): Promise<void> {
    if (activeLoad) return activeLoad;
    const current = generation;
    loading.value = true;
    error.value = '';
    activeLoad = (async () => {
      const results = await Promise.allSettled([getStockPool(), getPoolFocus()]);
      if (current !== generation) return;
      const [pool, focus] = results;
      if (pool.status === 'fulfilled') data.value = pool.value;
      else error.value = pool.reason instanceof Error ? pool.reason.message : '股票池加载失败';
      if (focus.status === 'fulfilled') {
        focusCodes.value = focus.value.codes;
        focusVersion = focus.value.rowVersion;
      } else {
        focusVersion = null;
        error.value = '个人关注加载失败，请刷新后再修改';
      }
    })().finally(() => {
      if (current === generation) {
        loading.value = false;
        activeLoad = null;
      }
    });
    return activeLoad;
  }

  function parseCodes(input: string): string[] {
    const codes = input
      .trim()
      .split(/[\s,，;；]+/)
      .filter(Boolean);
    if (!codes.length || codes.some((code) => !/^\d{5,6}$/.test(code))) {
      throw new Error('请输入完整的6位A股或5位港股代码，以空格或逗号分隔');
    }
    return [...new Set(codes)];
  }

  async function saveFocus(codes: string[]): Promise<boolean> {
    if (pending.value || !canFocus.value) return false;
    if (focusVersion == null) {
      operationMessage.value = '请先刷新个人关注';
      return false;
    }
    pending.value = true;
    const current = generation;
    try {
      const result = await savePoolFocus(codes, focusVersion);
      if (current !== generation) return false;
      focusCodes.value = result.codes;
      focusVersion = result.rowVersion;
      operationMessage.value = `近期关注已保存（${result.codes.length}只）`;
      await load();
      return true;
    } catch (cause) {
      if (current !== generation) return false;
      if (cause instanceof UserSystemApiError && cause.status === 409) {
        await load();
        operationMessage.value = '近期关注已在其他页面修改。已重新加载，请核对后再保存。';
      } else
        operationMessage.value = `保存失败：${
          cause instanceof Error ? cause.message : '请稍后重试'
        }`;
      return false;
    } finally {
      if (current === generation) pending.value = false;
    }
  }

  async function addFocus() {
    try {
      const codes = [...new Set([...focusCodes.value, ...parseCodes(focusInput.value)])];
      if (codes.length > 200) throw new Error('近期关注最多200只');
      if (await saveFocus(codes)) {
        focusInput.value = '';
        focusOpen.value = false;
      }
    } catch (cause) {
      operationMessage.value = (cause as Error).message;
    }
  }

  async function removeFocus(code: string) {
    await saveFocus(focusCodes.value.filter((value) => value !== code));
  }

  async function addBatch() {
    if (pending.value || !canEditPool.value) return;
    try {
      const codes = parseCodes(batchInput.value);
      if (codes.length > 50) throw new Error('每次最多添加50只');
      pending.value = true;
      const result = await addPoolCodes(codes);
      operationMessage.value = `已保存，核心股票池共${result.count}只；行情将在收盘更新后补齐`;
      batchInput.value = '';
      editOpen.value = false;
      await load();
    } catch (cause) {
      operationMessage.value = `添加失败：${(cause as Error).message}`;
    } finally {
      pending.value = false;
    }
  }

  function removePool(row: Stock) {
    if (pending.value || !canEditPool.value) return;
    Modal.confirm({
      title: `从团队核心池移除「${row.name}」？`,
      content: '个人近期关注不会受影响。',
      okText: '移除',
      cancelText: '取消',
      okType: 'danger',
      async onOk() {
        if (pending.value) return;
        pending.value = true;
        try {
          const result = await removePoolCode(row.code || row.instrument_id);
          operationMessage.value = `已移除${row.name}，核心池共${result.count}只`;
          await load();
        } catch (cause) {
          operationMessage.value = `移除失败：${(cause as Error).message}`;
          throw cause;
        } finally {
          pending.value = false;
        }
      },
    });
  }

  watch(
    () => user.getAuthentication?.user.userId,
    () => {
      generation += 1;
      activeLoad = null;
      data.value = null;
      focusCodes.value = [];
      focusVersion = null;
      operationMessage.value = '';
      pending.value = false;
      focusOpen.value = editOpen.value = false;
      if (user.getAuthentication) void load();
    },
  );
  onBeforeUnmount(() => {
    generation += 1;
  });
  return {
    data,
    loading,
    pending,
    error,
    operationMessage,
    focusCodes,
    focusOpen,
    focusInput,
    editOpen,
    batchInput,
    canEditPool,
    canFocus,
    load,
    addFocus,
    removeFocus,
    addBatch,
    removePool,
  };
}
