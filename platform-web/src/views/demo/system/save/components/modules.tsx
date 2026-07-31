import { defineComponent, ref, reactive, watch, computed } from 'vue';
import { useUserStore } from '@/store/modules/user';
import { useCode } from '@/hooks/web/useCode';
import { validatePassword, validatePhone, validateEmail } from '@/utils/regex';
import { useInterval } from '@vueuse/core';
import { useApiBasic } from '@/hooks/web/useApi';
import { Modal, Upload, message, Form, Input, Tabs, TabPane, Button } from 'ant-design-vue';
import { loginChangepw } from '@/api/sys/user';
import { ConfigPropType } from '../enums';

const modalFooterBtn: any = {
  class: 'w-74px !ml-4',
};
const modalFooterBtn1: any = {
  class: 'w-74px !ml-4',
};
const labelCol = {
  style: {
    width: '94px',
  },
};
// 修改密码
export const Password = defineComponent({
  emits: ['submit'],
  setup(props, { expose, emit }) {
    const userStore = useUserStore();
    const visible = ref(false);
    const formRef = ref();

    const { getCode, counterMsg, count } = useCode({ phone: '' });

    const formState = reactive({
      oldPw: '',
      newPw1: '',
      newPw2: '',
      code: '',
    });
    const confirmLoading = ref(false);

    function handleOk(params: any) {
      //   console.log(params)
      formRef.value.validate().then((res: any) => {
        confirmLoading.value = true;
        // emit('submit', { ...res, action: 'changePassword' })
        changePasswordFn(res);
      });
    }
    const rules = {
      code: [
        {
          required: false,
          message: '请输入验证码',
          trigger: 'blur',
        },
      ],
      newPw1: [
        {
          required: true,
          message: '请输入新密码',
          trigger: 'blur',
          validator: (rule: any, value: any) => {
            if (value === '') {
              return Promise.reject('密码不能为空');
            } else {
              if (!validatePassword(value)) {
                return Promise.reject('密码由8-16位数字、字母或符号组成');
              }
              return Promise.resolve();
            }
          },
        },
      ],
      newPw2: [
        {
          required: true,
          trigger: 'blur',
          validator: (rule: any, value: any) => {
            if (value === '') {
              return Promise.reject('两次输入密码不一致');
            } else if (value !== formState.newPw1) {
              return Promise.reject('两次输入密码不一致');
            } else {
              return Promise.resolve();
            }
          },
        },
      ],
    };
    watch(
      () => visible.value,
      (newValue, oldValue) => {
        if (!newValue) {
          formRef.value?.resetFields();
        }
      },
    );
    function changePasswordFn(params: any) {
      const { counter } = useInterval(1000, { controls: true });
      useApiBasic({
        apiFn: loginChangepw(params) as any,
        successFn: (data: any) => {
          visible.value = false;
          message.warning({
            content: () => `请勿操作，${5 - counter.value > 0 ? 5 - counter.value : 0}秒后自动退出`,
            key: 'Changepw',
            duration: 5,
            onClose: () => {
              userStore.logout(true);
            },
          });
        },
      });
    }

    expose({
      visible,
      confirmLoading,
    });
    return () => {
      return (
        <Modal
          okButtonProps={modalFooterBtn}
          cancelButtonProps={modalFooterBtn1}
          onOk={handleOk}
          width={574}
          class="modal-white-bg"
          v-model:open={visible.value}
        >
          {{
            title: () => <div class="font-500">修改密码</div>,
            default: () => (
              <Form
                hideRequiredMark={true}
                validateFirst={true}
                ref={formRef}
                labelCol={labelCol}
                model={formState}
                rules={rules}
                class="mt-8 mb-12 px-6"
              >
                <Form.Item name="oldPw" label="旧密码">
                  {{
                    default: () => (
                      <Input.Password
                        v-model:value={formState.oldPw}
                        placeholder="请输入旧密码"
                      ></Input.Password>
                    ),
                  }}
                </Form.Item>
                <Form.Item name="newPw1" label="新密码">
                  {{
                    default: () => (
                      <Input.Password
                        v-model:value={formState.newPw1}
                        placeholder="请输入新密码"
                      ></Input.Password>
                    ),
                    help: () => <div class="font-h8">密码由8-16位数字、字母或符号组成</div>,
                  }}
                </Form.Item>
                <Form.Item name="newPw2" label="重复新密码">
                  <Input.Password
                    v-model:value={formState.newPw2}
                    placeholder="请输入新密码"
                  ></Input.Password>
                </Form.Item>
                <Form.Item name="code" label="谷歌验证码">
                  <Input.Group compact>
                    <Input v-model:value={formState.code} placeholder="请输入验证码"></Input>
                    {/* <Button
                      disabled={counterMsg.value != count}
                      onClick={getCode}
                      class="w-30 text-center !px-0"
                    >
                      {counterMsg.value != count ? counterMsg.value + '秒后重新获取' : '获取验证码'}
                    </Button> */}
                  </Input.Group>
                </Form.Item>
              </Form>
            ),
          }}
        </Modal>
      );
    };
  },
});

