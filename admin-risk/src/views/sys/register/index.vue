<template>
  <div class="register-apply-page">
    <div class="register-box">
      <div class="register-panel">
        <div class="title title-main">注册申请</div>
        <div class="title title-sub">全球变量金融平台</div>
        <div class="form-note">申请提交后需要审核，审核通过前不能登录。</div>

        <Form
          ref="formRef"
          layout="vertical"
          class="form"
          :model="formData"
          :rules="rules"
          @keypress.enter="handleRegister"
        >
          <div class="form-grid">
            <FormItem name="username" label="账号">
              <Input
                v-model:value="formData.username"
                placeholder="3—64 个字符"
                autocomplete="username"
              />
            </FormItem>
            <FormItem name="realName" label="姓名">
              <Input
                v-model:value="formData.realName"
                placeholder="请输入姓名"
                autocomplete="name"
              />
            </FormItem>
            <FormItem name="email" label="邮箱">
              <Input
                v-model:value="formData.email"
                placeholder="邮箱或手机号至少填写一项"
                autocomplete="email"
              />
            </FormItem>
            <FormItem name="phone" label="手机号">
              <Input
                v-model:value="formData.phone"
                placeholder="邮箱或手机号至少填写一项"
                autocomplete="tel"
              />
            </FormItem>
            <FormItem name="requestedRole" label="申请身份">
              <Select v-model:value="formData.requestedRole" :options="roleOptions" />
            </FormItem>
            <FormItem v-if="formData.requestedRole === 'employee'" name="department" label="部门">
              <Input v-model:value="formData.department" placeholder="请输入部门" />
            </FormItem>
            <FormItem v-else name="memberType" label="会员类型">
              <Select v-model:value="formData.memberType" :options="memberTypeOptions" />
            </FormItem>
            <FormItem name="password" label="密码">
              <Input.Password
                v-model:value="formData.password"
                visibilityToggle
                placeholder="至少 12 个字符"
                autocomplete="new-password"
              />
            </FormItem>
            <FormItem name="passwordConfirmation" label="确认密码">
              <Input.Password
                v-model:value="formData.passwordConfirmation"
                visibilityToggle
                placeholder="请再次输入密码"
                autocomplete="new-password"
              />
            </FormItem>
          </div>

          <FormItem name="applicationNote" label="申请说明">
            <Input.TextArea
              v-model:value="formData.applicationNote"
              :maxlength="1000"
              :rows="3"
              show-count
              placeholder="请简要说明申请用途"
            />
          </FormItem>

          <FormItem name="privacyAccepted" class="privacy-item">
            <Checkbox v-model:checked="formData.privacyAccepted">
              我确认填写内容真实，并同意平台按账号审核和安全需要处理上述信息
            </Checkbox>
          </FormItem>

          <Button
            type="primary"
            block
            class="submit-btn"
            html-type="button"
            :loading="loading"
            @click="handleRegister"
          >
            提交申请
          </Button>
          <Button block class="back-btn" html-type="button" @click="router.push('/login')">
            返回登录
          </Button>
        </Form>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref, unref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Button, Checkbox, Form, Input, message, Select } from 'ant-design-vue';
  import type { RuleObject } from 'ant-design-vue/lib/form/interface';
  import {
    registerUser,
    UserSystemApiError,
    type PublicRegistrationRole,
  } from '@/api/platform/userSystem';

  const FormItem = Form.Item;
  const router = useRouter();
  const formRef = ref();
  const loading = ref(false);

  const formData = reactive({
    username: '',
    realName: '',
    email: '',
    phone: '',
    requestedRole: 'member' as PublicRegistrationRole,
    department: '',
    memberType: 'individual',
    applicationNote: '',
    password: '',
    passwordConfirmation: '',
    privacyAccepted: false,
  });

  const roleOptions = [
    { label: '会员', value: 'member' },
    { label: '员工', value: 'employee' },
  ];
  const memberTypeOptions = [
    { label: '个人会员', value: 'individual' },
    { label: '机构会员', value: 'institutional' },
  ];

  const validateContact = async () => {
    if (!formData.email.trim() && !formData.phone.trim()) {
      return Promise.reject('邮箱或手机号至少填写一项');
    }
    return Promise.resolve();
  };
  const validateConfirmation = async (_: RuleObject, value: string) => {
    if (!value) return Promise.reject('请确认密码');
    if (value !== formData.password) return Promise.reject('两次密码不一致');
    return Promise.resolve();
  };
  const validateRoleDetail = async () => {
    if (formData.requestedRole === 'employee' && !formData.department.trim()) {
      return Promise.reject('员工申请必须填写部门');
    }
    if (formData.requestedRole === 'member' && !formData.memberType) {
      return Promise.reject('会员申请必须选择会员类型');
    }
    return Promise.resolve();
  };

  const rules = {
    username: [
      { required: true, message: '请输入账号', trigger: 'change' },
      { min: 3, max: 64, message: '账号长度为 3—64 个字符', trigger: 'change' },
    ],
    realName: [{ required: true, message: '请输入姓名', trigger: 'change' }],
    email: [{ validator: validateContact, trigger: 'change' }],
    phone: [{ validator: validateContact, trigger: 'change' }],
    requestedRole: [{ required: true, message: '请选择申请身份', trigger: 'change' }],
    department: [{ validator: validateRoleDetail, trigger: 'change' }],
    memberType: [{ validator: validateRoleDetail, trigger: 'change' }],
    password: [
      { required: true, message: '请输入密码', trigger: 'change' },
      { min: 12, max: 128, message: '密码长度为 12—128 个字符', trigger: 'change' },
    ],
    passwordConfirmation: [{ required: true, validator: validateConfirmation, trigger: 'change' }],
    privacyAccepted: [
      {
        validator: async () =>
          formData.privacyAccepted ? Promise.resolve() : Promise.reject('请确认信息处理说明'),
        trigger: 'change',
      },
    ],
  };

  async function handleRegister() {
    const form = unref(formRef);
    if (!form || loading.value) return;
    await form.validate();
    loading.value = true;
    try {
      const result = await registerUser({
        username: formData.username.trim(),
        realName: formData.realName.trim(),
        email: formData.email.trim() || undefined,
        phone: formData.phone.trim() || undefined,
        requestedRole: formData.requestedRole,
        department: formData.requestedRole === 'employee' ? formData.department.trim() : undefined,
        memberType: formData.requestedRole === 'member' ? formData.memberType : undefined,
        applicationNote: formData.applicationNote.trim() || undefined,
        password: formData.password,
        passwordConfirmation: formData.passwordConfirmation,
        privacyAccepted: formData.privacyAccepted,
      });
      message.success(result.message);
      await router.push('/login');
    } catch (error) {
      const known = error instanceof UserSystemApiError ? error : null;
      const text =
        known?.code === 'registration_conflict'
          ? '账号、邮箱或手机号已被使用'
          : known?.message || '注册申请提交失败';
      message.error(text);
    } finally {
      loading.value = false;
    }
  }
