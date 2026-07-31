<template>
  <div class="component-background" style="height: calc(100% - 42px)">
    <!-- header  -->
    <div v-if="isOrder" class="flex justify-between items-center pr-3">
      <!-- <BasicTabs class="pl-1.5" size="small" v-model:value="tabVal" :options="tabsOptions" /> -->
      <!-- <Select
        class="has-fill"
        @change="change"
        v-model:value="selectVal"
        size="small"
        style="min-width: 80px"
        :disabled="scaleOptions.length == 0"
        :options="(scaleOptions as any)"
      /> -->
    </div>
    <!-- body  -->
    <div>
      <Empty
        v-if="isEmptyData"
        class="mx-auto pt-10"
        :style="{ marginBlock: '0' }"
        :image="Empty.PRESENTED_IMAGE_SIMPLE"
      />
      <div v-else class="order">
        <div class="order-header">
          <component
            :is="renderItem(OrderType.HEADER, ['价格(CNY)', '数量', isOrder ? '' : '时间'])"
          />
        </div>
        <div class="order-body">
          <template v-if="isOrder">
            <div v-if="tabVal != TabType.SELL" class="order-buy">
              <component
                v-for="(item, index) in record.buy.slice(0, showLen)"
                :key="index"
                :is="renderItem(OrderType.BUY, item)"
              />
            </div>
            <div v-if="tabVal == TabType.BUYSELL" :class="['order-balance', balance.type]">
              {{ balance.value }}
            </div>
            <div v-if="tabVal != TabType.BUY" class="order-sell">
              <component
                v-for="(item, index) in record.sell.slice(0, showLen)"
                :key="index"
                :is="renderItem(OrderType.SELL, item)"
              />
            </div>
          </template>
          <template v-else>
            <div class="order-deal">
              <component
                v-for="(item, index) in record?.deal"
                :key="index"
                :is="
                  renderItem(
                    Number(record?.deal[index]?.price || 0) <
                      Number(record?.deal[index + 1]?.price || 0)
                      ? OrderType.BUY
                      : OrderType.SELL,
                    item,
                  )
                "
              />
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="tsx" setup>
  import { ref, reactive, watch, computed } from 'vue';
  import { BasicTabs } from '@/components/Tabs/index';
  import { Select, Empty } from 'ant-design-vue';
  import { isEmpty } from 'lodash-es';
  import { formatToTime } from '@/utils/dateUtil';

  enum OrderType {
    BUY = 'buy',
    SELL = 'sell',
    HEADER = 'header',
  }
  enum TabType {
    BUYSELL = 'buysell',
    BUY = 'buy',
    SELL = 'sell',
  }
  const emit = defineEmits(['change']);
  const props = defineProps({
    type: {
      type: String,
      default: 'Order',
    },
    dataSource: {
      type: Object,
      default: () => ({}),
    },
    dataSourceOther: {
      type: Object,
      default: () => ({}),
    },
    scaleOptions: {
      type: Array,
      default: () => [],
    },
  });
  const record = reactive({
    buy: [],
    sell: [],
    deal: [],
  });
  const isEmptyData = ref(true);
  const isOrder = computed(() => props.type == 'Order');
  const showLen = computed(() => {
    return tabVal.value == TabType.BUYSELL ? 5 : 20;
  });
  const emptyArray = new Array(20).fill(['', '', '']);
  const balance = reactive({
    value: '',
    type: '',
  });
  watch(
    () => props.dataSource,
    (cur) => {
      if (isEmpty(cur)) {
        isEmptyData.value = true;
      } else {
        isEmptyData.value = false;
        if (isOrder.value) {
          let _buyArr = cur.a.reverse();
          let _sellArr = cur.b;
          if (_buyArr?.length < showLen.value) {
            _buyArr = _buyArr.concat(emptyArray).slice(0, 10).reverse();
          }
          if (_sellArr?.length < showLen.value) {
            _sellArr = _sellArr.concat(emptyArray);
          }
          record.buy = _buyArr;
          record.sell = _sellArr;
          if (!isEmpty(props.dataSourceOther)) {
            const _list = props.dataSourceOther?.list;
            if (_list?.length) {
              const _first = _list[0],
                _second = _list[1];
              balance.type =
                Number(_first?.price || 0) > Number(_second?.price || 0) ? 'green' : 'red';
              balance.value = _first?.price;
            }
          }
          // console.log('777777777-----');
        } else {
          // console.log('999999-----');

          record.deal = cur?.list;
        }
      }
    },
  );
  const tabVal = ref(TabType.BUYSELL);
  const selectVal = ref('');
  watch(
    () => props.scaleOptions,
    (cur: any) => {
      if (cur?.length > 0) {
        selectVal.value = cur[0]?.value;
      }
    },
    { immediate: true },
  );

  const tabsOptions = [
    {
      value: TabType.BUYSELL,
      label: '买卖盘',
    },
    {
      value: TabType.SELL,
      label: '买盘',
    },
    {
      value: TabType.BUY,
      label: '卖盘',
    },
  ];

  function renderItem(type: OrderType, data: any) {
    let _first = data[0],
      _second = data[1],
      _third = data[2];
    if (!isOrder.value && type != OrderType.HEADER) {
      (_first = data?.price), (_second = data?.size), (_third = formatToTime(Number(data?.time)));
    }
    return (
      <div class={`flex px-3 leading-6 order-item-${type}`}>
        <div class="flex-1 price">{_first || '--'}</div>
        <div class="text-right ml-4 flex-1">{_second || '--'}</div>
        {!isOrder.value && <div class="text-right flex-1">{_third || '--'}</div>}
      </div>
    );
  }
  function change(value: any) {
    emit('change', value);
  }
</script>
<style lang="less" scoped>
  @red-color: #ff5260ff;
  @green-color: #00ae93ff;

  .order-header {
    color: @text-color-base;
    font-size: 12px;
  }

  .order-buy,
  .order-item-buy {
    color: @text-color-base;
    font-size: 12px;
  }

  .order-item-buy {
    &:hover {
      background-color: fade(@red-color, 20%);
      cursor: pointer;
    }

    .price {
      color: @red-color;
    }
  }

  .order-sell,
  .order-item-sell {
    color: @text-color-base;
    font-size: 12px;
  }

  .order-item-sell {
    &:hover {
      background-color: fade(@green-color, 20%);
      cursor: pointer;
    }

    .price {
      color: @green-color;
    }
  }

  .order-balance {
    padding: 0 12px;
    font-size: 16px;
    font-weight: bold;
    line-height: 24px;

    &.green {
      color: @green-color;
    }

    &.red {
      color: @red-color;
    }
  }
</style>
