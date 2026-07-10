<template>
  <div v-if="curVisible" class="box">
    <div class="content">
      <div class="title text-center">请输入谷歌验证器动态码</div>
      <div class="flex justify-center mt-2">
        <CodeElm @change="changeCode" @enter="handleConfirm" ref="codeRef" />
      </div>
      <div :class="['code-msg', codeMsg && 'is-visible']">{{ codeMsg }}</div>
      <div class="btn-box">
        <GhostButton
          class="text-center"
          style="width: 130px; height: 32px; background-color: transparent; line-height: 20px"
          :onclick="closeMask"
          >取消</GhostButton
        >
        <Button
          :loading="loading"
          :disabled="curGoogleCode.length != 6"
          class="ml-3"
          style="width: 130px"
          type="primary"
          @click="handleConfirm"
          >确定</Button
        >
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { ref, watch } from 'vue';
  import { Button } from 'ant-design-vue';
  import GhostButton from '@/components/Button/src/GhostButton.vue';
  import { TypeGoogleCode } from './type';
  import CodeElm from '@/components/Code/Code.vue';

  const props = defineProps({
    type: {
      type: String as PropType<TypeGoogleCode>,
      default: TypeGoogleCode.REJECT,
    },
    visible: {
      type: Boolean,
      default: false,
    },
  });
  const emit = defineEmits(['update:visible', 'confirm']);
  const curVisible = ref(false);
  watch(
    () => props.visible,
    (newVal) => {
      curVisible.value = newVal;
      if (!newVal) {
        loading.value = false;
        closeMask();
      }
    },
  );
  watch(
    () => curVisible.value,
    (newVal) => {
      emit('update:visible', newVal);
    },
  );
  const curGoogleCode = ref('');
  const codeRef = ref();
  function changeCode(val) {
    curGoogleCode.value = val.code;
    if (val.code.length === 6) {
      setTimeout(() => {
        handleConfirm();
      }, 100);
    }
  }

  const codeMsg = ref('');
  const loading = ref(false);

  function closeMask() {
    curVisible.value = false;
    codeMsg.value = '';
  }
  function handleConfirm() {
    if (curGoogleCode.value.length != 6) return;
    loading.value = true;
    emit('confirm', { code: curGoogleCode.value, type: props.type });
  }

  defineExpose({ loading, codeMsg, closeMask });
</script>
<style lang="less" scoped>
  .box {
    display: flex;
    position: fixed;
    z-index: 9999;
    align-items: center;
    justify-content: center;
    background: rgb(0 0 0 / 50%);
    inset: 0;

    .content {
      width: 360px;
      height: 208px;
      padding: 20px 44px 12px;
      border-radius: 8px;
      background: @component-background;
      box-shadow: 0 2px 16px -4px rgb(0 0 0 / 50%);

      .code-msg {
        opacity: 0;
        color: @error-color;
        font-size: 12px;
        line-height: 16px;

        &.is-visible {
          opacity: 1;
        }
      }

      .btn-box {
        margin-top: 30px;
        margin-bottom: 4px;
      }

      .btn-msg {
        color: @text-color-secondary;
        font-size: 12px;
      }

      .title {
        height: 20px;
        // color: #fff;
        font-family: MicrosoftYaHei;
        font-size: 16px;
        line-height: 20px;
      }

      .msg {
        color: @text-color-secondary;
        font-family: RobotoRegular;
        font-size: 12px;
        font-weight: 400;
        line-height: 16px;
      }
    }
  }
</style>
