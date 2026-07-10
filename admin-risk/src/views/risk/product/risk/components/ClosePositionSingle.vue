<template>
  <BasicModal
    size="small"
    @register="registerEdit"
    v-bind="$attrs"
    :canFullscreen="false"
    :footer="null"
    width="344px"
    :bodyStyle="{ marginTop: '-12px' }"
    :confirmLoading="confirmLoading"
    :draggable="true"
  >
    <template #title>
      <div class="font-400 leading-22px flex items-center">
        {{ isSingle ? '单边' : '双边' }}平仓-{{ record?.currency || record?.symbol }}
        <div v-if="isSingle && record?.category" class="flex">
          -
          <div :class="[record?.category == 'spot' ? 'text-#2c97ebff' : 'text-#eb6e2cff']">{{
            record?.category == 'spot' ? '现货' : '期货'
          }}</div>
        </div>
      </div>
    </template>

    <BasicForm class="small-margin" @register="registerForm">
      <template #quantitySlot="{ model, field }">
        <FormItem :name="field" required :rules="{ required: true, message: '请输入平仓数量' }">
          <template #label>
            <div class="color-secondary text-xs">平仓数量</div>
          </template>
          <div class="px-2">
            <SliderInput
              v-model:value="model[field]"
              :total="sliderInputConfig.total"
              :imput-props="sliderInputConfig.imputProps"
              :show-btn="false"
              @change="changeSlider"
            />
          </div>
        </FormItem>
      </template>
    </BasicForm>
    <Button :loading="loading" @click="sunmit" type="primary" class="w-full mb-2">
      <span class="text-xs">平仓</span>
    </Button>
  </BasicModal>
</template>
<script lang="tsx" setup>
  import { watch, reactive, ref, nextTick } from 'vue';
  import { BasicModal, useModal } from '@/components/Modal';
  import { BasicForm, useForm } from '@/components/Form';
  import {
    getSingleCloseColumns,
    getSingleCloseSHFEColumns,
    getSingleCloseMt5Columns,
  } from '../data';
  import { AccountType } from '@/views/account/detail/type';
  import { Button, message, FormItem } from 'ant-design-vue';
  import SliderInput from '@/components/Input/SliderInput.vue';
  import { useSymbolRisk } from '@/utils/options/useBasicOptions';

  const { options } = useSymbolRisk();
  const emits = defineEmits(['submit']);
  const props = defineProps({
    record: { type: Object as PropType<any>, default: null },
    type: { type: String as PropType<string>, default: AccountType.BALANCE },
    isSingle: { type: Boolean as PropType<boolean>, default: true }, // 单边平仓
  });
  const loading = ref(false);
  const sliderInputConfig = reactive({
    total: 100,
    imputProps: {
      step: 0,
      precision: 0,
      size: 'large',
      placeholder: '请输入平仓数量',
    },
  });
  const [registerEdit, { openModal, getOpen }] = useModal();

  const [registerForm, { validate, resetSchema, resetFields, updateSchema, validateFields }] =
    useForm({
      baseColProps: {
        span: 24,
      },
      schemas: getSingleCloseColumns(),
      layout: 'vertical',
      showActionButtonGroup: false,
    });
  // const title = ref('单边平仓');
  const confirmLoading = ref(false);

  watch(
    () => props.record,
    (newVal) => {
      console.log('---------9', newVal);

      nextTick(() => {
        resetFields();
        if (props.type == AccountType.BALANCE) {
          resetSchema(getSingleCloseColumns());
          sliderInputConfig.total = newVal?.size;
          const _len = (newVal?.size?.toString().split('.')[1] || '').length;
          const _symbol = options.value?.find((item) => item.symbol == newVal?.symbol);
          sliderInputConfig.imputProps.precision = _len;
          if (_symbol) {
            sliderInputConfig.imputProps.precision = (
              _symbol?.lotSize?.toString().split('.')[1] || ''
            ).length;
            sliderInputConfig.imputProps.step = _symbol?.lotSize * 1;
          }
        } else if (props.type == AccountType.SHFE) {
          resetSchema(getSingleCloseSHFEColumns());
          sliderInputConfig.total = newVal?.size;
          sliderInputConfig.imputProps.precision = 0;
          sliderInputConfig.imputProps.step = 1;
        } else if (props.type == AccountType.MT5) {
          resetSchema(getSingleCloseMt5Columns());
          sliderInputConfig.total = newVal?.size;
          const _len = (newVal?.size?.toString().split('.')[1] || '').length;
          const _symbol = options.value?.find((item) => item.symbol == newVal?.symbol);
          sliderInputConfig.imputProps.precision = _len;
          if (_symbol) {
            sliderInputConfig.imputProps.precision = (
              _symbol?.lotSize?.toString().split('.')[1] || ''
            ).length;
            sliderInputConfig.imputProps.step = _symbol?.lotSize * 1;
          }
        }
        console.log('sliderInputConfig----', sliderInputConfig);
      });
    },
  );
  function sunmit() {
    validate().then((res) => {
      if (!res.quantity) {
        message.warning('请输入平仓数量');
        return;
      }
      loading.value = true;
      const _params = {
        ...res,
        record: props.record,
        type: props.isSingle ? 'single' : 'double',
      };
      emits('submit', _params);
    });
  }
  function changeSlider(params) {
    validateFields(['quantity']);
  }
  function reset() {
    loading.value = false;
  }
  watch(
    () => getOpen,
    () => {
      reset();
    },
    { deep: true },
  );
  defineExpose({
    openModal,
  });
</script>
