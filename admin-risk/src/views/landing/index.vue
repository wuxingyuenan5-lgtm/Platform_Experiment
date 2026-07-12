<template>
  <main class="landing-page">
    <header class="landing-header">
      <div class="landing-header__inner">
        <button class="landing-brand" type="button" @click="go('/')">
          <img :src="logoUrl" alt="Variable Global" />
          <strong>VARIABLE GLOBAL</strong>
        </button>

        <nav class="landing-nav">
          <button
            v-for="item in navItems"
            :key="item.label"
            type="button"
            :class="{ 'is-active': item.active }"
            @click="go(item.path)"
          >
            {{ item.label }}
          </button>
        </nav>

        <div class="landing-header__actions">
          <label class="landing-search">
            <SearchOutlined />
            <input placeholder="鎼滅储鎸囨爣 / 绛栫暐 / 鐢ㄦ埛" />
          </label>

          <button class="icon-btn" type="button" aria-label="閫氱煡">
            <BellOutlined />
            <span class="icon-btn__dot"></span>
          </button>

          <button class="landing-avatar" type="button">VG</button>
        </div>
      </div>
    </header>

    <section class="landing-shell">
      <aside class="landing-rail">
        <button
          v-for="item in railItems"
          :key="item.label"
          type="button"
          :class="{ 'is-active': item.active }"
          :title="item.label"
          @click="go(item.path)"
        >
          <component :is="item.icon" />
        </button>

        <button class="landing-rail__bottom" type="button">
          <RightOutlined />
        </button>
      </aside>

      <section class="landing-main">
        <section class="landing-stage">
          <section class="hero-panel">
            <div class="hero-panel__copy">
              <span>娆㈣繋鏉ュ埌</span>
              <h1>鍏ㄧ悆鍙橀噺</h1>
              <p>椤哄簲鏃朵唬澶у娍锛屾礊鎮夋姇璧勫厛鏈?/p>
            </div>

            <button class="hero-panel__anchor" type="button">
              <DownOutlined />
            </button>

            <div class="hero-panel__art"></div>
          </section>

          <section class="hero-side">
            <article class="hero-card hero-card--market">
              <header class="hero-card__head">
                <div>
                  <strong>鍏ㄧ悆甯傚満姒傝</strong>
                  <span>鏇存柊浜?18:02 UTC+8</span>
                </div>
                <button type="button" @click="go('/hedge-board/global')">
                  <RightOutlined />
                </button>
              </header>

              <div class="market-overview-grid">
                <article v-for="item in marketOverviewItems" :key="item.label">
                  <span>{{ item.label }}</span>
                  <svg viewBox="0 0 78 22" preserveAspectRatio="none">
                    <polyline
                      :points="item.spark"
                      fill="none"
                      :stroke="item.color"
                      stroke-width="2.2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                  <strong>--</strong>
                </article>
              </div>
            </article>

            <article class="hero-card hero-card--portfolio">
              <header class="hero-card__head">
                <div>
                  <strong>鎶曡祫缁勫悎鎬昏</strong>
                </div>
                <button type="button" @click="go('/strategy/index')">
                  <RightOutlined />
                </button>
              </header>

              <div class="portfolio-card__body">
                <div class="portfolio-card__metric">
                  <span>鎬昏祫浜э紙浼板€硷級</span>
                  <strong>--</strong>
                </div>

                <div class="portfolio-card__metric">
                  <span>浠婃棩鏀剁泭</span>
                  <strong>--锛?-锛?/strong>
                </div>

                <div class="portfolio-card__ring"></div>
              </div>
            </article>
          </section>
        </section>

        <section class="dashboard-grid">
          <article class="dashboard-card">
            <header class="dashboard-card__head">
              <strong>甯傚満鑴夋悘</strong>
              <p>鎹曟崏鍏ㄧ悆鎶曡祫鏈轰細鐨勬俯搴︿俊鍙?/p>
            </header>

            <div class="dashboard-tabs">
              <button
                v-for="tab in pulseTabs"
                :key="tab"
                type="button"
                :class="{ 'is-active': activePulseTab === tab }"
                @click="activePulseTab = tab"
              >
                {{ tab }}
              </button>
            </div>

            <div class="pulse-list">
              <button
                v-for="item in activePulseRows"
                :key="item.title"
                type="button"
                class="pulse-row"
                @click="go(item.path)"
              >
                <div class="pulse-row__icon">
                  <component :is="item.icon" />
                </div>

                <div class="pulse-row__copy">
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.desc }}</p>
                </div>

                <svg viewBox="0 0 88 22" preserveAspectRatio="none">
                  <polyline
                    :points="item.spark"
                    fill="none"
                    :stroke="item.color"
                    stroke-width="2.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>

                <span>--</span>
              </button>
            </div>

            <button class="dashboard-link" type="button" @click="go('/hedge-board/macro')">
              鏌ョ湅鍏ㄩ儴甯傚満鍒嗘瀽
              <RightOutlined />
            </button>
          </article>

          <article class="dashboard-card">
            <header class="dashboard-card__head">
              <strong>缁勫悎姒傝</strong>
              <p>鍏ㄥ眬瑙嗚鎺屾彙璧勪骇閰嶇疆</p>
            </header>

            <div class="allocation-box">
              <div class="allocation-box__ring"></div>

              <div class="allocation-box__legend">
                <div v-for="item in allocationLegend" :key="item.label">
                  <i :style="{ background: item.color }"></i>
                  <span>{{ item.label }}</span>
                  <strong>--</strong>
                </div>
              </div>
            </div>

            <div class="allocation-box__stats">
              <article v-for="item in allocationStats" :key="item">
                <span>{{ item }}</span>
                <strong>--</strong>
              </article>
            </div>

            <button class="dashboard-link" type="button" @click="go('/strategy/index')">
              鏌ョ湅缁勫悎璇︽儏
              <RightOutlined />
            </button>
          </article>

          <article class="dashboard-card">
            <header class="dashboard-card__head">
              <strong>绛栫暐姒傝</strong>
              <p>澶氱瓥鐣ュ崗鍚岋紝绋冲仴鑷磋繙</p>
            </header>

            <div class="strategy-list">
              <button
                v-for="item in strategyRows"
                :key="item.title"
                type="button"
                class="strategy-row"
                @click="go(item.path)"
              >
                <div class="strategy-row__icon">
                  <component :is="item.icon" />
                </div>

                <div class="strategy-row__copy">
                  <strong>{{ item.title }}</strong>
                  <p>--锛?-锛?/p>
                </div>

                <svg viewBox="0 0 90 22" preserveAspectRatio="none">
                  <polyline
                    :points="item.spark"
                    fill="none"
                    :stroke="item.color"
                    stroke-width="2.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
            </div>

            <button class="dashboard-link" type="button" @click="go('/strategy/index')">
              鏌ョ湅鎵€鏈夌瓥鐣?              <RightOutlined />
            </button>
          </article>

          <article class="dashboard-card">
            <header class="dashboard-card__head">
              <strong>閲嶈鏃ュ巻</strong>
              <p>鎶婃彙鍏抽敭浜嬩欢涓庡競鍦鸿剦鎼?/p>
            </header>

            <div class="calendar-strip">
              <button type="button" @click="shiftCalendar(-1)">
                <LeftOutlined />
              </button>
              <strong>{{ currentCalendar.title }}</strong>
              <span>{{ currentCalendar.weekday }}</span>
              <button type="button" @click="shiftCalendar(1)">
                <RightOutlined />
              </button>
            </div>

            <div class="calendar-list">
              <article v-for="item in currentCalendar.items" :key="`${item.time}-${item.title}`">
                <div class="calendar-list__time">
                  <i></i>
                  <span>{{ item.time }}</span>
                </div>
                <div class="calendar-list__main">
                  <strong>{{ item.region }}</strong>
                  <p>{{ item.title }}</p>
                </div>
                <div class="calendar-list__side">
                  <span>棰勬湡锛?-</span>
                  <span>鍓嶅€硷細--</span>
                </div>
              </article>
            </div>

            <button class="dashboard-link" type="button" @click="go('/news-calendar/macro')">
              鏌ョ湅瀹屾暣鏃ュ巻
              <RightOutlined />
            </button>
          </article>
        </section>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import {
    BellOutlined,
    CalendarOutlined,
    ClusterOutlined,
    DatabaseOutlined,
    DeploymentUnitOutlined,
    DownOutlined,
    FundProjectionScreenOutlined,
    LeftOutlined,
    LineChartOutlined,
    ProfileOutlined,
    RightOutlined,
    SearchOutlined,
    SettingOutlined,
    UserOutlined,
  } from '@ant-design/icons-vue';
  import logoUrl from '@/assets/images/logo.png';

  interface NavItem {
    label: string;
    path: string;
    active?: boolean;
  }

  interface PulseRow {
    title: string;
    desc: string;
    path: string;
    color: string;
    spark: string;
    icon: unknown;
  }

  interface CalendarItem {
    time: string;
    region: string;
    title: string;
  }

  interface CalendarSet {
    title: string;
    weekday: string;
    items: CalendarItem[];
  }

  const router = useRouter();
  const activePulseTab = ref('澧為暱涓荤嚎');
  const activeCalendarIndex = ref(0);

  const navItems: NavItem[] = [
    { label: '棣栭〉', path: '/', active: true },
    { label: '瀹忚', path: '/hedge-board/macro' },
    { label: '璧勯噾', path: '/hedge-board/gold' },
    { label: '鍔犻€?, path: '/hedge-board/crypto' },
    { label: '鏂伴椈鏃ュ巻涓庣悊璐?, path: '/news-calendar/macro' },
    { label: '绛栫暐', path: '/strategy/index' },
    { label: '鐢ㄦ埛绠＄悊', path: '/users/index' },
    { label: '椋庢帶', path: '/risk/detail' },
    { label: '閲戣瀺AI鍒嗘瀽', path: '/financial-ai/index' },
  ];

  const railItems = [
    { label: '棣栭〉', icon: FundProjectionScreenOutlined, path: '/', active: true },
    { label: '瀹忚', icon: DatabaseOutlined, path: '/hedge-board/macro' },
    { label: '鐢ㄦ埛', icon: UserOutlined, path: '/users/index' },
    { label: '绛栫暐', icon: ProfileOutlined, path: '/strategy/index' },
    { label: '鏃ュ巻', icon: CalendarOutlined, path: '/news-calendar/macro' },
    { label: '鍒嗘瀽', icon: LineChartOutlined, path: '/financial-ai/index' },
    { label: '椋庢帶', icon: DeploymentUnitOutlined, path: '/risk/detail' },
    { label: '璁剧疆', icon: SettingOutlined, path: '/settings/index' },
  ];

  const marketOverviewItems = [
    { label: '鍏ㄧ悆鑲＄エ', color: '#e0aa4f', spark: '0,17 12,12 24,13 36,8 48,11 60,7 72,10 78,6' },
    { label: '澶у畻鍟嗗搧', color: '#66a3f2', spark: '0,12 12,9 24,13 36,7 48,12 60,9 72,12 78,8' },
    { label: '缇庡厓鎸囨暟', color: '#e0aa4f', spark: '0,14 12,11 24,12 36,9 48,13 60,10 72,12 78,9' },
    { label: '椋庨櫓鏀剁泭鐜?, color: '#bdc4cf', spark: '0,12 12,10 24,11 36,8 48,10 60,9 72,10 78,8' },
  ];

  const pulseTabs = ['澧為暱涓荤嚎', '璧勪骇浼犲', '璧勯噾娴佸悜'];

  const pulseRowsByTab: Record<string, PulseRow[]> = {
    澧為暱涓荤嚎: [
      {
        title: 'AI + 鐢熶骇鍔?,
        desc: '绉戞妧鎴愰暱椹卞姩鏂板懆鏈?,
        path: '/hedge-board/us',
        color: '#dfa349',
        spark: '0,16 12,13 24,14 36,10 48,12 60,8 72,10 84,7',
        icon: DatabaseOutlined,
      },
      {
        title: 'Breakwaves vs Gold',
        desc: '閫氳儉瀵瑰啿涓庨粍閲戣疆鍔?,
        path: '/hedge-board/gold',
        color: '#69a5f4',
        spark: '0,12 12,14 24,10 36,15 48,11 60,13 72,9 84,12',
        icon: ClusterOutlined,
      },
      {
        title: 'DXY vs US10Y',
        desc: '缇庡厓鍒╃巼涓庢敹鐩婄巼鑱斿姩',
        path: '/hedge-board/macro',
        color: '#b8bfc9',
        spark: '0,10 12,11 24,9 36,12 48,11 60,10 72,11 84,9',
        icon: LineChartOutlined,
      },
    ],
    璧勪骇浼犲: [
      {
        title: '榛勯噾 vs 瀹為檯鍒╃巼',
        desc: '閫氳儉棰勬湡涓庤吹閲戝睘瀹氫环',
        path: '/hedge-board/gold',
        color: '#dfa349',
        spark: '0,15 12,10 24,12 36,8 48,10 60,7 72,9 84,6',
        icon: ClusterOutlined,
      },
      {
        title: 'BTC vs Nasdaq',
        desc: '椋庨櫓鍋忓ソ鍒板姞瀵嗚祫浜?,
        path: '/hedge-board/crypto',
        color: '#69a5f4',
        spark: '0,10 12,12 24,9 36,14 48,10 60,13 72,11 84,14',
        icon: LineChartOutlined,
      },
      {
        title: '缇庡厓 vs 鍘熸补',
        desc: '澶栨眹涓庡晢鍝佸弽棣堝洖璺?,
        path: '/hedge-board/macro',
        color: '#b8bfc9',
        spark: '0,11 12,9 24,10 36,11 48,9 60,10 72,9 84,8',
        icon: DeploymentUnitOutlined,
      },
    ],
    璧勯噾娴佸悜: [
      {
        title: '榛勯噾ETF娴佸悜',
        desc: '閬块櫓璧勯噾涓庤秼鍔跨‘璁?,
        path: '/hedge-board/gold',
        color: '#dfa349',
        spark: '0,14 12,12 24,13 36,9 48,11 60,8 72,9 84,7',
        icon: ClusterOutlined,
      },
      {
        title: 'BTC ETF娴侀噺',
        desc: '鐜拌揣璧勯噾杩涘叆鑺傚',
        path: '/hedge-board/crypto',
        color: '#69a5f4',
        spark: '0,11 12,13 24,12 36,16 48,13 60,15 72,12 84,14',
        icon: DatabaseOutlined,
      },
      {
        title: '缇庡厓娴佸姩鎬?,
        desc: '娴佸姩鎬ц剦鍐蹭笌椋庨櫓璧勪骇',
        path: '/hedge-board/macro',
        color: '#b8bfc9',
        spark: '0,8 12,9 24,8 36,10 48,9 60,8 72,9 84,8',
        icon: DeploymentUnitOutlined,
      },
    ],
  };

  const activePulseRows = computed(() => pulseRowsByTab[activePulseTab.value] || []);

  const allocationLegend = [
    { label: '鏉冪泭绫?, color: '#e2c48c' },
    { label: '鍥烘敹绫?, color: '#8fb1d8' },
    { label: '澶у畻鍟嗗搧', color: '#efdfc0' },
    { label: '鍔犲瘑璧勪骇', color: '#d9e4f0' },
    { label: '鐜伴噾鍙婂叾浠?, color: '#eceff3' },
  ];

  const allocationStats = ['缁勫悎娉㈠姩鐜囷紙骞村寲锛?, '鏈€澶у洖鎾?, '澶忔櫘姣旂巼', 'VaR锛?5%锛?];

  const strategyRows = [
    {
      title: '瀹忚瀵瑰啿绛栫暐',
      path: '/strategy/index',
      color: '#dfa349',
      spark: '0,15 12,11 24,14 36,10 48,12 60,9 72,13 84,10',
      icon: DatabaseOutlined,
    },
    {
      title: '璺ㄨ祫浜ч厤缃瓥鐣?,
      path: '/strategy/index',
      color: '#69a5f4',
      spark: '0,11 12,14 24,10 36,15 48,11 60,14 72,10 84,13',
      icon: DeploymentUnitOutlined,
    },
    {
      title: '浜嬩欢椹卞姩绛栫暐',
      path: '/strategy/index',
      color: '#bcc3cc',
      spark: '0,10 12,11 24,9 36,11 48,10 60,9 72,10 84,9',
      icon: CalendarOutlined,
    },
  ];

  const calendarSets: CalendarSet[] = [
    {
      title: '2025骞?鏈?7鏃?,
      weekday: '鏄熸湡鍏?,
      items: [
        { time: '09:30', region: '涓浗', title: '4鏈堣妯′互涓婂伐涓氬鍔犲€? },
        { time: '17:00', region: '娆у厓鍖?, title: '3鏈圕PI缁堝€硷紙骞寸巼锛? },
        { time: '20:30', region: '缇庡浗', title: '4鏈堥浂鍞攢鍞湀鐜? },
        { time: '22:00', region: '缇庡浗', title: '5鏈堝瘑姝囨牴澶у娑堣垂鑰呬俊蹇冩寚鏁板垵鍊? },
      ],
    },
    {
      title: '2025骞?鏈?8鏃?,
      weekday: '鏄熸湡鏃?,
      items: [
        { time: '08:30', region: '鏃ユ湰', title: '涓€瀛ｅ害GDP淇鍊? },
        { time: '15:00', region: '鑻卞浗', title: '4鏈堝け涓氱巼' },
        { time: '20:30', region: '缇庡浗', title: '鏂板眿寮€宸ユ€绘暟骞村寲' },
        { time: '23:00', region: '缇庡浗', title: 'EIA鐭湡鑳芥簮灞曟湜' },
      ],
    },
  ];

  const currentCalendar = computed(() => calendarSets[activeCalendarIndex.value]);

  function shiftCalendar(direction: number) {
    const total = calendarSets.length;
    activeCalendarIndex.value = (activeCalendarIndex.value + direction + total) % total;
  }

  function go(path: string) {
    router.push(path);
  }
</script>

<style scoped lang="less">
  .landing-page {
    min-height: 100vh;
    background:
      radial-gradient(circle at 20% 0%, rgba(227, 211, 181, 0.18) 0%, rgba(227, 211, 181, 0) 26%),
      radial-gradient(circle at 86% 10%, rgba(214, 225, 241, 0.26) 0%, rgba(214, 225, 241, 0) 32%),
      linear-gradient(180deg, #f9fafc 0%, #eef3f7 100%);
  }

  .landing-header {
    position: sticky;
    top: 0;
    z-index: 20;
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(226, 232, 239, 0.85);
  }

  .landing-header__inner {
    width: min(1760px, calc(100% - 40px));
    height: 88px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 24px;
  }

  .landing-brand {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0;
    border: none;
    background: transparent;
    cursor: pointer;

    img {
      width: 40px;
      height: 40px;
      object-fit: contain;
    }

    strong {
      color: #1f2730;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.12em;
    }
  }

  .landing-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 24px;

    button {
      position: relative;
      height: 46px;
      padding: 0;
      border: none;
      background: transparent;
      color: #202833;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;

      &::after {
        content: '';
        position: absolute;
        left: 50%;
        bottom: -2px;
        width: 28px;
        height: 2px;
        border-radius: 999px;
        background: transparent;
        transform: translateX(-50%);
      }

      &.is-active {
        color: #bb9252;
      }

      &.is-active::after {
        background: #bb9252;
      }
    }
  }

  .landing-header__actions {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .landing-search {
    width: 262px;
    height: 42px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 14px;
    border: 1px solid rgba(225, 231, 238, 0.95);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.92);
    color: #85909c;

    input {
      width: 100%;
      border: none;
      outline: none;
      background: transparent;
      color: #495460;
      font-size: 14px;
    }
  }

  .icon-btn {
    position: relative;
    width: 36px;
    height: 36px;
    border: none;
    background: transparent;
    color: #727d89;
    font-size: 20px;
    cursor: pointer;
  }

  .icon-btn__dot {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f25d55;
  }

  .landing-avatar {
    width: 42px;
    height: 42px;
    border: none;
    border-radius: 50%;
    background: linear-gradient(180deg, #d9c38a 0%, #b5914d 100%);
    color: #fff;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }

  .landing-shell {
    width: min(1760px, calc(100% - 40px));
    margin: 0 auto;
    padding: 30px 0 38px;
    display: grid;
    grid-template-columns: 62px minmax(0, 1fr);
    gap: 22px;
  }

  .landing-rail {
    position: sticky;
    top: 112px;
    height: fit-content;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 16px 0;
    border: 1px solid rgba(228, 233, 239, 0.95);
    border-radius: 30px;
    background: rgba(255, 255, 255, 0.82);
    box-shadow: 0 18px 34px rgba(183, 194, 209, 0.12);
    backdrop-filter: blur(10px);

    button {
      width: 36px;
      height: 36px;
      margin: 0 auto;
      border: none;
      border-radius: 14px;
      background: transparent;
      color: #7c8894;
      font-size: 18px;
      cursor: pointer;
      transition:
        background-color 0.2s ease,
        color 0.2s ease,
        transform 0.2s ease;

      &:hover {
        transform: translateY(-1px);
      }

      &.is-active {
        background: rgba(193, 155, 84, 0.16);
        color: #c09553;
      }
    }
  }

  .landing-rail__bottom {
    margin-top: 10px !important;
    border: 1px solid rgba(228, 233, 239, 0.95) !important;
    background: rgba(255, 255, 255, 0.9) !important;
    color: #202833 !important;
    font-size: 14px !important;
  }

  .landing-main {
    display: grid;
    gap: 28px;
  }

  .landing-stage {
    display: grid;
    grid-template-columns: minmax(0, 1.88fr) 410px;
    gap: 22px;
  }

  .hero-panel {
    position: relative;
    min-height: 448px;
    overflow: hidden;
    border: 1px solid rgba(228, 233, 239, 0.95);
    border-radius: 30px;
    background:
      radial-gradient(circle at 22% 0%, rgba(232, 219, 194, 0.16) 0, rgba(232, 219, 194, 0) 30%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(248, 250, 252, 0.9) 100%);
    box-shadow: 0 22px 46px rgba(183, 194, 209, 0.1);
  }

  .hero-panel::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at 68% 42%, rgba(209, 224, 241, 0.28) 0%, rgba(209, 224, 241, 0) 33%),
      linear-gradient(90deg, rgba(255, 255, 255, 0.82) 0%, rgba(255, 255, 255, 0.45) 42%, rgba(255, 255, 255, 0) 68%);
    pointer-events: none;
  }

  .hero-panel__copy {
    position: relative;
    z-index: 2;
    width: 420px;
    padding: 56px 0 0 64px;

    span {
      display: block;
      margin-bottom: 14px;
      color: #707c88;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.08em;
    }

    h1 {
      margin: 0;
      color: #1f2730;
      font-size: 64px;
      font-weight: 600;
      line-height: 1.05;
      letter-spacing: 0.02em;
    }

    p {
      margin: 20px 0 0;
      color: #4f5966;
      font-size: 24px;
      line-height: 1.52;
    }
  }

  .hero-panel__anchor {
    position: absolute;
    left: 64px;
    bottom: 34px;
    z-index: 2;
    width: 42px;
    height: 42px;
    border: 1px solid rgba(226, 232, 238, 0.95);
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.9);
    color: #bf9554;
    font-size: 16px;
    cursor: pointer;
  }

  .hero-panel__art {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 78%;
    background:
      url('@/assets/images/home-hero-art-locked.png') right center / cover no-repeat;
    filter: saturate(0.98) brightness(1.02);
  }

  .hero-side {
    display: grid;
    gap: 22px;
  }

  .hero-card,
  .dashboard-card {
    border: 1px solid rgba(228, 233, 239, 0.95);
    border-radius: 28px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 18px 40px rgba(183, 194, 209, 0.09);
    backdrop-filter: blur(12px);
  }

  .hero-card {
    padding: 24px 24px 22px;
  }

  .hero-card--market {
    min-height: 196px;
  }

  .hero-card--portfolio {
    min-height: 196px;
  }

  .hero-card__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;

    strong {
      display: block;
      color: #1f2730;
      font-size: 18px;
      font-weight: 700;
    }

    span {
      display: block;
      margin-top: 4px;
      color: #8a95a1;
      font-size: 13px;
    }

    button {
      width: 24px;
      height: 24px;
      border: none;
      background: transparent;
      color: #c39858;
      font-size: 16px;
      cursor: pointer;
    }
  }

  .market-overview-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;

    article {
      display: grid;
      gap: 8px;
    }

    span {
      color: #727c88;
      font-size: 13px;
      font-weight: 600;
    }

    svg {
      width: 100%;
      height: 24px;
    }

    strong {
      color: #1f2730;
      font-size: 18px;
    }
  }

  .portfolio-card__body {
    display: grid;
    grid-template-columns: 1fr 1fr 104px;
    gap: 16px;
    align-items: center;
  }

  .portfolio-card__metric {
    display: grid;
    gap: 10px;

    span {
      color: #8a95a1;
      font-size: 14px;
    }

    strong {
      color: #202833;
      font-size: 28px;
      font-weight: 700;
    }
  }

  .portfolio-card__ring,
  .allocation-box__ring {
    position: relative;
    border-radius: 50%;
    background: conic-gradient(#e4cfaa 0 24%, #a2bbda 24% 53%, #f0e1c3 53% 77%, #dce2eb 77% 100%);

    &::after {
      content: '';
      position: absolute;
      inset: 16px;
      border-radius: 50%;
      background: #fff;
    }
  }

  .portfolio-card__ring {
    width: 102px;
    height: 102px;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 22px;
  }

  .dashboard-card {
    min-height: 388px;
    padding: 22px 22px 20px;
    display: flex;
    flex-direction: column;
  }

  .dashboard-card__head {
    margin-bottom: 18px;

    strong {
      display: block;
      color: #202833;
      font-size: 18px;
      font-weight: 700;
    }

    p {
      margin: 6px 0 0;
      color: #8c97a3;
      font-size: 13px;
      line-height: 1.65;
    }
  }

  .dashboard-tabs {
    display: flex;
    gap: 30px;
    margin-bottom: 18px;

    button {
      position: relative;
      padding: 0 0 10px;
      border: none;
      background: transparent;
      color: #949daa;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;

      &::after {
        content: '';
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 2px;
        border-radius: 999px;
        background: transparent;
      }

      &.is-active {
        color: #c09553;
      }

      &.is-active::after {
        background: #c09553;
      }
    }
  }

  .pulse-list,
  .strategy-list,
  .calendar-list {
    display: grid;
    gap: 14px;
  }

  .pulse-row,
  .strategy-row {
    display: grid;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 8px 0;
    border: none;
    border-radius: 18px;
    background: transparent;
    text-align: left;
    cursor: pointer;
    transition:
      background-color 0.2s ease,
      transform 0.2s ease;

    &:hover {
      background: rgba(246, 248, 251, 0.92);
      transform: translateY(-1px);
    }

    svg {
      width: 88px;
      height: 22px;
    }
  }

  .pulse-row {
    grid-template-columns: 40px minmax(0, 1fr) 88px 20px;

    span:last-child {
      color: #8e98a4;
      font-size: 15px;
      text-align: right;
    }
  }

  .pulse-row__icon,
  .strategy-row__icon {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #f3f5f8;
    color: #c09553;
    font-size: 18px;
  }

  .pulse-row__copy,
  .strategy-row__copy {
    strong {
      display: block;
      color: #202833;
      font-size: 15px;
      font-weight: 700;
    }

    p {
      margin: 4px 0 0;
      color: #8d97a2;
      font-size: 13px;
    }
  }

  .allocation-box {
    display: flex;
    align-items: center;
    gap: 22px;
    margin-bottom: 18px;
  }

  .allocation-box__ring {
    flex: 0 0 auto;
    width: 164px;
    height: 164px;

    &::after {
      inset: 28px;
    }
  }

  .allocation-box__legend {
    flex: 1;
    display: grid;
    gap: 12px;

    div {
      display: grid;
      grid-template-columns: 10px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
    }

    i {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }

    span {
      color: #6d7783;
      font-size: 14px;
    }

    strong {
      color: #a0a8b1;
      font-size: 14px;
    }
  }

  .allocation-box__stats {
    margin-top: auto;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 18px;

    article {
      display: grid;
      gap: 8px;
    }

    span {
      color: #8c96a2;
      font-size: 13px;
    }

    strong {
      color: #a1a8b0;
      font-size: 18px;
    }
  }

  .strategy-row {
    grid-template-columns: 40px minmax(0, 1fr) 88px;
  }

  .calendar-strip {
    display: grid;
    grid-template-columns: 28px 1fr auto 28px;
    align-items: center;
    gap: 12px;
    padding: 8px 0 16px;
    border-bottom: 1px solid rgba(232, 237, 243, 0.95);

    button {
      width: 28px;
      height: 28px;
      border: none;
      background: transparent;
      color: #c09553;
      font-size: 16px;
      cursor: pointer;
    }

    strong {
      justify-self: center;
      color: #202833;
      font-size: 15px;
      font-weight: 700;
    }

    span {
      color: #6a7380;
      font-size: 15px;
    }
  }

  .calendar-list article {
    display: grid;
    grid-template-columns: 84px minmax(0, 1fr) auto;
    gap: 12px;
    align-items: start;
    padding: 12px 0;
  }

  .calendar-list__time {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #6e7782;
    font-size: 14px;

    i {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #d89753;
    }
  }

  .calendar-list__main {
    strong {
      display: inline-block;
      margin-right: 10px;
      color: #4d5662;
      font-size: 14px;
      font-weight: 700;
    }

    p {
      display: inline;
      margin: 0;
      color: #818a96;
      font-size: 13px;
      line-height: 1.7;
    }
  }

  .calendar-list__side {
    display: grid;
    gap: 4px;
    text-align: right;

    span {
      color: #8a94a0;
      font-size: 13px;
    }
  }

  .dashboard-link {
    margin-top: auto;
    padding-top: 20px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: none;
    background: transparent;
    color: #bf9352;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }

  @media (max-width: 1600px) {
    .landing-stage {
      grid-template-columns: minmax(0, 1.5fr) 380px;
    }

    .dashboard-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 1280px) {
    .landing-shell {
      grid-template-columns: 1fr;
    }

    .landing-rail {
      display: none;
    }

    .landing-stage {
      grid-template-columns: 1fr;
    }

    .hero-side {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .landing-nav {
      flex-wrap: wrap;
      justify-content: flex-start;
      gap: 18px;
    }

    .landing-header__inner {
      height: auto;
      padding: 18px 0;
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 900px) {
    .landing-shell,
    .landing-header__inner {
      width: min(100%, calc(100% - 24px));
    }

    .landing-search {
      width: 100%;
    }

    .landing-header__actions {
      flex-wrap: wrap;
    }

    .hero-panel {
      min-height: 420px;
    }

    .hero-panel__copy {
      width: auto;
      padding: 42px 24px 0;

      h1 {
        font-size: 46px;
      }

      p {
        font-size: 20px;
      }
    }

    .hero-panel__anchor {
      left: 24px;
    }

    .hero-panel__art {
      width: 100%;
      opacity: 0.58;
    }

    .hero-side,
    .dashboard-grid,
    .portfolio-card__body {
      grid-template-columns: 1fr;
    }

    .market-overview-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .allocation-box {
      flex-direction: column;
      align-items: flex-start;
    }

    .allocation-box__ring {
      margin: 0 auto;
    }
  }
</style>

