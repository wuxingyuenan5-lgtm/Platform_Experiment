<template>
  <div :class="prefixCls" class="relative w-full h-full">
    <div class="login-container relative h-full mx-auto">
      <LoginForm />
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useDesign } from '@/hooks/web/useDesign';
  import LoginForm from './LoginForm.vue';

  defineProps({
    sessionTimeout: {
      type: Boolean,
    },
  });

  const { prefixCls } = useDesign('login');
</script>
<style lang="less">
  @prefix-cls: ~'@{namespace}-login';
  @logo-prefix-cls: ~'@{namespace}-app-logo';
  @countdown-prefix-cls: ~'@{namespace}-countdown-input';
  @dark-bg: #293146;
  .@{prefix-cls} {
    width: 100vw;
    min-width: 0;
    max-width: 100vw;
    min-height: 100vh;
    overflow: auto;
    box-sizing: border-box;
    scrollbar-gutter: stable;
    background: radial-gradient(circle at top right, rgba(178, 206, 236, 0.28), transparent 30%),
      linear-gradient(180deg, #f6f8fb 0%, #edf2f7 100%);

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-image: url('@/assets/images/home-butterfly-topology.png');
      background-repeat: no-repeat;
      background-position: center 12%;
      background-size: 72%;
      opacity: 0.18;
    }

    .@{logo-prefix-cls} {
      position: absolute;
      top: 12px;
      height: 30px;

      &__title {
        color: #fff;
        font-size: 16px;
      }

      img {
        width: 32px;
      }
    }

    .login-container {
      width: 100%;

      .@{logo-prefix-cls} {
        display: flex;
        width: 60%;
        height: 80px;

        &__title {
          color: #fff;
          font-size: 24px;
        }

        img {
          width: 150px;
        }
      }
    }

    &-sign-in-way {
      .anticon {
        color: #888;
        font-size: 22px;
        cursor: pointer;

        &:hover {
          color: @primary-color;
        }
      }
    }
  }
</style>
