<template>
  <BasicModal @register="registerEdit" v-bind="$attrs" :canFullscreen="false" title="详情">
    <div v-for="(value, i) in dataSource" :key="value" class="flex">
      <div class="mb-1">{{ i }}：</div>
      <div class="font-bold">{{ value || '- -' }}</div>
    </div>
  </BasicModal>
</template>
<script lang="tsx" setup>
  import { watch, ref } from 'vue';
  import { BasicModal, useModal } from '@/components/Modal';
  import { getExecutionTasksDetail } from '@/api/risk/execution';

  const props = defineProps({
    record: { type: Object as PropType<any>, default: null },
  });
  const [registerEdit, { openModal }] = useModal();
  const dataSource = ref();
  watch(
    () => props.record,
    (newValue) => {
      console.log('newValue', newValue);
      getExecutionTasksDetailFn();
    },
  );
  function getExecutionTasksDetailFn() {
    console.log(2222);

    getExecutionTasksDetail({ id: props.record.id }).then((res) => {
      if (res.retCode == 0) {
        dataSource.value = res.data?.[0];
      }
    });
  }
  defineExpose({
    openModal,
  });
</script>
