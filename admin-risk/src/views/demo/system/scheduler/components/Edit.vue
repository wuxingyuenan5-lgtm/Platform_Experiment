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
  import { postSchedulerList } from '@/api/risk/scheduler';
  import { useApiBasic } from '@/hooks/web/useApi';

  const emit = defineEmits(['success', 'register']);

  const props = defineProps({
    record: { type: Object as PropType<any>, default: null },
  });
  const [registerEdit, { openModal }] = useModal();
  const title = ref('新增');

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
      curParams = { ..._params };
      if (props.record) {
        // curParams.jobId = props.record.jobId;
        curParams.action = 'update';
      } else {
        // curParams.jobId = 'web';
        curParams.action = 'create';
      }
      feakSave(curParams);
    });
  }

  async function feakSave(params: any) {
    const _params = JSON.parse(JSON.stringify(params));
    confirmLoading.value = true;
    useApiBasic({
      apiFn: postSchedulerList(_params),
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
