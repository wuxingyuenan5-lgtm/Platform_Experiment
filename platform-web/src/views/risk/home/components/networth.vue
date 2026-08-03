<template>
  <SimpleContainer title="æµ·å†…å¤–å‡€å€¼å æ¯”">
    <div class="h-100 component-background">
      <div class="flex justify-end pt-3 pr-3">
        <Segmented v-model:value="curUnit" size="small" :options="unitOptions" />
      </div>
      <div class="h-388px">
        <Spin :spinning="loading">
          <div ref="chartRef" :style="{ width, height: height }">
            <div
              v-if="!record || record?.length == 0"
              class="flex items-center justify-center h-full"
            >
              <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </div>
          </div>
        </Spin>
      </div>
    </div>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import type { PropType, Ref } from 'vue';
  import { watch, ref, reactive, toRaw, onMounted } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import { Empty, Spin, Segmented } from 'ant-design-vue';
  import { formateNumStr } from '@/utils/formate';
  import { unitOptions } from '@/utils/options/basicOptions';
  import { getProductNavProductRatio } from '@/api/data/product';
  import { watchDebounced } from '@vueuse/shared';

  const props = defineProps({
    // record: {
    //   type: Object,
    //   default: () => {},
    // },
    // loading: {
    //   type: Boolean,
    //   default: false,
    // },
    width: {
      type: String as PropType<string>,
      default: '100%',
    },
    height: {
      type: String as PropType<string>,
      default: '364px',
    },
  });
  const record = ref();
  // å½“å‰å•ä½
  const curUnit = ref('USD');
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, getInstance } = useECharts(chartRef as Ref<HTMLDivElement>);
  const loading = ref(false);
  function initData() {
    setOptions({
      dataset: { source: record.value },
      legend: {
        show: true,
        top: 16,
        icon: 'rect',
        itemWidth: 12,
        itemHeight: 2,
        itemGap: 36,
      },
      tooltip: {
        formatter: function (params) {
          // console.log(params);

          const _data = params?.data;
          return `<div class='text-xs'>
                <div class='color-secondary'>${_data?.name}</div>
                <div class='border-bottom my-2'></div>
                <div>å‡€å€¼ï¼š${formateNumStr(_data?.value, { decimals: 2, keepZero: true })}</div>
                <div>å æ¯”ï¼š${((_data?.percent || 0) * 100).toFixed(2)}%</div>
                </div>
                `;
        },
      },
      series: [
        {
          type: 'pie',
          radius: '50%',
          center: ['50%', '55%'],
         ÛÛÜˆÉÈÑMMN	Ë	ÈÍP‘‰×KˆX™[ˆÂˆÚİÎˆYKˆ›Ü›X]\ˆ[˜İ[Ûˆ
\˜[\ÊHÂˆËÈÛÛœÛÛK›ÙÊ\˜[\ÊNÂˆ™]\›ˆ	Ü\˜[\ÏË™]OË›˜[Y_W‰Ù›Ü›X]S[TİŠ\˜[\ÏË™]OË˜[YKÂˆXÚ[X[Îˆ‹ˆÙY\™\›ÎˆYKˆJ_XÂˆKˆKˆ[š[X][Û•\Nˆ	ÜØØ[IËˆ[š[X][Û‘X\Ú[™Îˆ	Ù^Û™[X[[“İ]	Ëˆ[š[X][Û‘[^Nˆ
[™^ˆ[X™\ŠHOˆ[™^
ˆˆKˆKˆJNÂˆBˆ[˜İ[ÛˆÙ]›ÙXİ˜]”›ÙXİ˜][Ñ›Š
HÂˆØY[™Ë˜[YHHYNÂˆÙ]›ÙXİ˜]”›ÙXİ˜][Ê
Bˆ[Š
™\Îˆ[JHOˆÂˆYˆ
™\Ëœ™]ÛÙHOH
HÂˆÛÛœİİİ[H™\Ë™]Kœ™YXÙJ
™Nˆ[Kİ\ˆ[JHOˆÂˆÛÛœİİ˜[Hİ\•[š]˜[YHOH	ÕTÑ	ÈÈİ\‹˜[YUTÑˆİ\‹˜[YNÂˆ™]\›ˆ™H
Èİ˜[ÂˆK
NÂˆ™XÛÜ™˜[YHH™\Ë™]OË›X\

][Nˆ[JHOˆÂˆ]İ˜[Hİ\•[š]˜[YHOH	ÕTÑ	ÈÈ][K˜[YUTÑˆ][K˜[YNÂˆ™]\›ˆÂˆ˜[YNˆ][K›˜[YKˆ˜[YNˆİ˜[Ñš^Y
ŠKˆ\˜Ù[ˆİİ[È
İ˜[Èİİ[
KÑš^Y

HˆˆNÂˆJNÂˆ[š]]J
NÂˆBˆJBˆ™š[˜[J

HOˆÂˆØY[™Ë˜[YHH˜[ÙNÂˆJNÂˆBˆØ]ÚX›İ[˜ÙY
ˆ

HOˆİ\•[š]˜[YKˆ

HOˆÂˆÙ]›ÙXİ˜]”›ÙXİ˜][Ñ›Š
NÂˆKˆÈ[[YYX]NˆYHKˆ
NÂÜØÜš\‚