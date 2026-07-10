<template>
  <div class="login-box">
    <div class="login-form py-20">
      <div class="title">欢迎登录</div>
      <div class="title title-platform pt-2 text-xl">全球变量金融平台</div>
      <div class="login-form__subhead">
        登录后会自动跳转到你刚刚点击的目标页面；首页、研究框架、新闻日历、金融 AI
        等入口都支持先登录再直达。
      </div>

      <Form
        ref="formRef"
        layout="vertical"
        class="px-20 pt-12"
        :model="formData"
        :rules="getFormRules"
        v-show="getShow"
        @keypress.enter="loginFirst"
      >
        <FormItem name="name" label="账号" class="enter-x mb-8">
          <Input
            v-model:value="formData.name"
            placeholder="请输入账号"
            class="fix-auto-fill login-input"
          />
        </FormItem>

        <FormItem name="password" label="密码" class="enter-x mb-6">
          <Input.Password
            class="login-input"
            visibilityToggle
            v-model:value="formData.password"
            placeholder="请输入密码"
          />
        </FormItem>

        <FormItem class="enter-x">
          <Button
            style="width: 320px; height: 46px"
            type="primary"
            block
            @click="loginFirst"
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
      </Form>
    </div>

    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </div>
</template>

<script lang="ts" setup>
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { reactive, ref, unref, computed, onBeforeUnmount } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { Form, Input, Button } from 'ant-design-vue';
  import { useI18n } from '@/hooks/web/useI18n';
  import { useMessage } from '@/hooks/web/useMessage';
  import { useUserStore } from '@/store/modules/user';
  import { LoginStateEnum, useLoginState, useFormRules, useFormValid } from './useLogin';
  import { useDesign } from '@/hooks/web/useDesign';
  import { loginApi } from '@/api/sys/user';

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

  const visibleGoogle = ref(false);
  const refGoogle = ref();
  let curParams: any = null;

  const { validForm } = useFormValid(formRef);
  const getShow = computed(() => unref(getLoginState) === LoginStateEnum.LOGIN);

  function handleClickConfirm(params: any) {
    const payload = { ...curParams, ...params, action: 'verify' };
    loginCode(payload);
  }

  function goRegisterApply() {
    router.push('/register-apply');
  }

  function loginCode(params: any) {
    loading.value = true;
    loginApi(params, 'none')
      .then(async (res: any) => {
        if (res && res.retCode === 0) {
          await successLogin(res.data);
        } else if (res && (res.token || res.access_token || res.userId)) {
          await successLogin(res);
        } else {
          failLoginModal(res);
        }
      })
      .catch((err) => {
        failLoginModal(err);
      })
      .finally(() => {
        refGoogle.value.loading = false;
        loading.value = false;
      });
  }

  async function loginFirst() {
    curParams = await validForm();
    if (!curParams) return;
    loading.value = true;
    try {
      const payload = {
        password: curParams.password,
        name: curParams.name,
        action: 'login',
      };
      const res: any = await loginApi(payload, 'none');
      if (res) {
        if (res.retCode === 0) {
          if (res.data) {
            await successLogin(res.data);
          } else {
            visibleGoogle.value = true;
          }
        } else if (res.token || res.access_token || res.userId) {
          await successLogin(res);
        } else {
          failLoginModal(res);
        }
      } else {
        failLoginModal({ msg: 'no response from server' });
      }
    } catch (error) {
      failLoginModal(error);
    } finally {
      loading.value = false;
    }
  }

  function failLoginModal(data: any) {
    let errorMessage = '';
    if (data?.response) {
      const status = data.response.status;
      const backendData = data.response.data;
      if (status === 401) {
        errorMessage =
          backendData?.msg ||
          backendData?.message ||
          backendData?.error ||
          '用户名或密码错误，请重试';
      } else {
        errorMessage = backendData?.msg || backendData?.message || `请求失败 (${status})`;
      }
    } else {
      errorMessage = data?.msg || data?.retMsg || t('sys.api.networkExceptionMsg');
    }

    createErrorModal({
      title: t('sys.api.errorTip'),
      content: errorMessage,
      getContainer: () => document.body.querySelector(`.${prefixCls}`) || document.body,
    });
  }

  async function successLogin(data: any) {
    createMessage.loading({
      content: '登录中...',
      key: 'successLogin',
      style: { marginTop: '25vh' },
      duration: 99,
    });

    try {
      const token =
        (data && (data.token || data.access_token)) ||
        (typeof data === 'string' ? data : undefined);
      if (!token) throw new Error('登录响应中缺少访问令牌');
      userStore.setToken(token);
      const userInfo = await userStore.afterLoginAction(true);
      if (userInfo) {
        notification.success({
          message: t('sys.login.loginSuccessTitle'),
          description: `${t('sys.login.loginSuccessDesc')}: ${curParams.name}`,
          duration: 3,
        });
      }

      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '';
      if (redirect) {
        router.replace(redirect);
        return;
      }

      router.replace('/home/index');
    } finally {
      createMessage.destroy('successLogin');
    }
  }

  onBeforeUnmount(() => {
    createMessage.destroy('successLogin');
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
        color: #0f172a;
        text-align: center;
      }

      .title-platform {
        font-family: Georgia, 'Times New Roman', 'Noto Serif SC', serif;
        font-size: 30px;
      }
    }

    .login-form__subhead {
      padding: 10px 52px 0;
      color: #64748b;
      font-size: 14px;
      line-height: 1.8;
      text-align: center;
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

    .login-box .login-form__subhead,
    .login-box .ant-form {
      padding-right: 28px !important;
      padding-left: 28px !important;
    }

    .login-box .login-input,
    .login-box .register-apply-btn,
    .login-box .ant-btn {
      width: 100% !important;
    }
  }
</style>
