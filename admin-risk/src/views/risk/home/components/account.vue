<template>
  <div>
    <div class="flex justify-between items-center">
      <div class="text-base leading-6 font-500 pb-1">{{ title }}</div>
      <LevelMarket />
    </div>
    <BasicSkeleton :loading="false" :paragraph="{ rows: 6 }" :showEmpty="!dataSource.length">
      <Row :gutter="4">
        <Col v-for="(item, i) in dataSource" :key="i" class="min-w-67" :xxl="4" :xl="6">
          <riskPanel :record="item" />
        </Col>

        <Col flex="auto">
          <div class="component-background h-full"></div>
        </Col>
      </Row>
    </BasicSkeleton>
  </div>
</template>
<script lang="tsx" setup>
  import LevelMarket from './LevelMarket.vue';
  // import productRisk from './productRisk.vue';
  import riskPanel from './riskPanel.vue';
  import { Row, Col, Slider } from 'ant-design-vue';
  import { BasicSkeleton } from '@/components/skeleton';

  const props = defineProps({
    title: {
      type: String,
      default: '产品概览',
    },
    dataSource: {
      type: Array as PropType<any>,
      default: () => [],
    },
  });
</script>
<style lang="less" scoped></style>