// 手机号
export const Phone = defineComponent({
  props: {
    type: {
      type: String as unknown as PropType<ConfigPropType>,
      validator: (value: string) => Object.values(ConfigPropType).includes(value),
      default: ConfigPropType.BIND,
    },
  },
  emits: ['submit'],
  setup(props, { expose, emit }) {
    const userStore = useUserStore();
    const userInfo = userStore.getUserInfo;
    const visible = ref(false);
    const formRef = ref();
    const formState = reactive({
      password: '',
      phone: '',
      phoneOld: '',
      newPhone: '',
      code: '',
      codeOld: '',
    });
    const confirmLoading = ref(false);
    const title = computed(() => {
      return props.type === ConfigPropType.BIND ? '绑定手机号' : '更换手机号码';
    });

    function handleOk(params: any) {
      //   console.log(params)
      formRef.value.validate().then((res: any) => {
        confirmLoading.value = true;
        emit('submit', { ...res, action: 'phone' });
      });
    }
    const rules = {
      code: [
        {
          required: true,
          message: '请输入验证码',
          trigger: 'blur',
        },
      ],
      newPhone: [
        {
          required: true,
          trigger: 'blur',
          validator: (rule: any, value: any) => {
            if (value) {
              if (!validatePhone(value)) {
                return Promise.reject('请输入正确的手机号');
              }
              return Promise.resolve();
            } else {
              return Promise.reject('请输入手机号');
            }
          },
        },
      ],
      password: [
        {
          required: true,
          message: '请输入密码',
          trigger: 'blur',
        },
      ],
    };
    watch(
      () => visible.value,
      (newValue, oldValue) => {
        if (!newValue) {
          formRef.value?.resetFields();
        }
      },
    );

    // 倒计时
    const {
      getCode: getCodeOld,
      counterMsg: counterMsgOld,
      count: countOld,
    } = useCode({ phone: '' });
    const { getCode, counterMsg, count } = useCode({ phone: '' });

    expose({
      visible,
      confirmLoading,
    });
    return () => {
      const _label = props.type === ConfigPropType.BIND ? '手机号码' : '新手机号码';

      return (
        <Modal
          okButtonProps={modalFooterBtn}
          cancelButtonProps={modalFooterBtn1}
          onOk={handleOk}
          width={574}
          class="modal-white-bg"
          v-model:open={visible.value}
        >
          {{
            title: () => <div class="font-500">{title.value}</div>,
            default: () => (
              <Form
                hideRequiredMark={true}
                ref={formRef}
                labelCol={labelCol}
                model={formState}
                rules={rules}
                class="mt-8 mb-12 px-6"
              >
                {/* {props.type === ConfigPropType.CHANGE && (
                  <Form.Item name="code" label="原手机验证码">
                    {{
                      default: () => (
                        <Input.Group compact>
                          <Input
                            v-model:value={formState.codeOld}
                            style="width: calc(100% - 120px)"
                            placeholder="请输入验证码"
                          ></Input>
                          <Button
                            disabled={counterMsgOld.value != countOld}
                            onClick={getCode}
                            class="w-30 text-center !px-0"
                          >
                            {counterMsgOld.value != countOld
                              ? counterMsgOld.value + '秒后重新获取'
                              : '获取验证码'}
                          </Button>
                        </Input.Group>
                      ),
                      extra: () => userInfo.phone,
                    }}
                  </Form.Item>
                )} */}
                <Form.Item name="newPhone" label={_label}>
                  <Input v-model:value={formState.newPhone} placeholder={'请输入' + _label}></Input>
                </Form.Item>
                <Form.Item name="code" label="谷歌验证码">
                  <Input v-model:value={formState.code} placeholder="请输入验证码"></Input>
                </Form.Item>
                {/* <Form.Item name="phone" label={_label}>
                  <Input v-model:value={formState.phone} placeholder={'请输入' + _label}></Input>
                </Form.Item>
                <Form.Item name="code" label="短信验证码">
                  <Input.Group compact>
                    <Input
                      v-model:value={formState.code}
                      style="width: calc(100% - 120px)"
                      placeholder="请输入验证码"
                    ></Input>
                    <Button
                      disabled={!validatePhone(formState.phone) || counterMsg.value != count}
                      onClick={getCode}
                      class="w-30 text-center !px-0"
                    >
                      {counterMsg.value != count ? counterMsg.value + '秒后重新获取' : '获取验证码'}
                    </Button>
                  </Input.Group>
                </Form.Item> */}
              </Form>
            ),
          }}
        </Modal>
      );
    };
  },
});

