<template>
  <SimpleContainer title="距离沪金交割日剩余时间">
    <div class="component-background h-100">
      <BasicTable :isScroll="false" @register="registerTable" body-padding="" />
    </div>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { computed } from 'vue';
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getCloseColumns } from '../data';
  import { getStrategySymbolInfo } from '@/api/future';
  import { useUserStore } from '@/store/modules/user';
  import { AccountType } from '@/views/account/detail/type';

  const userStore = useUserStore();
  const userProducts = computed(() => userStore.getUserInfoAccount);
  // 期货-账户
  const userProductsFuture = computed(() => {
    const _arr: any = [];
    userProducts.value?.forEach((itemProduct) => {
      if (itemProduct?.children?.length > 0) {
        itemProduct?.children?.forEach((itemChild) => {
          if (itemChild?.platform === AccountType.SHFE) {
            _arr.push(itemChild);
          }
        });
      }
    });
    return _arr;
  });
  // console.log('userProducts-----', userProducts);

  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    // dataSource: dataSoure,
    api: getStrategySymbolInfo,
    columns: getCloseColumns(),
    showIndexColumn: false,
    beforeFetch(params) {
      if (userProductsFuture.value.length == 1) {
        params['checkCode'] = userProductsFuture.value.map((item: any) => item.value).join(',');
      } else if (userProductsFuture.value.length > 1) {
        params['checkCodes'] = userProductsFuture.value.map((item: any) => item.value).join(',');
      }
      return params;
    },
    pagination: {
      // pageSize: 8,
      size: 'small',
      position: ['bottomCenter'],
    },
  });
</script>
