<template>
  <main class="start-page">
    <section class="start-hero">
      <div class="start-hero__shade"></div>

      <header class="start-header">
        <button class="start-logo" type="button" @click="goHome">
          <img :src="logoUrl" alt="Variable Global" />
        </button>

        <nav class="start-nav" aria-label="起始页导航">
          <button v-for="item in navItems" :key="item.label" type="button" @click="go(item.path)">
            {{ item.label }}
          </button>
          <button class="start-nav__login" type="button" @click="go('/home/index')">登录</button>
        </nav>
      </header>

      <section class="start-copy">
        <h1>专研全球变量<br />顺应时代大势</h1>
        <p class="start-copy__lead">全球变量，专注于识别影响时代进程与资产定价的核心变量。</p>
        <p class="start-copy__line">
          顺应周期，洞察趋势，追随资本流向；让个体与组织，成为推动世界变化的变量。
        </p>
      </section>

      <section class="start-entry-panel" aria-label="核心功能入口">
        <button
          v-for="item in entryItems"
          :key="item.label"
          class="start-entry"
          type="button"
          @click="go(item.path)"
        >
          <component :is="item.icon" class="start-entry__icon" />
          <strong>{{ item.label }}</strong>
          <span>{{ item.desc }}</span>
        </button>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
  import { useRouter } from 'vue-router';
  import {
    ClusterOutlined,
    DeploymentUnitOutlined,
    FundProjectionScreenOutlined,
    LineChartOutlined,
  } from '@ant-design/icons-vue';
  import { useUserStore } from '@/store/modules/user';
  import logoUrl from '@/assets/svg/logo.png';

  interface LandingItem {
    label: string;
    path: string;
    desc?: string;
    icon?: unknown;
  }

  const router = useRouter();
  const userStore = useUserStore();

  const navItems: LandingItem[] = [
    { label: '对冲基金看板', path: '/hedge-board/macro' },
    { label: '策略', path: '/strategy/index' },
    { label: '风控管理', path: '/risk/detail' },
    { label: '金融AI分析', path: '/financial-ai/index' },
  ];

  const entryItems: LandingItem[] = [
    {
      label: '对冲基金看板',
      path: '/hedge-board/macro',
      desc: '宏观信号与跨资产联动',
      icon: FundProjectionScreenOutlined,
    },
    {
      label: '策略研究',
      path: '/strategy/index',
      desc: '主题框架与交易洞察',
      icon: LineChartOutlined,
    },
    {
      label: '风控管理',
      path: '/risk/detail',
      desc: '账户风险与执行约束',
      icon: DeploymentUnitOutlined,
    },
    {
      label: '金融AI分析',
      path: '/financial-ai/index',
      desc: '结构化提炼与变量关联',
      icon: ClusterOutlined,
    },
  ];

  function goHome() {
    router.push('/');
  }

  async function go(path: string) {
    await userStore.logout(false);
    router.push({
      path: '/login',
      query: { redirect: path },
    });
  }
</script>

