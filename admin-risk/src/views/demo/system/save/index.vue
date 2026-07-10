<template>
  <div class="w-936px m-auto mt-12">
    <div class="text-base font-500 pb-4">安全设置</div>
    <div class="control-bg p-12 pb-40">
      <div class="flex items-center leading-16">
        <Icon icon="ant-design:lock-filled" size="24" class="text-#828282" />
        <div class="w-170px pl-2 shrink-0">密码</div>
        <div class="flex-1 color-third"></div>
        <div
          @click="handleClick({ type: ClickType.PASSWORD })"
          class="color-secondary cursor-pointer"
          >修改</div
        >
      </div>
      <div class="flex items-center leading-16">
        <Icon icon="ant-design:mobile-filled" size="24" class="text-#828282" />
        <div class="w-170px pl-2 shrink-0">手机号码</div>
        <div class="flex-1 color-third">{{ userInfo?.phoneNumber || '未绑定' }}</div>
        <div @click="handleClick({ type: ClickType.PHONE })" class="cursor-pointer text-#C1272D">{{
          userInfo?.phoneNumber ? '修改' : '绑定'
        }}</div>
      </div>
      <div class="flex items-center leading-16">
        <Icon icon="menu-feishu|svg" size="24" class="text-#828282" />
        <div class="w-170px pl-2 shrink-0">飞书地址</div>
        <div class="flex-1 color-third">{{ userInfo?.larkUrl || '未绑定' }}</div>
        <div @click="handleClick({ type: ClickType.FEISHU })" class="cursor-pointer text-#C1272D">{{
          userInfo?.larkUrl ? '修改' : '绑定'
        }}</div>
      </div>
      <div class="flex items-center leading-16">
        <Icon icon="ant-design:mail-filled" size="24" class="text-#828282" />
        <div class="w-170px pl-2 shrink-0">邮箱设置</div>
        <div class="flex-1 color-third">{{ userInfo?.email || '未绑定' }}</div>
        <div @click="handleClick({ type: ClickType.EMAIL })" class="cursor-pointer text-#C1272D"
          >修改</div
        >
      </div>
      <div class="flex items-center leading-16">
        <Icon icon="menu-google|svg" size="24" class="text-#828282" />
        <div class="w-170px pl-2 shrink-0">谷歌验证</div>
        <div class="flex-1 color-third">{{
          userInfo?.isGoogleAuthEnabled ? '已绑定' : '未绑定'
        }}</div>
        <div
          v-if="!userInfo?.isGoogleAuthEnabled"
          @click="handleClick({ type: ClickType.GOOGLE })"
          class="cursor-pointer text-#C1272D"
          >绑定</div
        >
      </div>
    </div>
    <Password ref="passwordRef" @submit="onSubmit" />
    <Phone
      ref="phoneRef"
      @submit="onSubmit"
      :type="userInfo?.phone ? ConfigPropType.CHANGE : ConfigPropType.BIND"
    />
    <Email
      ref="emailRef"
      @submit="onSubmit"
      :type="userInfo?.email ? ConfigPropType.CHANGE : ConfigPropType.BIND"
    />
    <Feishu
      ref="feishuRef"
      @submit="onSubmit"
      :type="userInfo?.feishu ? ConfigPropType.CHANGE : ConfigPropType.BIND"
    />
    <GoogleCode :code="code" @register="registerCode" />
  </div>
</template>
<script lang="tsx" setup>
  import Icon from '@/components/Icon/Icon.vue';
  import { Password, Phone, Email, Feishu } from './components/modules';
  import { computed, ref } from 'vue';
  import { ClickType, ConfigPropType } from './enums';
  import { useUserStore } from '@/store/modules/user';
  import GoogleCode from '@/layouts/default/header/components/code/index.vue';
  import { useModal } from '@/components/Modal';
  import { loginQrcode, postChangeEmail, postChangePhone } from '@/api/sys/user';
  import { useMessage } from '@/hooks/web/useMessage';
  import { useApiBasic } from '@/hooks/web/useApi';

  const { createMessage } = useMessage();

  const code = ref(''); // 二维码
  const [registerCode, { openModal: openCodeModal }] = useModal();

  const userStore = useUserStore();
  const userInfo = computed(() => userStore.getUserInfoInfo);
  console.log('userInfo', userInfo);

  const passwordRef = ref();
  const phoneRef = ref();
  const emailRef = ref();
  const feishuRef = ref();

  function onSubmit(params: any) {
    console.log('Submitted:', params);
    switch (params.action) {
      case 'phone':
        postChangePhoneFn(params);
        break;
      case 'email':
        postChangeEmailFn(params);
        break;
    }
  }
  function handleClick(params: any) {
    switch (params.type) {
      case ClickType.PASSWORD:
        passwordRef.value.visible = true;
        break;
      case ClickType.PHONE:
        phoneRef.value.visible = true;
        break;
      case ClickType.EMAIL:
        emailRef.value.visible = true;
        break;
      case ClickType.FEISHU:
        feishuRef.value.visible = true;
        break;
      case ClickType.GOOGLE:
        handleCode();
        break;
    }
  }
  async function handleCode() {
    const res = await loginQrcode();
    if (res.retCode == 0) {
      code.value = res.data;
      openCodeModal(true, {});
    } else {
      createMessage.error(res.msg || res.retMsg);
    }
  }
  function postChangePhoneFn(params?: any) {
    useApiBasic({
      apiFn: postChangePhone(params),
      successFn() {
        userStore.getUserInfoAction();
        phoneRef.value.visible = false;
      },
    });
  }
  function postChangeEmailFn(params?: any) {
    useApiBasic({
      apiFn: postChangeEmail(params),
      successFn() {
        userStore.getUserInfoAction();
        emailRef.value.visible = false;
      },
    });
  }
</script>
