<template>
  <div class="login-box">
    <div class="login-form py-20">
      <div class="title">欢迎登录</div>
      <div class="title title-platform">全球变量金融平台</div>

      <Form
        ref="formRef"
        layout="vertical"
        class="px-20 pt-12"
        :model="formData"
        :rules="getFormRules"
        v-show="getShow"
        @keypress.enter="handleLogin"
      >
        <FormItem name="name" label="账号" class="enter-x mb-8">
          <Input
            v-model:value="formData.name"
            placeholder="请输入账号"
            class="fix-auto-fill login-input"
            autocomplete="username"
          />
        </FormItem>

        <FormItem name="password" label="密码" class="enter-x mb-6">
          <Input.Password
            class="login-input"
            visibilityToggle
            v-model:value="formData.password"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </FormItem>

        <FormItem class="enter-x">
          <Button
            style="width: 320px; height: 46px"
            type="primary"
            block
            @click="handleLogin"
            :loading="loading"
          >
            {{ t('sys.login.loginButton') }}
          </Button>
        </FormItem>

        <Button
          block
          class="register-apply-btn mt-4 enter-x"
          html-type="button"
          @click.prevent="goRegisterApply"
        >
          没有账号？提交注册申请
        </Button>
        <Button
          type="link"
          block
          class="reset-password-btn mt-2 enter-x"
          html-type="button"
          @click.prevent="goResetPassword"
        >
          已有一次性重置凭证？设置新密码
        </Button>
      </Form>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref, unref, computed, onBeforeUnmount } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { Form, Input, Button } from 'ant-design-vue';
  import { useI18n } from '@/hooks/web/useI18n';
  import { useMessage } from '@/hooks/web/useMessage';
  import { useUserStore } from '@/store/modules/user';
  import { LoginStateEnum, useLoginState, useFormRules, useFormValid } from './useLogin';
  import { useDesign } from '@/hooks/web/useDesign';
  import { UserSystemApiError } from '@/api/platform/userSystem';

  const FormItem = Form.Item;
  const { t } = useI18n();
  const { notification, createErrorModal, createMessage } = useMessage();
  const { prefixCls } = useDesign('login');
  const userStore = useUserStore();
  const { getLoginState } = useLoginState();
  const router = useRouter();
  const route = useRoute();
  const { getFormRules } = useFormRules();

  const formRef = ref();
  const loading = ref(false);
  const formData = reactive({
    name: '',
    password: '',
  });

  const { validForm } = useFormValid(formRef);
  const getShow = computed(() => unref(getLoginState) === LoginStateEnum.LOGIN);

  function goRegisterApply() {
    router.push('/register-apply');
  }

  function goResetPassword() {
    router.push('/reset-password');
  }

  function showLoginError(error: unknown) {
    const known = error instanceof UserSystemApiError ? error : null;
    const messages: Record<string, string> = {
      account_pending: '账号正在等待审核，审核通过后方可登录',
      account_disabled: '账号已停用，请联系管理员',
      account_rejected: '注册申请未通过',
      account_temporarily_locked: '账号已临时锁定，请稍后重试',
      invalid_credentials: '账号或密码错误',
    };
    createErrorModal({
      title: t('sys.api.errorTip'),
      content: (known?.code && messages[known.code]) || known?.message || '登录失败，请稍后重试',
      getContainer: () => document.body.querySelector(`.${prefixCls}`) || document.body,
    });
  }

  async function handleLogin() {
    const params = await validForm();
    if (!params || loading.value) return;
    loading.value = true;
    createMessage.loading({
      content: '登录中...',
      key: 'user-system-login',
      style: { marginTop: '25vh' },
      duration: 99,
    });
    try {
      const userInfo = await userStore.login({
        name: params.name,
        password: params.password,
        goHome: false,
        mode: 'none',
      });
      if (!userInfo) throw new Error('登录状态初始化失败');
      notification.success({
        message: t('sys.login.loginSuccessTitle'),
        description: `${t('sys.login.loginSuccessDesc')}: ${params.name}`,
        duration: 3,
      });
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '';
      await router.replace(redirect || (userInfo as any).homePath || '/home/index');
    } catch (error) {
      showLoginError(error);
    } finally {
      loading.value = false;
      createMessage.destroy('user-system-login');
    }
  }

  onBeforeUnmount(() => {
    createMessage.destroy('user-system-login');
  });
</script>

<style lang="less">
  .login-box {
    display: flex;
    justify-content: center;
    width: min(1140px, 100%);
    min-height: 100vh;
    margin: 0 auto;
    padding: 96px 32px 72px;

    .login-form {
      width: 520px;
      margin: auto;
      padding-top: 18px;
      border: 1px solid rgba(214, 221, 229, 0.96);
      border-radius: 26px;
      background: rgba(255, 255, 255, 0.94);
      box-shadow: 0 30px 90px rgba(135, 155, 182, 0.16);
      backdrop-filter: blur(18px);

      .title {
        font-family: Georgia, 'Times New Roman', 'Noto Serif SC', serif;
        color: #0f172a;
        font-size: 18px;
        font-weight: 400;
        line-height: 30px;
        text-align: center;
      }

      .title-platform {
        margin-top: 10px;
        font-size: 30px;
        font-weight: 400;
        line-height: 40px;
      }
    }

    .ant-form {
      padding-top: 34px !important;
    }

    .login-input {
      width: 320px;
      height: 46px;
      border: 1px solid rgba(203, 213, 225, 0.95);
      border-radius: 12px;
      background: rgba(248, 250, 252, 0.96) !important;
      font-size: 14px;

      .ant-input {
        background: transparent !important;
      }
    }

    .register-apply-btn {
      width: 320px;
      height: 46px;
      border-color: rgba(203, 213, 225, 0.95);
      border-radius: 12px;
      color: #475569;
      font-size: 14px;
      font-weight: 400;
    }

    .reset-password-btn {
      width: 320px;
      color: #64748b;
    }

    .ant-form .ant-form-item-label > label {
      font-size: 14px;
      line-height: 16px;
    }
  }

  @media (max-width: 760px) {
    .login-box {
      padding: 72px 18px 40px;
    }

    .login-box .login-form {
      width: 100%;
      max-width: 420px;
    }

    .login-box .ant-form {
      padding-right: 28px !important;
      padding-left: 28px !important;
    }

    .login-box .login-input,
    .login-box .register-apply-btn,
    .login-box .reset-password-btn,
    .login-box .ant-btn {
      width: 100% !important;
    }
  }
</style>
