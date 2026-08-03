<template>
  <div>
    <strategyElm v-if="showStrategy" :productId="productId" class="mb-6" />
    <accountElm :account="account" v-if="!showStrategy" :productId="productId" />
  </div>
</template>
<script lang="tsx" setup>
  import strategyElm from './components/strategy.vue';
  import accountElm from './components/account.vue';
  import { useRoute } from 'vue-router';
  import { computed } from 'vue';

  const props = defineProps({
    showStrategy: {
      type: Boolean,
      default: true,
    },
    account: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
  });

  const route = useRoute();
  const productId = computed(() => {
    // 切割字符串最后一个/后的值
    return route.path.split('/').pop();
  });
</script>
