<template>
  <div class="vg-exception">
    <div class="vg-exception__shell">
      <div class="vg-exception__art">
        <div class="vg-exception__orb"></div>
        <div class="vg-exception__mark">?</div>
      </div>

      <div class="vg-exception__copy">
        <span class="vg-exception__eyebrow">Variable Global</span>
        <h1>{{ displayTitle }}</h1>
        <p>{{ displaySubtitle }}</p>

        <div class="vg-exception__actions">
          <Button type="primary" @click="primaryHandler">{{ primaryText }}</Button>
          <Button @click="go(PageEnum.BASE_HOME)">返回首页</Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute } from 'vue-router';
  import { Button } from 'ant-design-vue';
  import { ExceptionEnum } from '@/enums/exceptionEnum';
  import { useGo, useRedo } from '@/hooks/web/usePage';
  import { useI18n } from '@/hooks/web/useI18n';
  import { PageEnum } from '@/enums/pageEnum';
  import { useUserStore } from '@/store/modules/user';

  const props = defineProps({
    status: {
      type: Number,
      default: ExceptionEnum.PAGE_NOT_FOUND,
    },
    title: {
      type: String,
      default: '',
    },
    subTitle: {
      type: String,
      default: '',
    },
    full: {
      type: Boolean,
      default: false,
    },
  });

  const route = useRoute();
  const { t } = useI18n();
  const go = useGo();
  const redo = useRedo();
  const userStore = useUserStore();

  const currentStatus = computed(() => Number(route.query.status) || props.status);

  const titleMap = {
    [ExceptionEnum.PAGE_NOT_ACCESS]: '403',
    [ExceptionEnum.PAGE_NOT_FOUND]: '404',
    [ExceptionEnum.ERROR]: '500',
    [ExceptionEnum.PAGE_NOT_DATA]: t('sys.exception.noDataTitle'),
    [ExceptionEnum.NET_WORK_ERROR]: t('sys.exception.networkErrorTitle'),
  } as Record<number, string>;

  const subtitleMap = {
    [ExceptionEnum.PAGE_NOT_ACCESS]: t('sys.exception.subTitle403'),
    [ExceptionEnum.PAGE_NOT_FOUND]: '你访问的页面不存在，或当前入口路由还没有完成装载。',
    [ExceptionEnum.ERROR]: t('sys.exception.subTitle500'),
    [ExceptionEnum.PAGE_NOT_DATA]: '当前没有可展示的数据，请稍后再试。',
    [ExceptionEnum.NET_WORK_ERROR]: t('sys.exception.networkErrorSubTitle'),
  } as Record<number, string>;

  const displayTitle = computed(() => props.title || titleMap[currentStatus.value] || '404');
  const displaySubtitle = computed(
    () => props.subTitle || subtitleMap[currentStatus.value] || '页面暂时不可用。',
  );
  const primaryText = computed(() =>
    currentStatus.value === ExceptionEnum.PAGE_NOT_FOUND ? '返回登录' : '重新加载',
  );

  function primaryHandler() {
    if (currentStatus.value === ExceptionEnum.PAGE_NOT_FOUND) {
      userStore.logout(true);
      return;
    }
    if (
      currentStatus.value === ExceptionEnum.PAGE_NOT_DATA ||
      currentStatus.value === ExceptionEnum.NET_WORK_ERROR
    ) {
      redo();
      return;
    }
    go(PageEnum.BASE_HOME);
  }
</script>

<style scoped lang="less">
  .vg-exception {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 32px;
    background:
      radial-gradient(circle at top right, rgba(178, 206, 236, 0.34), transparent 28%),
      linear-gradient(180deg, #f6f8fb 0%, #edf2f7 100%);
  }

  .vg-exception__shell {
    display: grid;
    grid-template-columns: 280px minmax(360px, 520px);
    align-items: center;
    gap: 36px;
    padding: 42px;
    border: 1px solid rgba(214, 221, 229, 0.96);
    border-radius: 30px;
    background: rgba(255, 255, 255, 0.95);
    box-shadow: 0 28px 84px rgba(135, 155, 182, 0.16);
  }

  .vg-exception__art {
    position: relative;
    display: grid;
    place-items: center;
    height: 280px;
  }

  .vg-exception__orb {
    position: absolute;
    inset: 24px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(204, 219, 236, 0.9), rgba(235, 241, 248, 0.56));
  }

  .vg-exception__mark {
    position: relative;
    display: grid;
    place-items: center;
    width: 108px;
    height: 108px;
    border-radius: 28px;
    background: linear-gradient(135deg, #3f6ea3, #7ea7d1);
    color: #fff;
    font-size: 42px;
    font-weight: 700;
    box-shadow: 0 18px 48px rgba(63, 110, 163, 0.28);
  }

  .vg-exception__eyebrow {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .vg-exception__copy h1 {
    margin: 14px 0 10px;
    color: #0f172a;
    font-family: Georgia, 'Times New Roman', 'Noto Serif SC', serif;
    font-size: 56px;
    line-height: 1;
  }

  .vg-exception__copy p {
    margin: 0;
    color: #64748b;
    font-size: 15px;
    line-height: 1.8;
  }

  .vg-exception__actions {
    display: flex;
    gap: 12px;
    margin-top: 28px;
  }

  @media (max-width: 900px) {
    .vg-exception__shell {
      grid-template-columns: 1fr;
      text-align: center;
    }

    .vg-exception__actions {
      justify-content: center;
    }
  }
</style>
