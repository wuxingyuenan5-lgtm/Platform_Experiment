<template>
  <PageWrapper title="系统监控">
    <div class="monitor-page">
      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
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
                <Tag :color="health.status === 'ok' ? 'green' : 'orange'">{{ health.status }}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="服务">{{ health.service }}</Descriptions.Item>
              <Descriptions.Item label="同步频率">{{ health.update_frequency }}</Descriptions.Item>
              <Descriptions.Item label="端口">8082</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col :xs="24" :md="12">
          <Card :bordered="false" title="auth-service" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="状态">
                <Tag color="green">已连接</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="登录用户">{{ userInfo.username || userInfo.name || '-' }}</Descriptions.Item>
              <Descriptions.Item label="角色">{{ roleLabel }}</Descriptions.Item>
              <Descriptions.Item label="端口">8080</Descriptions.Item>
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
  import { DataServiceHealth, getDataHealth } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { useUserStore } from '@/store/modules/user';

  const loading = ref(false);
  const health = ref<DataServiceHealth>({ status: 'unknown', service: 'data-service', update_frequency: '-' });
  const { roleLabel, roleColor } = useRoleAccess();
  const userStore = useUserStore();
  const userInfo = computed(() => userStore.getUserInfo as any);

  async function loadHealth() {
    loading.value = true;
    try {
      health.value = await getDataHealth();
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
</style>
