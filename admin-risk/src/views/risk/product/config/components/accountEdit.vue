<template>
  <BasicModal
    @register="registerEdit"
    v-bind="$attrs"
    @ok="handleOk"
    :canFullscreen="false"
    :title="title"
    :confirmLoading="confirmLoading"
  >
    <BasicForm @register="registerForm" />
  </BasicModal>
</template>
<script lang="tsx" setup>
  import { schemasStrategy } from '../data';
  import { watch, nextTick, ref } from 'vue';
  import { BasicModal, useModal } from '@/components/Modal';
  import { BasicForm, useForm } from '@/components/Form';
  import { postAccountConfig } from '@/api/risk/settings';
  import { useApiBasic } from '@/hooks/web/useApi';

  const labelCol = { style: { width: '100px' } };
  const emit = defineEmits(['success']);
  const props = defineProps({
    record: { type: Object as PropType<any>, default: null },
    productId: {
      type: String,
      default: '',
    },
    accountId: {
      type: [String, Number],
      default: '',
    },
  });

  const [registerEdit, { openModal }] = useModal();
  const title = ref('新增');
  const confirmLoading = ref(false);
  let curParams: any = {};

  const [registerForm, { validate, setFieldsValue, resetFields, updateSchema, validateFields }] =
    useForm({
      baseColProps: {
        span: 24,
      },
      labelWidth: 100,
      schemas: schemasStrategy,
      showActionButtonGroup: false,
    });

  watch(
    () => props.record,
    (newValue) => {
      nextTick(() => {
        console.log('newValue===', newValue);
        if (newValue) {
          const _cur = JSON.parse(JSON.stringify(newValue));
          title.value = '编辑';
          setFieldsValue(_cur);
        } else {
          resetFields();
          title.value = '新增';
        }
      });
    },
  );
  function handleOk() {
    validate().then((res) => {
      const _params = res;
      curParams = { ..._params, productId: props.productId, accountId: props.accountId };
      if (props.record) {
        curParams.id = props.record.id;
        curParams.action = 'update';
      } else {
        curParams.action = 'create';
      }

      feakSave(curParams);
    });
  }
  async function feakSave(params: any) {
    useApiBasic({
      apiFn: postAccountConfig(params),
      successFn: (res) => {
        emit('success');
      },
      finallyFn() {
        confirmLoading.value = false;
      },
    });
  }

  defineExpose({
    openModal,
  });
</script>
