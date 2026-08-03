<template>
  <PageWrapper title="系统设置">
    <div class="settings-page">
      <ProductDataStatusAlert :meta="healthMeta" class="mb-4" />

      <Row :gutter="[16, 16]">
        <Col :xs="24" :xl="10">
          <Card :bordered="false" title="当前登录" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="用户">
                {{ userInfo.username || userInfo.name || '不可用' }}
              </Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag :color="roleColor">{{ roleLabel }}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="用户 ID">
                {{ userInfo.userId || userInfo.sub || '不可用' }}
              </Descriptions.Item>
              <Descriptions.Item label="会话来源">当前浏览器Session</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col :xs="24" :xl="14">
          <Card :bordered="false" title="数据服务状态" class="vg-panel">
            <div class="toolbar">
              <Tag :color="health.status === 'ok' ? 'green' : 'orange'">
                {{ health.service || 'data-service' }} {{ health.status || 'unavailable' }}
              </Tag>
              <Button :loading="loading" @click="loadSettings">
                <template #icon><ReloadOutlined /></template>
                刷新
              </Button>
            </div>
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="同步频率">
                {{ health.update_frequency || '不可用' }}
              </Descriptions.Item>
              <Descriptions.Item label="截至时间">{{ health.as_of || '不可用' }}</Descriptions.Item>
              <Descriptions.Item label="来源">配置的dataHttp origin</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <ProductNotConfiguredPanel
        class="mt-4"
        title="设置写入Owner尚未配置"
        description="当前没有正式的设置Application Service、Repository和写入合同。本页不展示固定Docker端口、推测服务连接状态，也不提供仅在浏览器生效的伪设置写入。"
        source="not-configured: settings-write-owner"
      />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Descriptions, Row, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';
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
  const healthMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'data-service health',
    unit: 'service status',
    timezone: 'source-defined',
    message: '尚未读取数据服务状态',
  });
  const userStore = useUserStore();
  const userInfo = computed(() => userStore.getUserInfo as Record<string, unknown>);
  const { roleLabel, roleColor } = useRoleAccess();

  async function loadSettings() {
    loading.value = true;
    try {
      health.value = await getDataHealth();
      healthMeta.value = {
        status: health.value.status === 'ok' ? 'ready' : 'unavailable',
        source: health.value.service || 'data-service',
        asOf: health.value.as_of,
        unit: 'service status',
        timezone: 'source-defined',
        errorCode: health.value.status === 'ok' ? undefined : 'provider_reported_unhealthy',
        message:
          health.value.status === 'ok'
            ? undefined
            : `Provider报告状态：${health.value.status || 'unknown'}`,
      };
    } catch (error) {
      healthMeta.value = unavailableMeta('data-service health', error, {
        unit: 'service status',
        timezone: 'source-defined',
      });
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadSettings);
</script>

<style scoped>
  .settings-page {
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
    height: 100%;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  @media (max-width: 768px) {
    .settings-page {
      padding: 12px;
    }
  }
</style>
