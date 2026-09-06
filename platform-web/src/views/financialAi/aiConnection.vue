<template>
  <PageWrapper title="接入AI">
    <main class="page">
      <section class="mode-grid">
        <button
          class="mode-card"
          :class="{ active: form.mode === 'api' }"
          @click="selectMode('api')"
          ><span class="mode-copy"
            ><b>API 接入</b
            ><small>网页填写后由 platform-api 自动保存到本机；浏览器不保存密钥。</small></span
          ><i>{{ form.mode === 'api' ? '✓' : '' }}</i></button
        >
        <button
          class="mode-card"
          :class="{ active: form.mode === 'subscription' }"
          @click="selectMode('subscription')"
          ><span class="mode-copy"
            ><b>订阅接入</b
            ><small>调用本机已登录的 Claude Code / Qwen / DeepSeek / Codex。</small></span
          ><i>{{ form.mode === 'subscription' ? '✓' : '' }}</i></button
        >
      </section>
      <section v-if="form.mode === 'api'" class="card form-card">
        <label class="full"
          >选择模型<select
            v-model="apiForm.preset"
            :disabled="!canManageConnection"
            @change="applyPreset"
            ><option value="deepseek-v4-flash"
              >DeepSeek V4 Flash —— DeepSeek 官方 · 快而省 · 思考/非思考双模</option
            ><option value="custom">任意 OpenAI 兼容端点</option></select
          ></label
        >
        <label
          >Base URL<input
            v-model.trim="apiForm.baseUrl"
            :disabled="!canManageConnection"
            placeholder="https://api.deepseek.com"
        /></label>
        <label
          >Model<input
            v-model.trim="apiForm.model"
            :disabled="!canManageConnection"
            placeholder="deepseek-v4-flash"
        /></label>
        <label class="full"
          >API Key<input
            v-model="apiForm.apiKey"
            type="password"
            name="financial-ai-api-token"
            autocomplete="new-password"
            data-1p-ignore="true"
            data-lpignore="true"
            data-form-type="other"
            :disabled="!canManageConnection"
            :placeholder="deployment.hasApiKey ? '已保存在本机后端；留空保持原 Key' : 'sk-...'"
        /></label>
        <p class="hint full"
          >{{ deployment.message }} 密钥保存在本机
          <code>platform-api/data</code> 忽略目录，不返回浏览器、数据库、日志或仓库。</p
        >
        <p v-if="!canManageConnection" class="hint full"
          >当前账号可查看状态和使用已配置的分析能力，但无权修改机器级 API 配置。</p
        >
      </section>
      <section v-else class="card"
        ><p class="eyebrow">LOCAL SUBSCRIPTION</p><h2>选择本机 AI CLI</h2
        ><div class="cli-grid"
          ><button
            v-for="item in cliOptions"
            :key="item.key"
            class="cli-card"
            :class="{ selected: form.cli === item.key }"
            @click="form.cli = item.key"
            ><b>{{ item.name }}</b
            ><small>{{ item.note }}</small
            ><span :class="capability(item.key)?.available ? 'ok' : 'muted'">{{
              capability(item.key)?.status || '尚未检测'
            }}</span></button
          ></div
        ></section
      >
      <section class="card gateway-card"
        ><div
          ><p class="eyebrow">OPTIONAL GATEWAY KEY</p><h3>后端访问密钥（可选）</h3
          ><p class="hint"
            >仅当公网部署启用了金融 AI 网关二次校验时填写；本机开发通常留空。该值只存当前浏览器。</p
          ></div
        ><div class="gateway-input"
          ><input
            v-model="form.backendAccessKey"
            type="password"
            name="financial-ai-gateway-token"
            autocomplete="new-password"
            data-1p-ignore="true"
            data-lpignore="true"
            data-form-type="other"
            placeholder="与后端金融 AI 访问密钥保持一致"
          /><button class="quiet" @click="saveGateway">保存</button></div
        ></section
      >
      <section class="card health-card"
        ><div class="section-head"
          ><div><p class="eyebrow">DATA PROVIDER HEALTH</p><h3>数据源健康状态</h3></div
          ><button class="quiet" :disabled="loading" @click="refresh">{{
            loading ? '检测中…' : '刷新'
          }}</button></div
        ><div v-if="providers.length" class="health-grid"
          ><article v-for="item in providers" :key="item.key"
            ><b>{{ item.name }}</b
            ><em :class="item.available ? 'ok' : 'bad'">{{ item.status }}</em
            ><small>{{ item.latencyMs ? `${item.latencyMs}ms` : '—' }}</small></article
          ></div
        ><p v-else class="hint">尚未检测。点击“刷新”后检查数据源状态。</p></section
      >
      <footer class="action-bar"
        ><span :class="messageType">{{
          message || (form.mode === 'api' ? deployment.message : '请选择已登录的 CLI')
        }}</span
        ><div
          ><button class="quiet" :disabled="testing" @click="test">{{
            testing ? '测试中…' : '测试连接'
          }}</button
          ><button
            v-if="form.mode === 'api' && deployment.hasApiKey && canManageConnection"
            class="quiet danger-text"
            :disabled="clearing"
            @click="clearApiConnection"
            >{{ clearing ? '清除中…' : '清除本机配置' }}</button
          ><button
            v-if="form.mode !== 'api' || canManageConnection"
            class="primary"
            @click="save"
            >{{ form.mode === 'api' ? '保存到本机' : '保存接入方式' }}</button
          ></div
        ></footer
      >
    </main>
  </PageWrapper>
