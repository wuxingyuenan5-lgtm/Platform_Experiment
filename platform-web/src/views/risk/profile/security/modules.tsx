import { computed, defineComponent, reactive, ref, watch } from 'vue';
import { Form, Input, message, Modal } from 'ant-design-vue';
import { loginChangepw } from '@/api/sys/user';
import { useApiBasic } from '@/hooks/web/useApi';
import { useUserStore } from '@/store/modules/user';
import { validateEmail, validatePassword, validatePhone } from '@/utils/regex';
import { ConfigPropType } from './enums';

const modalFooterButton = { class: 'w-74px !ml-4' };
const labelCol = { style: { width: '94px' } };

function resetWhenClosed(visible: ReturnType<typeof ref<boolean>>, formRef: ReturnType<typeof ref>) {
  watch(visible, (open) => {
    if (!open) formRef.value?.resetFields();
  });
}

export const Password = defineComponent({
  setup(_, { expose }) {
    const userStore = useUserStore();
    const visible = ref(false);
    const formRef = ref();
    const confirmLoading = ref(false);
    const formState = reactive({ oldPw: '', newPw1: '', newPw2: '', code: '' });
    const rules = {
      newPw1: [
        {
          required: true,
          trigger: 'blur',
          validator: (_rule: unknown, value: string) =>
            validatePassword(value)
              ? Promise.resolve()
              : Promise.reject('密码由8-16位数字、字母或符号组成'),
        },
      ],
      newPw2: [
        {
          required: true,
          trigger: 'blur',
          validator: (_rule: unknown, value: string) =>
            value && value === formState.newPw1
              ? Promise.resolve()
              : Promise.reject('两次输入密码不一致'),
        },
      ],
    };

    resetWhenClosed(visible, formRef);

    async function handleOk() {
      const values = await formRef.value.validate();
      confirmLoading.value = true;
      useApiBasic({
        apiFn: loginChangepw(values) as any,
        successFn: () => {
          visible.value = false;
          message.warning({
            content: '密码修改成功，请重新登录',
            duration: 3,
            onClose: () => userStore.logout(true),
          });
        },
        finallyFn: () => {
          confirmLoading.value = false;
        },
      });
    }

    expose({ visible, confirmLoading });
    return () => (
      <Modal
        v-model:open={visible.value}
        width={574}
        class="modal-white-bg"
        okButtonProps={modalFooterButton}
        cancelButtonProps={modalFooterButton}
        confirmLoading={confirmLoading.value}
        onOk={handleOk}
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
              <Form.Item name="oldPw" label="旧密码">
                <Input.Password v-model:value={formState.oldPw} placeholder="请输入旧密码" />
              </Form.Item>
              <Form.Item name="newPw1" label="新密码">
                <Input.Password v-model:value={formState.newPw1} placeholder="请输入新密码" />
              </Form.Item>
              <Form.Item name="newPw2" label="重复新密码">
                <Input.Password v-model:value={formState.newPw2} placeholder="请再次输入新密码" />
              </Form.Item>
              <Form.Item name="code" label="谷歌验证码">
                <Input v-model:value={formState.code} placeholder="请输入验证码" />
              </Form.Item>
            </Form>
          ),
        }}
      </Modal>
    );
  },
});

function createBindingComponent(
  titleMap: Record<ConfigPropType, string>,
  field: 'newPhone' | 'url' | 'newEmail',
  labelMap: Record<ConfigPropType, string>,
  validator?: (value: string) => boolean,
) {
  return defineComponent({
    props: {
      type: {
        type: String as PropType<ConfigPropType>,
        validator: (value: string) => Object.values(ConfigPropType).includes(value as ConfigPropType),
        default: ConfigPropType.BIND,
      },
    },
    emits: ['submit'],
    setup(props, { emit, expose }) {
      const visible = ref(false);
      const formRef = ref();
      const confirmLoading = ref(false);
      const formState = reactive<Record<string, string>>({ [field]: '', code: '' });
      const title = computed(() => titleMap[props.type]);
      const label = computed(() => labelMap[props.type]);
      const rules = {
        [field]: [
          {
            required: true,
            trigger: 'blur',
            validator: (_rule: unknown, value: string) =>
              !validator || validator(value)
                ? Promise.resolve()
                : Promise.reject(`请输入正确的${label.value}`),
          },
        ],
        code: [{ required: true, message: '请输入谷歌验证码', trigger: 'blur' }],
      };

      resetWhenClosed(visible, formRef);

      async function handleOk() {
        const values = await formRef.value.validate();
        confirmLoading.value = true;
        emit('submit', values);
      }

      expose({ visible, confirmLoading });
      return () => (
        <Modal
          v-model:open={visible.value}
          width={574}
          class="modal-white-bg"
          okButtonProps={modalFooterButton}
          cancelButtonProps={modalFooterButton}
          confirmLoading={confirmLoading.value}
          onOk={handleOk}
        >
          {{
            title: () => <div class="font-500">{title.value}</div>,
            default: () => (
              <Form
                ref={formRef}
                model={formState}
                rules={rules}
                labelCol={labelCol}
                hideRequiredMark
                class="mt-8 mb-12 px-6"
              >
                <Form.Item name={field} label={label.value}>
                  <Input v-model:value={formState[field]} placeholder={`请输入${label.value}`} />
                </Form.Item>
                <Form.Item name="code" label="谷歌验证码">
                  <Input v-model:value={formState.code} placeholder="请输入验证码" />
                </Form.Item>
              </Form>
            ),
          }}
        </Modal>
      );
    },
  });
}

export const Phone = createBindingComponent(
  { [ConfigPropType.BIND]: '绑定手机号', [ConfigPropType.CHANGE]: '更换手机号码' },
  'newPhone',
  { [ConfigPropType.BIND]: '手机号码', [ConfigPropType.CHANGE]: '新手机号码' },
  validatePhone,
);

export const Feishu = createBindingComponent(
  { [ConfigPropType.BIND]: '绑定飞书', [ConfigPropType.CHANGE]: '更换飞书' },
  'url',
  { [ConfigPropType.BIND]: '飞书地址', [ConfigPropType.CHANGE]: '新飞书地址' },
);

export const Email = createBindingComponent(
  { [ConfigPropType.BIND]: '绑定邮箱', [ConfigPropType.CHANGE]: '更换邮箱' },
  'newEmail',
  { [ConfigPropType.BIND]: '邮箱', [ConfigPropType.CHANGE]: '新邮箱' },
  validateEmail,
);
