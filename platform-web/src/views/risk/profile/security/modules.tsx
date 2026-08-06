import type { PropType, Ref } from 'vue';
import type { FormInstance } from 'ant-design-vue/lib/form/Form';
import type { Rule as ValidationRule } from 'ant-design-vue/lib/form/interface';
import { computed, defineComponent, reactive, ref, watch } from 'vue';
import { Form, Input, message, Modal } from 'ant-design-vue';
import { loginChangepw } from '@/api/sys/user';
import { useUserStore } from '@/store/modules/user';
import { validateEmail, validatePassword, validatePhone } from '@/utils/regex';
import {
  buildEmailPayload,
  buildFeishuPayload,
  buildPasswordPayload,
  buildPhonePayload,
  executeWithLoading,
  resetFormWhenClosed,
  type EmailFormValues,
  type FeishuFormValues,
  type PasswordFormValues,
  type PhoneFormValues,
  type SecurityBindingPayload,
} from './contracts';
import { ConfigPropType } from './enums';

const FormItem = Form.Item;
const PasswordInput = Input.Password;
const modalFooterButton = { class: 'w-74px !ml-4' };
const labelCol = { style: { width: '94px' } };

function resetWhenClosed(visible: Ref<boolean>, formRef: Ref<FormInstance | undefined>) {
  watch(visible, (open) => {
    resetFormWhenClosed(open, () => formRef.value?.resetFields());
  });
}

function readString(values: Record<string, unknown>, field: string): string {
  const value = values[field];
  return typeof value === 'string' ? value : '';
}

function isConfigPropType(value: unknown): boolean {
  return value === ConfigPropType.BIND || value === ConfigPropType.CHANGE;
}

export const Password = defineComponent({
  setup(_, { expose }) {
    const userStore = useUserStore();
    const visible = ref(false);
    const formRef = ref<FormInstance>();
    const confirmLoading = ref(false);
    const formState = reactive<PasswordFormValues>({
      oldPw: '',
      newPw1: '',
      newPw2: '',
      code: '',
    });
    const rules: Record<string, ValidationRule[]> = {
      oldPw: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
      newPw1: [
        {
          required: true,
          trigger: 'blur',
          validator: (_rule, value: unknown) => {
            const password = typeof value === 'string' ? value : '';
            return validatePassword(password)
              ? Promise.resolve()
              : Promise.reject('密码由8-16位数字、字母或符号组成');
          },
        },
      ],
      newPw2: [
        {
          required: true,
          trigger: 'blur',
          validator: (_rule, value: unknown) => {
            const password = typeof value === 'string' ? value : '';
            return password && password === formState.newPw1
              ? Promise.resolve()
              : Promise.reject('两次输入密码不一致');
          },
        },
      ],
      code: [{ required: true, message: '请输入谷歌验证码', trigger: 'blur' }],
    };

    resetWhenClosed(visible, formRef);

    async function handleOk() {
      if (!formRef.value) return;
      const values = (await formRef.value.validateFields()) as Record<string, unknown>;
      const payload = buildPasswordPayload({
        oldPw: readString(values, 'oldPw'),
        newPw1: readString(values, 'newPw1'),
        newPw2: readString(values, 'newPw2'),
        code: readString(values, 'code'),
      });

      await executeWithLoading(
        (loading) => {
          confirmLoading.value = loading;
        },
        async () => {
          await loginChangepw(payload);
          visible.value = false;
          message.warning({
            content: '密码修改成功，请重新登录',
            duration: 3,
            onClose: () => userStore.logout(true),
          });
        },
      );
    }

    function handleCancel() {
      visible.value = false;
    }

    expose({ visible, confirmLoading });
    return () => (
      <Modal
        open={visible.value}
        width={574}
        class="modal-white-bg"
        okButtonProps={modalFooterButton}
        cancelButtonProps={modalFooterButton}
        confirmLoading={confirmLoading.value}
        onOk={handleOk}
        onCancel={handleCancel}
      >
        {{
          title: () => <div class="font-500">修改密码</div>,
          default: () => (
            <Form
              ref={formRef}
              model={formState}
              rules={rules}
              labelCol={labelCol}
              hideRequiredMark
              validateFirst
              class="mt-8 mb-12 px-6"
            >
              <FormItem name="oldPw" label="旧密码">
                <PasswordInput v-model:value={formState.oldPw} placeholder="请输入旧密码" />
              </FormItem>
              <FormItem name="newPw1" label="新密码">
                <PasswordInput v-model:value={formState.newPw1} placeholder="请输入新密码" />
              </FormItem>
              <FormItem name="newPw2" label="重复新密码">
                <PasswordInput
                  v-model:value={formState.newPw2}
                  placeholder="请再次输入新密码"
                />
              </FormItem>
              <FormItem name="code" label="谷歌验证码">
                <Input v-model:value={formState.code} placeholder="请输入验证码" />
              </FormItem>
            </Form>
          ),
        }}
      </Modal>
    );
  },
});

