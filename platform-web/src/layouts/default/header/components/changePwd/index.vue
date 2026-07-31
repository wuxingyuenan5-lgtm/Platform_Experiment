<template>
  <BasicModal
    :confirmLoading="loading"
    @ok="handleOk"
    :canFullscreen="false"
    v-bind="$attrs"
    @register="register"
  >
    <template #title>
      <div>修改密码</div>
    </template>
    <BasicForm @register="registerForm" />
    <!-- 谷歌验证 -->
    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </BasicModal>
</template>
<script lang="ts" setup>
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { ref } from 'vue';
  import { BasicModal, useModalInner } from '@/components/Modal';
  import { BasicForm, useForm } from '@/components/Form';
  import { formSchema } from './pwd.data';
  import { loginChangepw } from '@/api/sys/user';
  import { useMessage } from '@/hooks/web/useMessage';
  import { useUserStore } from '@/store/modules/user';

  const [register, { closeModal }] = useModalInner();
  const { createMessage } = useMessage();
  const loading = ref(false);
  const userStore = useUserStore();
  const userInfo = userStore.getUserInfoInfo;
  const time = ref(3);
  let curParams = {};
  const props = defineProps({
    code: {
      type: String,
      default: '',
    },
  });
  const [registerForm, { validate, resetFields }] = useForm({
    // size: 'large',
    baseColProps: { span: 24 },
    labelWidth: 90,
    showActionButtonGroup: false,
    schemas: formSchema,
  });
  const visibleGoogle = ref(false); // google验证码
  const refGoogle = ref();

  function handleOk() {
    validate().then((res) => {
      const _params = res;
      curParams = _params;
      if (userInfo?.isGoogleAuthEnabled) {
        visibleGoogle.value = true;
      } else {
        loginChangepwFn(_params);
      }
      // TODO 移除Google验证
      console.log('params', _params);
    });
  }
  function handleClickConfirm(params: any) {
    const _params = { ...curParams, ...params };
    loginChangepwFn(_params);
  }
  function loginChangepwFn(params: any) {
    loading.value = true;
    loginChangepw(params)
      .then((res) => {
        if (res.retCode == 0) {
          createMessage.success({
            content: () => `修改密码成功,${time.value}秒后自动退出`,
            key: 'Changepw',
            duration: 3,
          });
          setTimeout(() => {
            time.value = 2;
          }, 1000);
          setTimeout(() => {
            time.value = 1;
          }, 2000);
          setTimeout(() => {
            time.value = 0;
            userStore.logout(true);
          }, 3000);
        } else {
          createMessage.error({
            content: res.msg || '修改密码失败',
            key: 'Changepw',
            duration: 2,
          });
        }
      })
      .finally(() => {
        loading.value = false;
        refGoogle.value.loading = false;
      });
  }
</script>