</script>

<style lang="less" scoped>
  .register-apply-page {
    min-width: 100%;
    min-height: 100vh;
    overflow: auto;
    padding: 48px 18px;
    background: radial-gradient(circle at 20% 18%, rgba(191, 219, 254, 0.48), transparent 34%),
      radial-gradient(circle at 82% 75%, rgba(226, 232, 240, 0.75), transparent 38%),
      linear-gradient(145deg, #eef4f8 0%, #f8fafc 55%, #e8eef3 100%);
  }

  .register-box {
    display: flex;
    justify-content: center;
    width: min(1140px, 100%);
    min-height: calc(100vh - 96px);
    margin: 0 auto;
  }

  .register-panel {
    width: min(760px, 100%);
    margin: auto;
    padding: 42px 52px;
    border: 1px solid rgba(203, 213, 225, 0.92);
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.95);
    box-shadow: 0 28px 85px rgba(100, 116, 139, 0.16);
    backdrop-filter: blur(18px);
  }

  .title {
    color: #0f172a;
    text-align: center;
  }

  .title-main {
    font-size: 18px;
  }

  .title-sub {
    margin-top: 6px;
    font-family: Georgia, 'Times New Roman', 'Noto Serif SC', serif;
    font-size: 25px;
  }

  .form-note {
    margin: 12px 0 28px;
    color: #64748b;
    font-size: 13px;
    text-align: center;
  }

  .form-grid {
    display: grid;
    gap: 0 20px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .privacy-item {
    margin-top: 6px;
  }

  .submit-btn,
  .back-btn {
    height: 44px;
    border-radius: 11px;
  }

  .back-btn {
    margin-top: 12px;
    color: #475569;
  }

  :deep(.ant-input),
  :deep(.ant-input-affix-wrapper),
  :deep(.ant-select-selector) {
    min-height: 42px;
    border-radius: 10px !important;
  }

  @media (max-width: 760px) {
    .register-apply-page {
      padding: 24px 12px;
    }

    .register-panel {
      padding: 32px 24px;
    }

    .form-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