// 飞书
export const Feishu = defineComponent({
  props: {
    type: {
      type: String as unknown as PropType<ConfigPropType>,
      validator: (value: string) => Object.values(ConfigPropType).includes(value),
      default: ConfigPropType.BIND,
    },
  },
  emits: ['submit'],
  setup(props, { expose, emit }) {
    const visible = ref(false);
    const formRef = ref();
    const formState = reactive({
      password: '',
      url: '',
      code: '',
    });
    const confirmLoading = ref(false);
    const title = computed(() => {
      return props.type === ConfigPropType.BIND ? '绑定飞书' : '更换飞书';
    });

    function handleOk(params: any) {
      //   console.log(params)
      formRef.value.validate().then((res: any) => {
        confirmLoading.value = true;
        emit('submit', { ...res, action: 'changePassword' });
      });
    }
    const rules = {
      code: [
        {
          required: true,
          message: '请输入验证码',
          trigger: 'blur',
        },
      ],
      url: [
        {
          required: true,
          message: '请输入飞书地址',
          trigger: 'blur',
        },
      ],
    };
    watch(
      () => visible.value,
      (newValue, oldValue) => {
        if (!newValue) {
          formRef.value?.resetFields();
        }
      },
    );

    // 倒计时
    const _count = 60;
    const counterMsg = ref(_count);
    const { resume, pause } = useInterval(1000, {
      controls: true,
      immediate: false,
      callback: (count: number) => {
        counterMsg.value--;
        if (counterMsg.value < 0) {
          counterMsg.value = _count;
          pause();
        }
      },
    });
    // 获取短信验证码
    function getCode() {
      counterMsg.value--;
      resume();
    }

    expose({
      visible,
      confirmLoading,
    });
    return () => {
      const _label = props.type === ConfigPropType.BIND ? '飞书地址' : '新飞书地址';
      return (
        <Modal
          okButtonProps={modalFooterBtn}
          cancelButtonProps={modalFooterBtn1}
          onOk={handleOk}
          width={574}
          class="modal-white-bg"
          v-model:open={visible.value}
        >
          {{
            title: () => <div class="font-500">{title.value}</div>,
            default: () => (
              <Form
                hideRequiredMark={true}
                ref={formRef}
                labelCol={labelCol}
                model={formState}
                rules={rules}
                class="mt-8 mb-12 px-6"
              >
                <Form.Item name="email" label={_label}>
                  <Input v-model:value={formState.url} placeholder={`请输入${_label}`}></Input>
                </Form.Item>
                <Form.Item name="code" label="谷歌验证码">
                  <Input v-model:value={formState.code} placeholder="请输入验证码"></Input>
                </Form.Item>
              </Form>
            ),
          }}
        </Modal>
      );
    };
  },
});

