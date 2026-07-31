<template>
  <PageWrapper title="系统设置">
    <div class="settings-page">
      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="health.status === 'ok' ? 'green' : 'orange'"
            >data-service {{ health.status || 'unknown' }}</Tag
          >
        </Space>
        <Button :loading="loading" @click="loadSettings">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]">
        <Col :xs="24" :xl="10">
          <Card :bordered="false" title="当前登录" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="用户">{{
                userInfo.username || userInfo.name || '-'
              }}</Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag :color="roleColor">{{ roleLabel }}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="用户 ID">{{
                userInfo.userId || userInfo.sub || '-'
              }}</Descriptions.Item>
              <Descriptions.Item label="默认首页">{{
                userInfo.homePath || '/home/index'
              }}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col :xs="24" :xl="14">
          <Card :bordered="false" title="本地服务配置" class="vg-panel">
            <Table
              row-key="key"
              size="small"
              :columns="columns"
              :data-source="serviceRows"
              :loading="loading"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <Tag :color="record.color">{{ record.status }}</Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
      </Row>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Descriptions, Row, Space, Table, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import { DataServiceHealth, getDataHealth } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { useUserStore } from '@/store/modules/user';

  const loading = ref(false);
  const health = ref<DataServiceHealth>({
    status: 'unknown',
    service: 'data-service',
    update_frequency: '-',
  });
  const userStore = useUserStore();
  const userInfo = computed(() => userStore.getUserInfo as any);
  const { roleLabel, roleColor } = useRoleAccess();

  const serviceRows = computed(() => [
    {
      key: 'auth',
      name: 'auth-service',
      route: '/api/auth/*',
      target: 'Docker 内网 auth-service:8080',
      status: '已连接',
      color: 'green',
    },
    {
      key: 'data',
      name: 'data-service',
      route: '/api/data/*',
      target: 'Docker 内网 data-service:8082',
      status: health.value.status === 'ok' ? '已连接' : '异常',
      color: health.value.status === 'ok' ? 'green' : 'orange',
    },
    {
      key: 'risk',
      name: 'risk-service',
      route: '/api/auth/risk/api/v1/risk-records/',
      target: 'auth-service 兼容接口',
      status: '兼容模式',
      color: 'blue',
    },
    {
      key: 'notification',
      name: 'notification',
      route: '/api/auth/notifications/api/v1/messages/',
      target: 'auth-service 兼容接口',
      status: '兼容模式',
      color: 'blue',
    },
  ]);

  const columns = [
    { title: '服务', dataIndex: 'name', key: 'name' },
    { title: '前端路由', dataIndex: 'route', key: 'route' },
    { title: '目标', dataIndex: 'target', key: 'target' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 110 },
  ];

  async function loadSettings() {
    loading.value = true;
    try {
      health.value = await getDataHealth();
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
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  @media (max-width: 768px) {
    .settings-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
