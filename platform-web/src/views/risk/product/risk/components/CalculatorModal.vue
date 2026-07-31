<template>
  <BasicModal
    title="换算器"
    size="small"
    @register="registerEdit"
    v-bind="$attrs"
    :canFullscreen="false"
    width="360px"
    :bodyStyle="{ marginTop: '-12px' }"
    :confirmLoading="confirmLoading"
    :draggable="true"
    :footer="null"
  >
    <div class="h-60">
      <BasicForm class="small-margin" @register="registerForm">
        <template #directionSlot="{ model, field }">
          <FormItem>
            <div class="flex gap-2 items-center">
              <div class="flex-1">
                <div>从</div>
                <Select
                  v-model:value="formState.direction1"
                  class="w-full"
                  :options="directionOptions"
                  popupClassName="z-9999"
                />
              </div>
              <div>
                <div>&nbsp;</div>
                <SwapOutlined @click="changeDirection" class="cursor-pointer hover:text-#C1272D" />
              </div>
              <div class="flex-1">
                <div>到</div>
                <Select
                  v-model:value="formState.direction2"
                  class="w-full"
                  :options="directionOptions2"
                  popupClassName="z-9999"
                />
              </div>
            </div>
          </FormItem>
        </template>
        <template #qtySlot="{ model, field }">
          <FormItem label="数量">
            <div class="flex gap-2 items-center">
              <div class="flex-1">
                <Input placeholder="请输入" v-model:value="formState.qty1" />
              </div>
              <div>
                <div>&nbsp;</div>
                <SwapOutlined class="opacity-0" />
              </div>
              <div class="flex-1">
                <Input disabled v-model:value="convertedQty" />
              </div>
            </div>
          </FormItem>
        </template>
      </BasicForm>
    </div>
  </BasicModal>
</template>
<script lang="tsx" setup>
  import { BasicModal, useModal } from '@/components/Modal';
  import { watch, reactive, ref, nextTick, computed } from 'vue';
  import { BasicForm, useForm } from '@/components/Form';
  import { getCalculatorColumns } from '../data';
  import { getConverter } from '@/api/risk/execution';
  import { SwapOutlined } from '@ant-design/icons-vue';
  import { Select, FormItem, Input } from 'ant-design-vue';
  import { directionOptions } from '@/utils/options/basicOptions';
  import { watchDebounced } from '@vueuse/shared';

  const [registerEdit, { openModal, getOpen }] = useModal();
  const confirmLoading = ref(false);
  const dataSoure = ref();
  const convertedQty = ref();
  const formState = reactive({
    direction1: 'futures_to_mt5',
    direction2: 'mt5_to_futures',
    qty1: undefined,
  });
  const directionOptions2 = computed(() => {
    return directionOptions.filter((item) => item.value != formState.direction1);
  });
  const [registerForm, { getFieldsValue }] = useForm({
    baseColProps: {
      span: 24,
    },
    schemas: getCalculatorColumns(),
    layout: 'vertical',
    showActionButtonGroup: false,
  });
  function handleOk() {
    const _params = {
      qty: formState.qty1,
      direction: formState.direction1,
      symbol: getFieldsValue().symbol,
    };
    getConverter(_params)
      .then((res) => {
        if (res.retCode == 0) {
          convertedQty.value = res.data?.convertedQty;
        }
      })
      .finally(() => {
        confirmLoading.value = false;
      });
  }
  watch(
    () => formState.direction1,
    () => {
      formState.direction2 = directionOptions2.value[0].value;
    },
  );
  watchDebounced(
    () => formState,
    (val) => {
      if (!val.qty1) return;
      handleOk();
    },
    { debounce: 500, deep: true },
  );
  function changeDirection() {
    [formState.direction1, formState.direction2] = [formState.direction2, formState.direction1];
  }
  defineExpose({
    openModal,
  });
</script>
