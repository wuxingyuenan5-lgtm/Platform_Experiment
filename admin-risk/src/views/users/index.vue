<template>
  <PageWrapper title="用户管理">
    <div class="users-page">
      <Row :gutter="[16, 16]">
        <Col :xs="24" :lg="8">
          <Card :bordered="false" title="当前用户" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="用户 ID">{{ userInfo.userId || userInfo.sub || '-' }}</Descriptions.Item>
              <Descriptions.Item label="用户名">{{ userInfo.username || userInfo.name || '-' }}</Descriptions.Item>
              <Descriptions.Item label="角色">
                <Tag :color="roleColor">{{ roleLabel }}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="首页">{{ userInfo.homePath || '/home/index' }}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col :xs="24" :lg="16">
          <Card :bordered="false" title="角色权限矩阵" class="vg-panel">
            <Table
              row-key="key"
              size="small"
              :columns="permissionColumns"
              :data-source="permissionRows"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="isRoleColumn(column.key)">
                  <Tag :color="isAllowed(record, column.key) ? 'green' : 'default'">
                    {{ isAllowed(record, column.key) ? '可用' : '隐藏' }}
                  </Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
      </Row>

      <Card :bordered="false" title="登录后的界面差异" class="vg-panel mt-4">
        <div class="role-cards">
          <div class="role-card admin">
            <div class="role-title">管理员 admin</div>
            <div>完整菜单、账户新增、账户同步、用户/审计/设置。</div>
          </div>
          <div class="role-card employee">
            <div class="role-title">员工 employee</div>
            <div>业务菜单、账户查看和新增、账户同步、风控和报表。</div>
          </div>
          <div class="role-card guest">
            <div class="role-title">访客 guest</div>
            <div>总览、账户、数据和财务只读视图。</div>
          </div>
        </div>
      </Card>

      <Card v-if="isAdmin" :bordered="false" title="注册申请审核" class="vg-panel mt-4">
        <Table
          row-key="id"
          size="small"
          :columns="applicationColumns"
          :data-source="registrationRequests"
          :loading="loadingApplications"
          :pagination="{ pageSize: 8 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'requested_role'">
              <Tag :color="roleColorByValue(record.requested_role)">{{ roleName(record.requested_role) }}</Tag>
            </template>
            <template v-else-if="column.key === 'approval_status'">
              <Tag :color="record.approval_status === 'pending' ? 'orange' : 'default'">
                {{ record.approval_status }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Space>
                <Button type="link" size="small" @click="approve(record.id)">通过</Button>
                <Popconfirm title="确认拒绝该申请？" @confirm="reject(record.id)">
                  <Button danger type="link" size="small">拒绝</Button>
                </Popconfirm>
              </Space>
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Descriptions, message, Popconfirm, Row, Space, Table, Tag } from 'ant-design-vue';
  import { PageWrapper } from '@/components/Page';
  import { useUserStore } from '@/store/modules/user';
  import { ROLE_COLOR_MAP, ROLE_LABEL_MAP, useRoleAccess } from '@/hooks/web/useRoleAccess';
  import {
    approveRegistration,
    getRegistrationRequests,
    rejectRegistration,
  } from '@/api/sys/user';
  import type { RegistrationRequest } from '@/api/sys/model/userModel';

  const userStore = useUserStore();
  const { roleLabel, roleColor, isAdmin } = useRoleAccess();
  const userInfo = computed(() => userStore.getUserInfo as any);
  const loadingApplications = ref(false);
  const registrationRequests = ref<RegistrationRequest[]>([]);

  const permissionColumns = [
    { title: '模块', dataIndex: 'module', key: 'module' },
    { title: 'admin', dataIndex: 'admin', key: 'admin', width: 120 },
    { title: 'employee', dataIndex: 'employee', key: 'employee', width: 120 },
    { title: 'guest', dataIndex: 'guest', key: 'guest', width: 120 },
  ];

  const permissionRows = [
    { key: 'home', module: '首页总览', admin: true, employee: true, guest: true },
    { key: 'account', module: '账户查看', admin: true, employee: true, guest: true },
    { key: 'sync', module: 'Bybit 手动同步', admin: true, employee: true, guest: false },
    { key: 'createAccount', module: '新增账户', admin: true, employee: true, guest: false },
    { key: 'deleteAccount', module: '删除账户', admin: true, employee: false, guest: false },
    { key: 'risk', module: '风控/策略/报表/监控', admin: true, employee: true, guest: false },
    { key: 'admin', module: '用户/审计/设置', admin: true, employee: false, guest: false },
  ];

  const applicationColumns = [
    { title: '账号', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '申请身份', dataIndex: 'requested_role', key: 'requested_role', width: 110 },
    { title: '状态', dataIndex: 'approval_status', key: 'approval_status', width: 100 },
    { title: '申请时间', dataIndex: 'created_at', key: 'created_at', width: 190 },
    { title: '操作', key: 'action', width: 130 },
  ];

  function isRoleColumn(key: any) {
    return ['admin', 'employee', 'guest'].includes(String(key));
  }

  function isAllowed(record: any, key: any) {
    return !!record[String(key)];
  }

  function roleName(role: string) {
    return ROLE_LABEL_MAP[role] || role;
  }

  function roleColorByValue(role: string) {
    return ROLE_COLOR_MAP[role] || 'default';
  }

  async function loadRegistrationRequests() {
    if (!isAdmin.value) return;
    loadingApplications.value = true;
    try {
      registrationRequests.value = await getRegistrationRequests({ status: 'pending' });
    } catch (error: any) {
      message.error(error?.response?.data?.message || error?.message || '注册申请加载失败');
    } finally {
      loadingApplications.value = false;
    }
  }

  async function approve(id: number) {
    await approveRegistration(id);
    message.success('已通过申请');
    await loadRegistrationRequests();
  }

  async function reject(id: number) {
    await rejectRegistration(id, '管理员拒绝');
    message.success('已拒绝申请');
    await loadRegistrationRequests();
  }

  onMounted(loadRegistrationRequests);
</script>

<style scoped>
  .users-page {
    padding: 16px;
  }

  .vg-panel {
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .role-cards {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .role-card {
    border: 1px solid #e5e7eb;
    border-left-width: 4px;
    border-radius: 6px;
    padding: 14px;
    color: #364152;
    line-height: 1.7;
  }

  .role-card.admin {
    border-left-color: #d4380d;
  }

  .role-card.employee {
    border-left-color: #1677ff;
  }

  .role-card.guest {
    border-left-color: #8c8c8c;
  }

  .role-title {
    margin-bottom: 6px;
    color: #111827;
    font-weight: 600;
  }

  @media (max-width: 900px) {
    .role-cards {
      grid-template-columns: 1fr;
    }
  }
</style>
