import { useInterval } from '@vueuse/core';
import { ref } from 'vue';

// 获取验证码
interface CodeConfig {
  phone: string; // 电话号码
  count?: number; // 倒计时时间
}
export const useCode = (config: CodeConfig) => {
  const count = config?.count || 60;
  const counterMsg = ref(count);
  const { resume, pause } = useInterval(1000, {
    controls: true,
    immediate: false,
    callback: (count: number) => {
      counterMsg.value--;
      if (counterMsg.value < 0) {
        counterMsg.value = count;
        pause();
      }
    },
  });
  // 获取短信验证码
  function getCode() {
    counterMsg.value--;
    resume();
  }
  return {
    counterMsg,
    getCode,
    count,
  };
};
