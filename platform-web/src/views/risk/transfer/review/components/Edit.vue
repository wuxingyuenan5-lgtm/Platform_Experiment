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
<script lang="ts" setup>
  import { watch, nextTick, ref } from 'vue';
  import { BasicModal, useModal } from '@/components/Modal';
  import { BasicForm, useForm } from '@/components/Form';
  import { schemas } from '../data';
  import { postManualReview } from '@/api/risk/transfer';
  import { useApiBasic } from '@/hooks/web/useApi';

  const emit = defineEmits(['success', 'register']);

  const props = defineProps({
    record: { type: Object as PropType<any>, default: null },
  });
  const [registerEdit, { openModal }] = useModal();
  const title = ref('同意');
  let curParams = {};
  const confirmLoading = ref(false);

  const [registerForm, { validate, setFieldsValue, resetFields, updateSchema, validateFields }] =
    useForm({
      baseColProps: {
        span: 24,
      },
      labelWidth: 100,
      schemas: schemas,
      showActionButtonGroup: false,
    });
  watch(
    () => props.record,
    (newValue) => {
      nextTick(() => {
        resetFields();
        if (newValue) {
          const _cur = JSON.parse(JSON.stringify(newValue));
          setFieldsValue(_cur);
          if (newValue.action === 'reject') {
            title.value = '驳回';
          } else {
            title.value = '同意';
          }
        }
      });
    },
  );

  function handleOk() {
    validate().then((res) => {
      const _params = res;
      curParams = { ..._params };
      feakSave(curParams);
    });
  }

  async function feakSave(params: any) {
    const _params = JSON.parse(JSON.stringify(params));
    confirmLoading.value = true;
    useApiBasic({
      apiFn: postManualReview(_params),
      successFn() {
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
