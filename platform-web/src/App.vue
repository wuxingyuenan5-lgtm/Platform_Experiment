<template>
  <ConfigProvider :locale="getAntdLocale" :theme="themeConfig" :autoInsertSpaceInButton="false">
    <AppProvider>
      <RouterView />
    </AppProvider>
  </ConfigProvider>
</template>

<script lang="ts" setup>
  import { AppProvider } from '@/components/Application';
  import { useTitle } from '@/hooks/web/useTitle';
  import { useLocale } from '@/locales/useLocale';
  import { ConfigProvider } from 'ant-design-vue';

  import { useDarkModeTheme } from '@/hooks/setting/useDarkModeTheme';
  import 'dayjs/locale/zh-cn';
  import { computed } from 'vue';
  // support Multi-language
  const { getAntdLocale } = useLocale();
  const { isDark, darkTheme } = useDarkModeTheme();
  const themeConfig = computed(() => {
    console.log('isDark-----', isDark, darkTheme);

    const customColorObj = {
      colorPrimary: '#165DFF',
    };
    let _theme = {
      token: {
        fontFamily: 'Roboto',
        borderRadius: 2,
        colorPrimary: customColorObj.colorPrimary,
      },
      components: {
        Button: {
          colorLink: customColorObj.colorPrimary,
          colorLinkActive: customColorObj.colorPrimary + 'e0',
          colorLinkHover: customColorObj.colorPrimary + 'e0',
        },
        Form: {
          marginLG: 16,
        },
        Segmented: {
          colorBgElevated: customColorObj.colorPrimary,
        },
      },
    };
    if (isDark.value) {
      _theme = {
        ..._theme,
        ...darkTheme,
      };
    }
    return _theme;
  });
  // Listening to page changes and dynamically changing site titles
  useTitle();
</script>
