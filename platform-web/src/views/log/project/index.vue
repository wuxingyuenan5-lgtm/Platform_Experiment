<template>
  <div class="px-3 pb-3 flex flex-col" :style="boxStyle">
    <div class="flex justify-end pb-2">
      <Button type="primary" @click="refresh">刷新</Button>
    </div>
    <div ref="preRef" class="overflow-y-auto flex-1">
      <Spin wrapperClassName="h-full" :spinning="loading">
        <div class="h-120 flex justify-center items-center" v-if="!dataSource?.str">
          <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
        </div>
        <pre v-else class="whitespace-pre-wrap p-1"><template 
        v-for="(line, index) in formatLogData(dataSource?.str)" 
        :key="index"><div :class="['text-xs leading-5 mb-1', getLineClass(line)]">{{ line }}</div></template>
        </pre>
      </Spin>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { getProjectLogs } from '@/api/quantSystem';
  import { ref, onMounted, nextTick } from 'vue';

  import { Empty, Spin, Button } from 'ant-design-vue';

  const boxStyle = {
    height: 'calc(100vh - 140px)',
  };
  const loading = ref(true);
  const dataSource = ref();
  const preRef = ref();

  async function getProjectLogsFn() {
    try {
      loading.value = true;
      const res = await getProjectLogs();
      if (res.retCode == 0) {
        dataSource.value = res.data;
        nextTick(() => {
          preRef.value.scrollTop = preRef.value.scrollHeight;
        });
      }
    } catch (error) {
      console.log(error);
    } finally {
      loading.value = false;
    }
  }
  function formatLogData(str: string) {
    if (!str) return [];
    return str.split('\n').map((line) => line.trim());
  }
  function getLineClass(line: string) {
    if (line.includes('TRACE') || line.includes('trace')) {
      return 'log-trace';
    }
    if (line.includes('DEBUG') || line.includes('debug')) {
      return 'log-debug';
    }
    if (line.includes('ERROR') || line.includes('error')) {
      return 'log-error';
    }
    if (line.includes('SUCCESS') || line.includes('success')) {
      return 'log-success';
    }
    if (line.includes('WARN') || line.includes('warn')) {
      return 'log-warning';
    }
    if (line.includes('CRITICAL') || line.includes('critical')) {
      return 'log-critical';
    }
    return '';
  }
  onMounted(() => {
    getProjectLogsFn();
  });
  function refresh() {
    getProjectLogsFn();
  }
</script>
