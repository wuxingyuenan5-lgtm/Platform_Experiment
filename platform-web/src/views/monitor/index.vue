<template>
  <PageWrapper title="系统监控">
    <div class="monitor-page">
      <ProductDataStatusAlert :meta="dataMeta" class="mb-4" />

      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag>只读诊断</Tag>
        </Space>
        <Button :loading="loading" @click="loadHealth">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]">
        <Col :xs="24" :md="12">
          <Card :bordered="false" title="data-service" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="状态">
                <Tag :color="health.status === 'ok' ? 'green' : 'orange'">
                  {{ health.status || 'unavailable' }}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="服务">{{ health.service || 'data-service' }}</Descriptions.Item>
              <Descriptions.Item label="同步频率">
                {{ health.update_frequency || '不可用' }}
              </Descriptions.Item>
              <Descriptions.Item label="截至时间">{{ health.as_of || '不可用' }}</Descriptions.Item>
              <Descriptions.Item label="来源">配置的dataHttp origin</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col :xs="24" :md="12">
          <Card :bordered="false" title="当前认证会话" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="状态">
                <Tag :color="authenticated ? 'green' : 'orange'">
                  {{ authenticated ? 'authenticated' : 'unavailable' }}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="登录用户">
                {{ userInfo.username || userInfo.name || '不可用' }}
              </Descriptions.Item>
              <Descriptions.Item label="角色">{{ roleLabel }}</Descriptions.Item>
              <Descriptions.Item label="来源">当前浏览器Session</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Descriptions, Row, Space, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import { type DataServiceHealth, getDataHealth } from '@/api/riskControl';
  import {
    unavailableMeta,
    type ProductDataMeta,
  } from '@/api/platform/productDataState';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { useUserStore } from '@/store/modules/user';

  const loading = ref(false);
  const health = ref<DataServiceHealth>({
    status: 'unknown',
    service: 'data-service',
    update_frequency: 'unknown',
  });
  const dataMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'data-service health',
    timezone: 'source-defined',
    unit: 'service status',
    message: '尚未读取服务状态',
  });
  const { roleLabel, roleColor } = useRoleAccess();
  const userStore = useUserStore();
  const userInfo = computed(() => userStore.getUserInfo as Record<string, unknown>);
  const authenticated = computed(() => Boolean(userInfo.value?.username || userInfo.value?.name));

  async function loadHealth() {
    loading.value = true;
    try {
      health.value = await getDataHealth();
      dataMeta.value = {
        status: health.value.status === 'ok' ? 'ready' : 'unavailable',
        source: health.value.service || 'data-service',
        asOf: health.value.as_of,
        timezone: 'source-defined',
        unit: 'service status',
        errorCode: health.value.status === 'ok' ? undefined : 'provider_reported_unhealthy',
        message:
          health.value.status === 'ok'
            ? undefined
            : `Provider报告状态：${health.value.status || 'unknown'}`,
      };
    } catch (error) {
      health.value = {
        status: 'unavailable',
        service: 'data-service',
        update_frequency: 'unknown',
      };
      dataMeta.value = unavailableMeta('data-service health', error, {
        timezone: 'source-defined',
        unit: 'service status',
      });
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadHealth);
</script>

<style scoped>
  .monitor-page {
    padding: 16px;
  }

  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .vg-panel {
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  @media (max-width: 768px) {
    .monitor-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
