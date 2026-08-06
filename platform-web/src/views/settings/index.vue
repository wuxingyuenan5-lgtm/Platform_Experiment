<template>
  <PageWrapper title="系统设置">
    <main class="settings-page" data-testid="settings-original-structure">
      <header class="settings-identity">
        <div><span>SYSTEM SETTINGS</span><h1>系统设置</h1></div>
        <div class="toolbar">
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="health.status === 'ok' ? 'green' : 'orange'">
            data-service {{ health.status || 'unknown' }}
          </Tag>
          <Button :loading="loading" @click="loadSettings">
            <template #icon><ReloadOutlined /></template>
            刷新
          </Button>
        </div>
      </header>

      <ProductDataStatusAlert :meta="healthMeta" />

      <Row :gutter="[16, 16]">
        <Col :xs="24" :xl="9">
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
              <Descriptions.Item label="默认首页">
                {{ userInfo.homePath || '/home/index' }}
              </Descriptions.Item>
              <Descriptions.Item label="会话来源">当前浏览器 Session</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col :xs="24" :xl="15">
          <Card :bordered="false" title="本地服务配置" class="vg-panel">
            <div class="service-table-wrap">
              <table class="service-table">
                <thead>
                  <tr><th>服务</th><th>正式接口</th><th>当前来源</th><th>状态</th></tr>
                </thead>
                <tbody>
                  <tr v-for="item in serviceRows" :key="item.name">
                    <td>{{ item.name }}</td>
                    <td>{{ item.route }}</td>
                    <td>{{ item.target }}</td>
                    <td
                      ><Tag :color="item.color">{{ item.status }}</Tag></td
                    >
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        </Col>
      </Row>

      <section class="account-grid" aria-label="个人账号自助管理">
        <article v-for="item in accountServices" :key="item.title">
          <component :is="item.icon" />
          <div
            ><strong>{{ item.title }}</strong
            ><p>{{ item.note }}</p></div
          >
          <Button @click="openPersonalAccount">进入个人账号</Button>
        </article>
      </section>

      <Row :gutter="[16, 16]">
        <Col :xs="24" :xl="8">
          <Card :bordered="false" title="数据服务状态" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="服务">
                {{ health.service || 'data-service' }}
              </Descriptions.Item>
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
        <Col :xs="24" :xl="16">
          <RestoredProductSurface
            state="unavailable"
            source="not-configured:settings-write-owner"
            :actionable="false"
            message="没有真实 Owner 的设置项保留原布局但禁止保存；页面不会伪造保存成功。"
          >
            <Card :bordered="false" title="平台偏好" class="vg-panel settings-options">
              <div>
                <span>通知策略</span>
                <Button disabled data-write-action="true">配置（Owner未配置）</Button>
              </div>
              <div>
                <span>研究数据刷新</span>
                <Button disabled data-write-action="true">配置（Owner未配置）</Button>
              </div>
              <div>
                <span>外观与布局偏好</span>
                <Button disabled data-write-action="true">保存（Owner未配置）</Button>
              </div>
              <div>
                <span>交易安全</span>
                <strong>Live Write关闭 · 审批、Kill Switch、Allowlist与风险门禁不可绕过</strong>
              </div>
            </Card>
          </RestoredProductSurface>
        </Col>
      </Row>
    </main>
  </PageWrapper>
</template>

<script setup lang="ts">
  import {
    DesktopOutlined,
    KeyOutlined,
    ReloadOutlined,
    SafetyCertificateOutlined,
    UserOutlined,
  } from '@ant-design/icons-vue';
  import { Button, Card, Col, Descriptions, Row, Tag } from 'ant-design-vue';
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { type ProductDataMeta, unavailableMeta } from '@/api/platform/productDataState';
  import { type DataServiceHealth, getDataHealth } from '@/api/riskControl';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { useUserStore } from '@/store/modules/user';

  interface SettingsSessionIdentity {
    username?: string;
    name?: string;
    userId?: string | number;
    sub?: string | number;
    homePath?: string;
  }

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
  const userInfo = computed<SettingsSessionIdentity>(
    () => userStore.getUserInfo as SettingsSessionIdentity,
  );
  const { roleLabel, roleColor } = useRoleAccess();

  const accountServices = [
    { title: '本人资料与头像', note: '读取和更新本人资料、姓名与头像。', icon: UserOutlined },
    { title: '密码与安全', note: '管理本人密码和安全验证。', icon: KeyOutlined },
    { title: '设备与会话', note: '查看本人设备、会话并执行自助管理。', icon: DesktopOutlined },
    {
      title: '账号边界',
      note: '所有角色仅通过个人账号入口管理本人资源。',
      icon: SafetyCertificateOutlined,
    },
  ];

  const serviceRows = computed(() => [
    {
      name: 'platform-api',
      route: '/api/v1/*',
      target: 'Platform API',
      status: '正式接口',
      color: 'green',
    },
    {
      name: 'data-service',
      route: 'dataHttp origin',
      target: health.value.service || 'data-service',
      status: health.value.status === 'ok' ? '已连接' : '不可用',
      color: health.value.status === 'ok' ? 'green' : 'orange',
    },
    {
      name: 'execution-runtime',
      route: '/runtime/*',
      target: 'Execution Runtime',
      status: 'Live Write关闭',
      color: 'blue',
    },
  ]);

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

<style scoped lang="less">
  .settings-page {
    display: grid;
    gap: 16px;
    padding: 16px;
  }

  .settings-identity {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    padding: 18px 20px;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #fff;
  }

  .settings-identity span {
    color: #6c8fb1;
    font-size: 11px;
    letter-spacing: 0.15em;
  }

  h1 {
    margin: 4px 0 0;
    font-size: 25px;
  }

  .toolbar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .vg-panel {
    height: 100%;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .service-table-wrap {
    overflow: auto;
  }

  .service-table {
    width: 100%;
    border-collapse: collapse;
  }

  .service-table th,
  .service-table td {
    padding: 11px;
    border-bottom: 1px solid #edf1f5;
    text-align: left;
    white-space: nowrap;
  }

  .service-table th {
    color: #778396;
    font-size: 12px;
  }

  .account-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .account-grid article {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: start;
    gap: 11px;
    padding: 16px;
    border: 1px solid #e2e8f0;
    border-radius: 13px;
    background: #fff;
  }

  .account-grid article > span {
    margin-top: 3px;
    color: #4d6f92;
    font-size: 20px;
  }

  .account-grid p {
    margin: 4px 0 10px;
    color: #667085;
    line-height: 1.55;
  }

  .account-grid button {
    grid-column: 2;
    justify-self: start;
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
    text-align: right;
  }

  @media (max-width: 1100px) {
    .account-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 680px) {
    .settings-identity {
      align-items: stretch;
      flex-direction: column;
    }

    .account-grid {
      grid-template-columns: 1fr;
    }

    .settings-options :deep(.ant-card-body) > div {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