</template>
<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue';
  import { PageWrapper } from '@/components/Page';
  import { hasPermission } from '@/access/userAccess';
  import { useUserStore } from '@/store/modules/user';
  import {
    clearSavedFinancialAiConnection,
    getFinancialAiCapabilities,
    getSavedFinancialAiConnection,
    loadFinancialAiConnection,
    purgeLegacyBrowserAiSecrets,
    saveFinancialAiConnection,
    saveFinancialAiApiConnection,
    testFinancialAiConnection,
    type AiCapability,
    type FinancialAiDeployment,
    type FinancialAiMode,
  } from '@/api/financialAi';

  const form = reactive(loadFinancialAiConnection());
  const userStore = useUserStore();
  const canManageConnection = computed(() =>
    hasPermission(userStore.getAuthentication?.permissions || [], 'settings.write'),
  );
  const cliOptions = [
    { key: 'claude', name: 'Claude Code', note: 'Anthropic 订阅' },
    { key: 'qwen', name: 'Qwen Code', note: '通义订阅' },
    { key: 'deepseek', name: 'DeepSeek CLI', note: 'DeepSeek / CodeWhale' },
    { key: 'codex', name: 'Codex', note: 'OpenAI / ChatGPT 订阅' },
  ] as const;
  const deployment = ref<FinancialAiDeployment>({
    configured: false,
    hasApiKey: false,
    provider: 'deepseek',
    baseUrl: 'https://api.deepseek.com',
    model: 'deepseek-v4-flash',
    message: '正在读取本机部署状态。',
  });
  const cliStatus = ref<AiCapability[]>([]);
  const providers = ref<AiCapability[]>([]);
  const loading = ref(false);
  const testing = ref(false);
  const clearing = ref(false);
  const message = ref('');
  const messageType = ref('');
  const apiForm = reactive({
    preset: 'deepseek-v4-flash',
    provider: 'deepseek',
    baseUrl: 'https://api.deepseek.com',
    model: 'deepseek-v4-flash',
    apiKey: '',
  });
  const capability = (key: string) => cliStatus.value.find((item) => item.key === key);
  function selectMode(mode: FinancialAiMode) {
    form.mode = mode;
    message.value = '';
  }
  function applyPreset() {
    if (apiForm.preset === 'deepseek-v4-flash')
      Object.assign(apiForm, {
        provider: 'deepseek',
        baseUrl: 'https://api.deepseek.com',
        model: 'deepseek-v4-flash',
      });
  }
  async function save() {
    saveFinancialAiConnection({ ...form });
    if (form.mode === 'subscription') {
      message.value = '订阅接入方式已保存。';
      messageType.value = 'ok';
      return;
    }
    if (!canManageConnection.value) {
      message.value = '当前账号无权修改机器级 AI 配置。';
      messageType.value = 'bad';
      return;
    }
    try {
      deployment.value = await saveFinancialAiApiConnection(apiForm);
      apiForm.apiKey = '';
      message.value = 'API 配置已保存到本机后端。';
      messageType.value = 'ok';
    } catch (reason) {
      message.value = reason instanceof Error ? reason.message : '本机配置保存失败。';
      messageType.value = 'bad';
    }
  }
  function saveGateway() {
    saveFinancialAiConnection({ ...form });
    message.value = form.backendAccessKey
      ? '后端访问密钥已保存到当前浏览器。'
      : '后端访问密钥已清除。';
    messageType.value = 'ok';
  }
  async function test() {
    testing.value = true;
    message.value = '';
    try {
      const result = await testFinancialAiConnection({ ...form });
      message.value = result.message || '连接正常。';
      messageType.value = 'ok';
    } catch (reason) {
      message.value = reason instanceof Error ? reason.message : '连接测试失败。';
      messageType.value = 'bad';
    } finally {
      testing.value = false;
    }
  }
  async function clearApiConnection() {
    if (!canManageConnection.value) return;
    clearing.value = true;
    message.value = '';
    try {
      deployment.value = await clearSavedFinancialAiConnection();
      apiForm.apiKey = '';
      message.value = '本机 API 配置已清除。';
      messageType.value = 'ok';
    } catch (reason) {
      message.value = reason instanceof Error ? reason.message : '本机配置清除失败。';
      messageType.value = 'bad';
    } finally {
      clearing.value = false;
    }
  }
  async function refresh() {
    loading.value = true;
    try {
      const result = await getFinancialAiCapabilities();
      cliStatus.value = result.cli;
      providers.value = result.providers;
      deployment.value = result.deployment;
    } catch {
      message.value = '状态检测暂不可用。';
      messageType.value = 'bad';
    } finally {
      loading.value = false;
    }
  }
  onMounted(async () => {
    void purgeLegacyBrowserAiSecrets();
    const saved = await getSavedFinancialAiConnection();
    deployment.value = saved;
    Object.assign(apiForm, {
      provider: saved.provider,
      baseUrl: saved.baseUrl,
      model: saved.model,
    });
  });
