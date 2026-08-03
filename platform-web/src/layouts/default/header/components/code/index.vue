<template>
  <BasicModal :footer="null" :canFullscreen="false" v-bind="$attrs" @register="register">
    <template #title>
      <div>谷歌验证</div>
    </template>
    <div class="flex justify-center items-center">
      <QRCode
        cancel
        :size="160"
        :value="code"
        error-level="H"
        icon="/logo.png"
        color="#000000FF"
        bgColor="#00000008"
        style="border-color: transparent"
      />
    </div>

    <div class="text-center color-secondary text-xs mt-1">扫码后输入动态码绑定账户</div>
    <div class="flex justify-center mt-2">
      <CodeElm @change="changeCode" ref="codeRef" />
    </div>

    <div class="flex justify-center mt-10">
      <GhostButton
        class="text-center"
        style="width: 130px; height: 32px; background-color: transparent; line-height: 20px"
        :onclick="closeModalFn"
        >取消</GhostButton
      >
      <Button
        :loading="loading"
        :disabled="curGoogleCode.length != 6"
        class="ml-3"
        style="width: 130px"
        type="primary"
        @click="handleConfirm"
        >绑定</Button
      >
    </div>
  </BasicModal>
</template>
<script lang="ts" setup>
  import { ref } from 'vue';
  import { QRCode, Button } from 'ant-design-vue';
  import { BasicModal, useModalInner } from '@/components/Modal';
  import CodeElm from '@/components/Code/Code.vue';
  import GhostButton from '@/components/Button/src/GhostButton.vue';
  import { postLoginQrcode } from '@/api/sys/user';
  import { useMessage } from '@/hooks/web/useMessage';
  import { useUserStore } from '@/store/modules/user';

  const { createMessage } = useMessage();

  const [register, { closeModal }] = useModalInner();
  const props = defineProps({
    code: {
      type: String,
      default: '',
    },
  });
  const userStore = useUserStore();
  const curGoogleCode = ref('');
  const codeRef = ref();
  const loading = ref(false);
  async function handleConfirm() {
    const res = await postLoginQrcode({ code: curGoogleCode.value });
    if (res.retCode === 0) {
      createMessage.success({
        content: '绑定成功',
        key: 'postLoginQrcode',
        duration: 2,
      });
      chageUserInfo();
      closeModalFn();
    } else {
      createMessage.error({
        content: res.msg || '"验证失败',
        key: 'postLoginQrcode',
        duration: 2,
      });
    }
  }
  function changeCode(val) {
    curGoogleCode.value = val.code;
  }
  function closeModalFn() {
    closeModal();
    codeRef.value?.clearAll?.();
  }
  function chageUserInfo() {
    userStore.getUserInfoAction();
    // const userInfo = userStore.userInfo;
    // if (userInfo) {
    //   userInfo.isGoogleAuthEnabled = true;
    //   userStore.setUserInfo(userInfo);
    // }
  }
</script>
