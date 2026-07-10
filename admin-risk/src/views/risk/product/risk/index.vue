<template>
  <div>
    <div class="flex justify-between items-center">
      <div class="text-base leading-6 font-500 pb-1">产品因子</div>
      <LevelMarket />
    </div>
    <!-- 产品 -->
    <div v-if="showProductHeader" class="component-background p-3 pb-4 mb-1">
      <div class="flex justify-between items-center">
        <div class="border-bottom pb-2">产品</div>
        <div
          @click="openCalculator"
          class="cursor-pointer hover:text-#C1272D pb-2 flex items-center"
        >
          <CalculatorOutlined class="mr-1" />
          换算器
        </div>
      </div>

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
              :value="(productSource?.navShfeDrawdown * 100).toFixed(2)"
              :levelList="productSource.drawdownProgressList"
              :reverse="true"
            />
            <!-- <div class="h-26px pb-1">
              <span class="absolute translate-x-[-50%]" :style="navShfeDrawdownStyle">
                {{ (productSource?.navShfeDrawdown * 100).toFixed(2) }}%</span
              >
            </div>
            <StaticSlider
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
          :showEmpty="!productChildrenRisk.length"
        >
          <Spin :spinning="loading && !isFirst">
            <Row :gutter="4">
              <Col
                v-for="(item, i) in productChildrenRisk"
                :key="i"
                class="min-w-67 relative"
                :xxl="4"
                :xl="6"
              >
                <riskPanel
                  @click="changeActiveKey(i)"
                  :bgType="i == activeIndex ? 'default' : 'gary'"
                  class="cursor-pointer"
                  :record="item"
                />
                <div
                  :class="[
                    'absolute boottom-0 h-2 left-[2px] right-[2px]',
                    i == activeIndex ? 'component-background' : '',
                  ]"
                ></div>
              </Col>
              <Col flex="auto">
                <div class="content-bg h-full"></div>
              </Col>
            </Row>
          </Spin>
        </BasicSkeleton>
      </div>
    </div>
    <!-- 盘口 平仓 -->
    <div class="flex pt-2 h-650px items-stretch w-full">
      <OrderBook
        v-if="account?.platform == AccountType.BALANCE"
        class="w-80 shrink-0 component-background"
      />
      <OrderBookFuture
        v-else-if="account?.platform == AccountType.SHFE"
        class="w-80 shrink-0 component-background"
      />
      <div v-else class="w-80 component-background">
        <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
      </div>
      <div class="flex-1">
        <ClosePosition
          :showDoubleSide="showProductHeader"
          :product="product"
          :account="account"
          @success="closeSuccess"
        />
      </div>
    </div>
    <!-- 当前订单 -->
    <!-- <CurOrder ref="curOrderRef" :product="product" :account="account" class="pt-6" /> -->
    <!-- 平仓日志 -->
    <Log ref="logRef" :product="product" :account="account" class="pt-6" />
    <CalculatorModal ref="calculatorRef" />
  </div>
</template>
<script lang="tsx" setup>
  import LevelMarket from '@/views/risk/home/components/LevelMarket.vue';
  import riskPanel from '@/views/risk/home/components/riskPanel.vue';
  import { Row, Col, Empty, Spin } from 'ant-design-vue';
  import { ref, computed, onMounted, watch } from 'vue';
  import OrderBook from './components/OrderBook.vue';
  import OrderBookFuture from '@/views/bargain/future/components/OrderBook.vue';
  import ClosePosition from './components/ClosePosition.vue';
  import Log from './components/Log.vue';
  // import CurOrder from './components/CurOrder.vue';
  import { BasicSkeleton } from '@/components/skeleton';
  import { AccountType } from '@/views/account/detail/type';
  import CalculatorModal from './components/CalculatorModal.vue';
  import { CalculatorOutlined } from '@ant-design/icons-vue';
  import ProgressLevel from '@/views/risk/home/components/progressLevel.vue';
  import StaticSlider from '@/views/risk/home/components/staticSlider.vue';

  const props = defineProps({
    product: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    productSource: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    productChildren: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    productChildrenRisk: {
      type: Array as PropType<any>,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
    isFirst: {
      type: Boolean,
      default: false,
    },
    showProductHeader: {
      type: Boolean,
      default: true,
    },
  });

  const calculatorRef = ref();
  const logRef = ref();
  const activeKey = ref();
  const activeIndex = ref(0);
  const account = computed(() => {
    return (
      props.productChildrenRisk.find(
        (item, i) => item?.checkCode == activeKey.value && i == activeIndex.value,
      ) || {}
    );
  });
  const isFuture = computed(() => account.value?.platform == AccountType.SHFE);

  function changeActiveKey(index: number) {
    activeIndex.value = index;
    const key = props.productChildrenRisk[index]?.checkCode;
    activeKey.value = key;
  }
  watch(
    () => props.productChildrenRisk,
    (newVal) => {
      console.log('props.productChildrenRisk=====', props.productChildrenRisk);

      if (newVal.length && !activeKey.value) {
        activeKey.value = newVal[0]?.checkCode;
      }
    },
    {
      immediate: true,
    },
  );
  // console.log('productSource----------', props.productSource);

  function closeSuccess() {
    logRef.value?.reload();
  }
  function openCalculator() {
    calculatorRef.value?.openModal();
  }
  // onMounted(() => {
  //   console.log('productSource----------99999999', props.productSource);
  // });

  const navShfeDrawdownStyle = computed(() => {
    const _left = `${Math.max(Math.abs(props.productSource?.navShfeDrawdown * 100), 12)}%`;
    return {
      // left: `${Math.abs(productSource?.navShfeDrawdown * 100)}%`,
      left: _left,
    };
  });
</script>