// 邮箱
export const Email = defineComponent({
  props: {
    type: {
      type: String as unknown as PropType<ConfigPropType>,
      validator: (value: string) => Object.values(ConfigPropType).includes(value),
      default: ConfigPropType.BIND,
    },
  },
  emits: ['submit'],
  setup(props, { expose, emit }) {
    const visible = ref(false);
    const formRef = ref();
    const formState = reactive({
      newEmail: '',
      code: '',
    });
    const confirmLoading = ref(false);
    const title = computed(() => {
      return props.type === ConfigPropType.BIND ? '绑定邮箱' : '更换邮箱';
    });

    function handleOk(params: any) {
      //   console.log(params)
      formRef.value.validate().then((res: any) => {
        confirmLoading.value = true;
        emit('submit', { ...res, action: 'email' });
      });
    }
    const rules = {
      code: [
        {
          required: true,
          message: '请输入验证码',
          trigger: 'blur',
        },
      ],
      newEmail: [
        {
          required: true,
          message: '请输入邮箱',
          trigger: 'blur',
        },
      ],
    };
    watch(
      () => visible.value,
      (newValue, oldValue) => {
        if (!newValue) {
          formRef.value?.resetFields();
        }
      },
    );

    // 倒计时
    const _count = 60;
    const counterMsg = ref(_count);
    const { resume, pause } = useInterval(1000, {
      controls: true,
      immediate: false,
      callback: (count: number) => {
        counterMsg.value--;
        if (counterMsg.value < 0) {
          counterMsg.value = _count;
          pause();
        }
      },
    });
    // 获取短信验证码
    function getCode() {
      counterMsg.value--;
      resume();
    }

    expose({
      visible,
      confirmLoading,
    });
    return () => {
      const _label = props.type === ConfigPropType.BIND ? '邮箱' : '新邮箱';
      return (
        <Modal
          okButtonProps={modalFooterBtn}
          cancelButtonProps={modalFooterBtn1}
          onOk={handleOk}
          width={574}
          class="modal-white-bg"
          v-model:open={visible.value}
        >
          {{
            title: () => <div class="font-500">{title.value}</div>,
            default: () => (
              <Form
                hideRequiredMark={true}
                ref={formRef}
                labelCol={labelCol}
                model={formState}
                rules={rules}
                class="mt-8 mb-12 px-6"
              >
                {/* <Form.Item name="password" label="登录密码">
                  <Input.Password
                    v-model:value={formState.password}
                    placeholder="请输入登录密码"
                    autocomplete="new-password"
                  ></Input.Password>
                </Form.Item> */}
                <Form.Item name="newEmail" label={_label}>
                  <Input v-model:value={formState.newEmail} placeholder={`请输入${_label}`}></Input>
                </Form.Item>
                <Form.Item name="code" label="谷歌验证码">
                  <Input v-model:value={formState.code} placeholder="请输入验证码"></Input>
                </Form.Item>
                {/* <Form.Item name="code" label="邮箱验证码">
                  <Input.Group compact>
                    <Input
                      v-model:value={formState.code}
                      style="width: calc(100% - 120px)"
                      placeholder="请输入验证码"
                    ></Input>
                    <Button
                      disabled={!validateEmail(formState.email) || counterMsg.value != _count}
                      onClick={getCode}
                      class="w-30 text-center !px-0"
                    >
                      {counterMsg.value != _count
                        ? counterMsg.value + '秒后重新获取'
                        : '获取验证码'}
                    </Button>
                  </Input.Group>
                </Form.Item> */}
              </Form>
            ),
          }}
        </Modal>
      );
    };
  },
});
