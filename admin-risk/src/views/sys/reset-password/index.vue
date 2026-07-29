<template>
  <div class="reset-page">
    <div class="reset-panel">
      <div class="title">设置新密码</div>
      <div class="subtitle">使用管理员提供的一次性重置凭证</div>
      <Alert
        type="info"
        show-icon
        message="凭证不会保存在浏览器中"
        description="凭证单次使用并在短时间后失效；提交成功后请使用新密码重新登录。"
      />
      <Form ref="formRef" layout="vertical" :model="formData" class="form">
        <Form.Item label="账号" required>
          <Input v-model:value="formData.username" autocomplete="username" :maxlength="64" />
        </Form.Item>
        <Form.Item label="一次性重置凭证" required>
          <Input.TextArea
            v-model:value="formData.resetTicket"
            :rows="4"
            autocomplete="off"
            :maxlength="512"
          />
        </Form.Item>
        <Form.Item label="新密码" required>
          <Input.Password
            v-model:value="formData.newPassword"
            autocomplete="new-password"
            :maxlength="128"
          />
        </Form.Item>
        <Form.Item label="确认新密码" required>
          <Input.Password
            v-model:value="formData.confirmPassword"
            autocomplete="new-password"
            :maxlength="128"
            @press-enter="submit"
          />
        </Form.Item>
        <p class="hint">密码长度为 12—128 个字符，不能使用常见弱密码或包含完整联系方式。</p>
        <Button type="primary" block :loading="loading" @click="submit">确认设置</Button>
        <Button block class="mt-3" @click="router.push('/login')">返回登录</Button>
      </Form>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Alert, Button, Form, Input, message } from 'ant-design-vue';
  import { resetPasswordWithTicket } from '@/api/platform/userSystem';

  const router = useRouter();
  const formRef = ref();
  const loading = ref(false);
  const formData = reactive({
    username: '',
    resetTicket: '',
    newPassword: '',
    confirmPassword: '',
  });

  async function submit() {
    if (loading.value) return;
    if (!formData.username.trim() || !formData.resetTicket.trim()) {
      message.warning('请输入账号和一次性重置凭证');
      return;
    }
    if (formData.newPassword.length < 12) {
      message.warning('新密码至少需要 12 个字符');
      return;
    }
    if (formData.newPassword !== formData.confirmPassword) {
      message.warning('两次输入的新密码不一致');
      return;
    }
    loading.value = true;
    try {
      await resetPasswordWithTicket({
        username: formData.username.trim(),
        resetTicket: formData.resetTicket.trim(),
        newPassword: formData.newPassword,
        newPasswordConfirmation: formData.confirmPassword,
      });
      formData.resetTicket = '';
      formData.newPassword = '';
      formData.confirmPassword = '';
      message.success('密码设置成功，请重新登录');
      await router.replace('/login');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '密码重置失败');
    } finally {
      loading.value = false;
    }
  }
</script>

<style scoped>
  .reset-page {
    display: flex;
    min-height: 100vh;
    align-items: center;
    justify-content: center;
    padding: 48px 18px;
    background: linear-gradient(145deg, #eef3f8, #f8fafc 56%, #e8eef5);
  }

  .reset-panel {
    width: min(520px, 100%);
    padding: 42px 56px;
    border: 1px solid rgba(203, 213, 225, 0.9);
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 28px 80px rgba(100, 116, 139, 0.16);
  }

  .title {
    color: #0f172a;
    font-size: 26px;
    font-weight: 700;
    text-align: center;
  }

  .subtitle {
    margin: 8px 0 24px;
    color: #64748b;
    text-align: center;
  }

  .form {
    margin-top: 24px;
  }

  .hint {
    margin: -4px 0 18px;
    color: #64748b;
    font-size: 12px;
    line-height: 1.7;
  }

  @media (max-width: 640px) {
    .reset-panel {
      padding: 34px 26px;
    }
  }
</style>