</script>
<style scoped lang="less">
  .page {
    display: grid;
    gap: 14px;
    padding: 12px 4px 28px;
    color: #344054;
  }

  .mode-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .mode-card,
  .card,
  .action-bar {
    border: 1px solid #dbe4ed;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 2px 8px rgb(15 23 42 / 5%);
  }

  .mode-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 24px;
    align-items: center;
    padding: 18px;
    text-align: left;
    gap: 16px;
  }

  .mode-copy {
    display: grid;
    min-width: 0;
    gap: 6px;
  }

  .mode-card.active {
    border-color: #2f6fed;
    box-shadow: 0 0 0 2px rgb(47 111 237 / 10%);
  }

  .mode-card b,
  h2,
  h3 {
    color: #17212f;
  }

  .mode-card small,
  .hint,
  small {
    color: #667085;
    line-height: 1.5;
  }

  .mode-card i {
    justify-self: end;
    color: #2f6fed;
    font-style: normal;
  }

  .card {
    padding: 20px;
  }

  .eyebrow {
    margin: 0 0 4px;
    color: #758196;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  h2,
  h3 {
    margin: 0;
  }

  .hint {
    margin: 10px 0 0;
  }

  .detail-grid,
  .cli-grid,
  .health-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-top: 16px;
  }

  .form-card {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }

  .form-card label {
    display: grid;
    gap: 6px;
    color: #667085;
    font-size: 12px;
    font-weight: 700;
  }

  .gateway-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(360px, 0.7fr);
    align-items: center;
    gap: 20px;
  }

  .gateway-input {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }

  .full {
    grid-column: 1/-1;
  }

  input,
  select {
    width: 100%;
    height: 40px;
    padding: 0 11px;
    border: 1px solid #cfd9e4;
    border-radius: 7px;
    background: #f8fafc;
    color: #17212f;
  }

  .detail-grid div,
  .cli-card,
  .health-grid article {
    display: grid;
    gap: 6px;
    padding: 13px;
    border: 1px solid #dbe4ed;
    border-radius: 8px;
    background: #fbfcfe;
  }

  .cli-card {
    text-align: left;
  }

  .cli-card.selected {
    border-color: #2f6fed;
    background: #f3f7ff;
  }

  .ok {
    color: #087a55;
  }

  .bad {
    color: #b42318;
  }

  .muted {
    color: #8a94a3;
  }

  .section-head,
  .action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .action-bar {
    padding: 12px 16px;
  }

  .quiet,
  .primary {
    padding: 7px 12px;
    border: 1px solid #cfd9e4;
    border-radius: 7px;
    background: #fff;
    color: #344054;
  }

  .danger-text {
    margin-left: 8px;
    color: #b42318;
  }

  .primary {
    margin-left: 8px;
    border-color: #2f6fed;
    background: #2f6fed;
    color: #fff;
  }

  em {
    font-size: 12px;
    font-style: normal;
  }

  @media (max-width: 800px) {
    .mode-grid,
    .detail-grid,
    .cli-grid,
    .health-grid {
      grid-template-columns: 1fr 1fr;
    }

    .gateway-card {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 520px) {
    .mode-grid,
    .detail-grid,
    .cli-grid,
    .health-grid {
      grid-template-columns: 1fr;
    }

    .gateway-input {
      grid-template-columns: 1fr;
    }

    .action-bar {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
