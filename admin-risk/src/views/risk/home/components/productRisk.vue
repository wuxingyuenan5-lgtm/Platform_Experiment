<template>
  <div>
    <div v-if="showProductHeader" class="component-background p-3 pb-4 mb-1">
      <div class="border-bottom pb-2">产品</div>
      <div class="flex pt-2 gap-16">
        <div>
          <div class="color-secondary h-20px text-xs">
            净值回撤
            <span class="text-10px">(过去24H)</span>
          </div>

          <div class="relative w-160px pb-3">
            <div class="leading-22px">{{ (productSource?.navShfeDrawdown * 100).toFixed(2) }}%</div>
            <ProgressLevel
              class="w-40 mt-1"
              :value="productSource?.navShfeDrawdown * 100"
              :levelList="productSource.drawdownProgressList"
              :reverse="true"
            />
            <!-- <div class="h-26px pb-1">
              <span class="absolute translate-x-[-50%]" :style="navShfeDrawdownStyle">
                {{ (productSource?.navShfeDrawdown * 100).toFixed(2) }}%</span
              >
            </div> -->
            <!-- <StaticSlider
              :levelList="productSource.drawdownProgressList"
              :value="Math.abs(productSource?.navShfeDrawdown * 100)"
              :max="10"
            /> -->
          </div>
        </div>
        <div>
          <div class="color-secondary pb-1 text-xs">总杠杆率</div>
          <div class="leading-22px">{{ (productSource?.levelRatio * 1).toFixed(2) }}%</div>
          <ProgressLevel
            class="w-40 mt-1"
            :value="(productSource?.levelRatio / 100).toFixed(2)"
            :levelList="productSource.levelRatioProgressList"
          />
        </div>
        <!-- 中性平衡 -->
        <div>
          <div class="color-secondary pb-1 text-xs">中性平衡</div>
          <div class="flex justify-between leading-22px">
            <div class="text-#C1272D">多{{ productSource?.deltaBalance }}%</div>
            <div class="text-#22B573">空{{ productSource?.deltaBalanceShort }}%</div>
          </div>
          <div class="mt-1">
            <div class="w-180px">
              <div class="bg-#22B573 h-1 rounded-full">
                <div
                  :style="{
                    height: '100%',
                    width: productSource.deltaBalance + '%',
                    background: '#C1272D',
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
        <!-- 净值/权益总资产净值比例 -->
        <div v-if="productSource.hasTotalNetworthRatio">
          <div class="color-secondary pb-1 text-xs">权益</div>
          <div class="flex justify-between leading-22px">
            <div class="text-#C1272D">国内{{ productSource?.futuresTotalNetworthRatio }}%</div>
            <div class="text-#22B573">海外{{ productSource?.cryptoTotalNetworthRatio }}%</div>
          </div>
          <div class="mt-1">
            <div class="w-180px">
              <div class="bg-#22B573 h-1 rounded-full">
                <div
                  :style="{
                    height: '100%',
                    width: productSource.futuresTotalNetworthRatio + '%',
                    background: '#C1272D',
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="flex gap-1 w-full">
      <div class="w-full">
        <BasicSkeleton
          :loading="loading && isFirst"
          :paragraph="{ rows: 6 }"
          :showEmpty="!dataSource.length"
        >
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
    </div>
  </div>
</template>

<script lang="tsx" setup>
  import riskPanel from './riskPanel.vue';
  import { Row, Col, Slider } from 'ant-design-vue';
  import { BasicSkeleton } from '@/components/skeleton';
  import { useProductRisk } from '@/views/risk/product/risk/hooks';
  import { computed, onMounted } from 'vue';
  import ProgressLevel from './progressLevel.vue';
  import StaticSlider from './staticSlider.vue';

  const props = defineProps({
    product: {
      type: Object,
      default: () => ({}),
    },
    isTiming: {
      type: Boolean,
      default: true,
    },
    showProductHeader: {
      type: Boolean,
      default: true,
    },
  });
  const productId = computed(() => props.product?.id);
  const { loading, isFirst, dataSource, productSource, artificialStop } = useProductRisk(
    productId,
    {
      isTiming: props.isTiming,
    },
  );

  onMounted(() => {
    artificialStop.value = !props.isTiming;
  });
  const navShfeDrawdownStyle = computed(() => {
    const _left = `${Math.max(Math.abs(productSource?.navShfeDrawdown * 100), 12)}%`;
    return {
      left: _left,
    };
  });
</script>
