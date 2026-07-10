<template>
  <div class="register-apply-page">
    <div class="register-box">
      <div class="register-panel">
        <div class="title title-main">注册申请</div>
        <div class="title title-sub">全球变量金融平台</div>
        <Form
          ref="formRef"
          layout="vertical"
          class="form"
          :model="formData"
          :rules="rules"
          @keypress.enter="handleRegister"
        >
          <FormItem name="username" label="账号" class="mb-4">
            <Input v-model:value="formData.username" placeholder="请输入账号" class="form-input" />
          </FormItem>
          <FormItem name="email" label="邮箱" class="mb-4">
            <Input v-model:value="formData.email" placeholder="请输入邮箱" class="form-input" />
          </FormItem>
          <FormItem name="requested_role" label="申请身份" class="mb-4">
            <Select v-model:value="formData.requested_role" :options="roleOptions" class="form-input" />
          </FormItem>
          <FormItem name="password" label="密码" class="mb-4">
            <Input.Password
              v-model:value="formData.password"
              visibilityToggle
              placeholder="请输入密码"
              class="form-input"
            />
          </FormItem>
          <FormItem name="confirmPassword" label="确认密码" class="mb-4">
            <Input.Password
              v-model:value="formData.confirmPassword"
              visibilityToggle
              placeholder="请再次输入密码"
              class="form-input"
            />
          </FormItem>

          <Button type="primary" block class="submit-btn" html-type="button" :loading="loading" @click="handleRegister">
            提交申请
          </Button>
          <Button block class="back-btn" html-type="button" @click="router.push('/login')">返回登录</Button>
        </Form>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref, unref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Button, Form, Input, message, Select } from 'ant-design-vue';
  import type { RuleObject } from 'ant-design-vue/lib/form/interface';
  import { registerApi } from '@/api/sys/user';

  const FormItem = Form.Item;
  const router = useRouter();
  const formRef = ref();
  const loading = ref(false);

  const formData = reactive({
    username: '',
    email: '',
    requested_role: 'guest' as 'guest' | 'employee' | 'admin',
    password: '',
    confirmPassword: '',
  });

  const roleOptions = [
    { label: '访客', value: 'guest' },
    { label: '员工', value: 'employee' },
    { label: '管理员', value: 'admin' },
  ];

  const validateConfirmPassword = async (_: RuleObject, value: string) => {
    if (!value) return Promise.reject('请确认密码');
    if (value !== formData.password) return Promise.reject('两次密码不一致');
    return Promise.resolve();
  };

  const rules = {
    username: [{ required: true, message: '请输入账号', trigger: 'change' }],
    requested_role: [{ required: true, message: '请选择申请身份', trigger: 'change' }],
    password: [{ required: true, message: '请输入密码', trigger: 'change' }],
    confirmPassword: [{ required: true, validator: validateConfirmPassword, trigger: 'change' }],
  };

  async function handleRegister() {
    const form = unref(formRef);
    if (!form) return;
    await form.validate();
    loading.value = true;
    try {
      await registerApi({
        username: formData.username,
        password: formData.password,
        email: formData.email,
        requested_role: formData.requested_role,
      });
      message.success('注册申请已提交，请等待管理员审核');
      router.push('/login');
    } catch (error: any) {
      message.error(error?.response?.data?.message || error?.message || '注册申请提交失败');
    } finally {
      loading.value = false;
    }
  }
</script>

<style lang="less" scoped>
  .register-apply-page {
    position: relative;
    min-width: 100%;
    min-height: 100vh;
    overflow: auto;
    scrollbar-gutter: stable;
    padding: 8px 16px;
    background-color: #071425;
    background-image:
      linear-gradient(90deg, rgba(5, 15, 29, 0.72), rgba(5, 15, 29, 0.16)),
      url('@/assets/images/landing-global-network.png');
    background-repeat: no-repeat;
    background-position: center;
    background-size: cover;
  }

  .register-box {
    display: flex;
    justify-content: flex-end;
    width: min(1140px, 100%);
    min-height: calc(100vh - 16px);
    margin: 0 auto;
    padding: 132px 24px 56px;
  }

  .register-panel {
    width: 480px;
    margin: auto;
    padding: 46px 0;
    border: 1px solid rgba(255, 255, 255, 0.72);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 24px 70px rgba(3, 9, 19, 0.32);
    backdrop-filter: blur(18px);
  }

  .title {
    color: @text-color-main;
    text-align: center;
  }

  .title-main {
    font-size: 16px;
    font-weight: 400;
    line-height: 28px;
  }

  .title-sub {
    margin-top: 6px;
    font-family: Georgia, 'Times New Roman', 'Noto Serif SC', serif;
    font-size: 20px;
    font-weight: 400;
    line-height: 32px;
  }

  .form {
    padding: 32px 80px 0;
  }

  .form-input,
  .submit-btn {
    width: 320px;
    height: 40px;
  }

  .submit-btn {
    margin-top: 4px;
    font-size: 14px;
    font-weight: 400;
  }

  .back-btn {
    width: 320px;
    height: 40px;
    margin-top: 16px;
    border-color: rgba(91, 72, 45, 0.16);
    color: #6f5c43;
    font-size: 14px;
    font-weight: 400;
  }

  .ant-form {
    .ant-form-item-label > label {
      font-size: 14px;
      line-height: 16px;
    }
  }

  :deep(.ant-input),
  :deep(.ant-input-password),
  :deep(.ant-input-password .ant-input),
  :deep(.ant-select-selection-item),
  :deep(.ant-select-selection-placeholder) {
    font-size: 14px;
  }

  @media (max-width: 760px) {
    .register-apply-page {
      padding: 0;
    }

    .register-box {
      justify-content: center;
      padding: 112px 18px 40px;
    }

    .register-panel {
      width: 100%;
      max-width: 420px;
    }

    .form {
      padding-right: 28px;
      padding-left: 28px;
    }

    .form-input,
    .submit-btn,
    .back-btn {
      width: 100%;
    }
  }
</style>