type BindingField = 'newPhone' | 'newEmail' | 'url';
type BindingAction = 'phone' | 'email' | 'feishu';

type BindingFormState = PhoneFormValues & EmailFormValues & FeishuFormValues;

interface BindingComponentConfig {
  action: BindingAction;
  field: BindingField;
  titleMap: Record<ConfigPropType, string>;
  labelMap: Record<ConfigPropType, string>;
  validator?: (value: string) => boolean;
}

function createBindingComponent(config: BindingComponentConfig) {
  return defineComponent({
    props: {
      type: {
        type: Number as PropType<ConfigPropType>,
        validator: isConfigPropType,
        default: ConfigPropType.BIND,
      },
    },
    emits: {
      submit: (_payload: SecurityBindingPayload) => true,
    },
    setup(props, { emit, expose }) {
      const visible = ref(false);
      const formRef = ref<FormInstance>();
      const confirmLoading = ref(false);
      const formState = reactive<BindingFormState>({
        newPhone: '',
        newEmail: '',
        url: '',
        code: '',
      });
      const title = computed(() => config.titleMap[props.type]);
      const label = computed(() => config.labelMap[props.type]);
      const rules = computed<Record<string, ValidationRule[]>>(() => ({
        [config.field]: [
          {
            required: true,
            trigger: 'blur',
            validator: (_rule, value: unknown) => {
              const fieldValue = typeof value === 'string' ? value : '';
              return fieldValue && (!config.validator || config.validator(fieldValue))
                ? Promise.resolve()
                : Promise.reject(`请输入正确的${label.value}`);
            },
          },
        ],
        code: [{ required: true, message: '请输入谷歌验证码', trigger: 'blur' }],
      }));

      resetWhenClosed(visible, formRef);

      function buildPayload(values: Record<string, unknown>): SecurityBindingPayload {
        const code = readString(values, 'code');
        if (config.action === 'phone') {
          return buildPhonePayload(props.type, {
            newPhone: readString(values, 'newPhone'),
            code,
          });
        }
        if (config.action === 'email') {
          return buildEmailPayload(props.type, {
            newEmail: readString(values, 'newEmail'),
            code,
          });
        }
        return buildFeishuPayload(props.type, {
          url: readString(values, 'url'),
          code,
        });
      }

      async function handleOk() {
        if (!formRef.value) return;
        const values = (await formRef.value.validateFields()) as Record<string, unknown>;
        const payload = buildPayload(values);
        await executeWithLoading(
          (loading) => {
            confirmLoading.value = loading;
          },
          () => emit('submit', payload),
        );
      }

      function handleCancel() {
        visible.value = false;
      }

      expose({ visible, confirmLoading });
      return () => (
        <Modal
          open={visible.value}
          width={574}
          class="modal-white-bg"
          okButtonProps={modalFooterButton}
          cancelButtonProps={modalFooterButton}
          confirmLoading={confirmLoading.value}
          onOk={handleOk}
          onCancel={handleCancel}
        >
          {{
            title: () => <div class="font-500">{title.value}</div>,
            default: () => (
              <Form
                ref={formRef}
                model={formState}
                rules={rules.value}
                labelCol={labelCol}
                hideRequiredMark
                class="mt-8 mb-12 px-6"
              >
                <FormItem name={config.field} label={label.value}>
                  <Input
                    v-model:value={formState[config.field]}
                    placeholder={`请输入${label.value}`}
                  />
                </FormItem>
                <FormItem name="code" label="谷歌验证码">
                  <Input v-model:value={formState.code} placeholder="请输入验证码" />
                </FormItem>
              </Form>
            ),
          }}
        </Modal>
      );
    },
  });
}

export const Phone = createBindingComponent({
  action: 'phone',
  field: 'newPhone',
  titleMap: {
    [ConfigPropType.BIND]: '绑定手机号',
    [ConfigPropType.CHANGE]: '更换手机号码',
  },
  labelMap: {
    [ConfigPropType.BIND]: '手机号码',
    [ConfigPropType.CHANGE]: '新手机号码',
  },
  validator: validatePhone,
});

export const Email = createBindingComponent({
  action: 'email',
  field: 'newEmail',
  titleMap: {
    [ConfigPropType.BIND]: '绑定邮箱',
    [ConfigPropType.CHANGE]: '更换邮箱',
  },
  labelMap: {
    [ConfigPropType.BIND]: '邮箱',
    [ConfigPropType.CHANGE]: '新邮箱',
  },
  validator: validateEmail,
});

export const Feishu = createBindingComponent({
  action: 'feishu',
  field: 'url',
  titleMap: {
    [ConfigPropType.BIND]: '绑定飞书',
    [ConfigPropType.CHANGE]: '更换飞书',
  },
  labelMap: {
    [ConfigPropType.BIND]: '飞书地址',
    [ConfigPropType.CHANGE]: '新飞书地址',
  },
});
