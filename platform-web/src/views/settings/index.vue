<template>
  <PageWrapper title="系统设置">
    <div class="settings-page">
      <ProductDataStatusAlert :meta="healthMeta" class="mb-4" />

      <Row :gutter="[16, 16]">
        <Col :xs="24" :xl="8">
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
              <Descriptions.Item label="会话来源">当前浏览器 Session</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col :xs="24" :xl="8">
          <Card :bordered="false" title="个人账号" class="vg-panel">
            <p class="card-copy">所有角色均可管理本人的资料、头像、密码、设备和会话。</p>
            <Button type="primary" @click="openPersonalAccount">进入个人账号</Button>
          </Card>
        </Col>

        <Col :xs="24" :xl="8">
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
              <Descriptions.Item label="截至时间">
                {{ health.as_of || '不可用' }}
              </Descriptions.Item>
              <Descriptions.Item label="来源">配置的 dataHttp origin</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <RestoredProductSurface
        class="mt-4"
        state="unavailable"
        source="not-configured:settings-write-owner"
        :actionable="false"
        message="设置 Application Service、Repository 与写入合同尚未配置；页面不会创建仅在浏览器生效的伪设置。"
      >
        <Card :bordered="false" title="平台偏好" class="vg-panel settings-options">
          <div>
            <span>通知策略</span>
            <Button v-if="canWrite" disabled>配置（Owner未配置）</Button>
            <Tag v-else>只读</Tag>
          </div>
          <div>
            <span>研究数据刷新</span>
            <Button v-if="canWrite" disabled>配置（Owner未配置）</Button>
            <Tag v-else>只读</Tag>
          </div>
          <div>
            <span>交易安全</span>
            <strong>Live Write关闭 · 安全门禁不可绕过</strong>
          </div>
        </Card>
      </RestoredProductSurface>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { Button, Card, Col, Descriptions, Row, Tag } from 'ant-design-vue';
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import {
    type ProductDataMeta,
    unavailableMeta,
  } from '@/api/platform/productDataState';
  import { type DataServiceHealth, getDataHealth } from '@/api/riskControl';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import { hasPermission } from '@/access/userAccess';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { useUserStore } from '@/store/modules/user';

  const router = useRouter();
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
  const canWrite = computed(() =>
    hasPermission(userStore.getAuthentication?.permissions || [], 'settings.write'),
  );
  const { roleLabel, roleColor } = useRoleAccess();

  function openPersonalAccount() {
    router.push('/account/index');
  }

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
    border-radius: 8px;
    box-shadow: 0 1px 3px rgb(15 23 42 / 6%);
  }

  .card-copy {
    min-height: 44px;
    color: #667085;
    line-height: 1.6;
  }

  .settings-options :deep(.ant-card-body) {
    display: grid;
    gap: 12px;
  }

  .settings-options :deep(.ant-card-body) > div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid #edf1f5;
  }

  .settings-options strong {
    color: #785a16;
    font-size: 12px;
  }

  @media (max-width: 768px) {
    .settings-page {
      padding: 12px;
    }
  }
</style>