<style scoped lang="less">
  .start-page {
    min-height: 100vh;
    background: #07162a;
    color: #fff;
  }

  .start-hero {
    position: relative;
    min-height: 100vh;
    overflow: hidden;
    background: linear-gradient(
        90deg,
        rgb(2 9 24 / 72%) 0%,
        rgb(4 14 31 / 42%) 38%,
        rgb(4 12 27 / 8%) 72%
      ),
      url('@/assets/images/landing-global-network.png') center center / cover no-repeat;
  }

  .start-hero__shade {
    position: absolute;
    background: linear-gradient(
        180deg,
        rgb(3 12 28 / 8%) 0%,
        rgb(3 12 28 / 10%) 56%,
        rgb(3 12 28 / 34%) 100%
      ),
      radial-gradient(circle at 28% 35%, rgb(18 54 94 / 50%), transparent 36%);
    pointer-events: none;
    inset: 0;
  }

  .start-header {
    display: flex;
    position: relative;
    z-index: 2;
    align-items: center;
    justify-content: space-between;
    height: 74px;
    padding: 0 56px 0 78px;
    border-bottom: 1px solid rgb(255 255 255 / 13%);
  }

  .start-logo {
    display: flex;
    align-items: center;
    width: 192px;
    height: 72px;
    padding: 0;
    border: none;
    background: transparent;
    cursor: pointer;

    img {
      width: 178px;
      height: auto;
      object-fit: contain;
      filter: drop-shadow(0 12px 26px rgb(0 0 0 / 28%));
    }
  }

  .start-nav {
    display: flex;
    align-items: center;
    gap: 34px;

    button {
      transition: color 160ms ease, transform 160ms ease;
      border: none;
      background: transparent;
      color: rgb(255 255 255 / 88%);
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0;
      cursor: pointer;

      &:hover {
        transform: translateY(-1px);
        color: #f3d09a;
      }
    }

    .start-nav__login {
      min-width: 82px;
      height: 38px;
      padding: 0 22px;
      border: 1px solid rgb(255 255 255 / 46%);
      border-radius: 999px;
      box-shadow: inset 0 0 18px rgb(255 255 255 / 6%);
      color: #fff;
    }
  }

  .start-copy {
    position: relative;
    z-index: 2;
    width: min(620px, calc(100% - 48px));
    margin-left: clamp(84px, 11.5vw, 240px);
    padding-top: clamp(88px, 13vh, 158px);
  }

  .start-copy h1 {
    margin: 0;
    color: rgb(255 255 255 / 96%);
    font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif;
    font-size: clamp(54px, 4.7vw, 92px);
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1.18;
    text-shadow: 0 18px 42px rgb(0 0 0 / 42%);
  }

  .start-copy__lead {
    margin: 48px 0 0;
    color: rgb(220 234 255 / 86%);
    font-size: 18px;
    line-height: 1.8;
  }

  .start-copy__line {
    margin: 28px 0 0;
    padding-top: 24px;
    border-top: 1px solid rgb(255 255 255 / 22%);
    color: rgb(206 224 249 / 82%);
    font-size: 16px;
    line-height: 1.9;
  }

  .start-entry-panel {
    display: grid;
    position: absolute;
    z-index: 2;
    bottom: clamp(42px, 7.5vh, 84px);
    left: 50%;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    width: min(1160px, calc(100% - 48px));
    overflow: hidden;
    transform: translateX(-50%);
    border-radius: 8px;
    background: rgb(255 255 255 / 93%);
    box-shadow: 0 28px 70px rgb(0 0 0 / 34%);
  }

  .start-entry {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    min-height: 228px;
    padding: 48px 20px 34px;
    transition: background 180ms ease, transform 180ms ease;
    border: none;
    border-right: 1px solid rgb(9 24 44 / 12%);
    background: transparent;
    color: #172234;
    cursor: pointer;

    &:last-child {
      border-right: none;
    }

    &:hover {
      transform: translateY(-2px);
      background: rgb(246 241 232 / 94%);
    }
  }

  .start-entry__icon {
    margin-bottom: 16px;
    color: #c5a06a;
    font-size: 46px;
    line-height: 1;
  }

  :deep(.start-entry__icon svg) {
    width: 46px;
    height: 46px;
  }

  .start-entry strong {
    color: #161c24;
    font-family: 'Noto Serif SC', 'Songti SC', SimSun, serif;
    font-size: 25px;
    font-weight: 500;
    line-height: 1.25;
    text-align: center;
  }

  .start-entry span {
    margin-top: 14px;
    color: #717b87;
    font-size: 16px;
    line-height: 1.6;
    text-align: center;
  }

  @media (max-width: 1280px) {
    .start-header {
      padding: 0 32px;
    }

    .start-nav {
      gap: 20px;
    }

    .start-entry-panel {
      position: relative;
      bottom: auto;
      left: auto;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      margin: 72px auto 42px;
      transform: none;
    }
  }

  @media (max-width: 900px) {
    .start-hero {
      min-height: 100%;
    }

    .start-header {
      flex-direction: column;
      align-items: flex-start;
      height: auto;
      min-height: 86px;
      padding: 18px 20px;
      gap: 18px;
    }

    .start-logo {
      width: 160px;
      height: auto;

      img {
        width: 150px;
      }
    }

    .start-nav {
      flex-wrap: wrap;
      width: 100%;
      gap: 12px 18px;

      button {
        font-size: 14px;
      }
    }

    .start-copy {
      margin-left: 24px;
      padding-top: 68px;
    }

    .start-copy__lead {
      margin-top: 30px;
    }

    .start-entry-panel {
      grid-template-columns: 1fr;
      width: calc(100% - 32px);
      margin-top: 56px;
    }

    .start-entry {
      min-height: 150px;
      border-right: none;
      border-bottom: 1px solid rgb(9 24 44 / 12%);

      &:last-child {
        border-bottom: none;
      }
    }
  }
</style>
