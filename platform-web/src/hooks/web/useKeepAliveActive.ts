import { onActivated, onDeactivated, onMounted, onUnmounted, ref } from 'vue';

/** Tracks whether a mounted view is currently active inside or outside KeepAlive. */
export function useKeepAliveActive() {
  const active = ref(false);

  onMounted(() => {
    active.value = true;
  });
  onActivated(() => {
    active.value = true;
  });
  onDeactivated(() => {
    active.value = false;
  });
  onUnmounted(() => {
    active.value = false;
  });

  return active;
}
