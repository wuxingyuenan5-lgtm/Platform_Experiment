# 对冲基金看板新增“交易工具”子页设计

## 目标

在 `对冲基金看板` 下新增一个独立子页 `交易工具`，当前只交付 `加密工具` 内容。页面需要延续现有平台在 `hedgeBoard` 模块中的浅色研究面板风格，但代码结构必须独立、可迁移，便于后续单独交给程序员并入部署环境。

## 本轮范围

- 新增 `交易工具` 子路由与菜单入口
- 新增独立页面容器，不把新逻辑堆进现有超大 `hedgeBoard/index.vue`
- 只展示 `加密工具`
- 将 `加密工具` 按四组展示：
  - `研报类`
  - `交易类`
  - `基本面类`
  - `媒体类`
- 每个工具可点击并跳转到对应外部网站
- 对文档中一个条目包含多个链接的情况，拆成多个独立工具项

## 明确不做

- 本轮不填充 `宏观工具 / 股市工具 / 金属工具`
- 本轮不做登录态收藏、标签筛选、搜索、排序、埋点
- 本轮不接入后端接口，工具清单先使用前端本地静态数据
- 本轮不改造现有 `宏观 / 商品 / 加密 / 美股 / A股 / 全球` 页面内部逻辑

## 路由与入口

### 路由设计

在 `hedge-board` 下新增子路由：

- `/hedge-board/trading-tools`

该路由指向新的独立页面文件，而不是继续复用 `src/views/hedgeBoard/index.vue`。

### 导航表现

`交易工具` 需要出现在对冲基金看板体系里，成为并列入口。视觉上保持和当前 `hedgeBoard` 顶部导航一致的语义，但实现上不与旧页面的巨型单文件强耦合。

## 页面结构

页面采用目录式工具库，而不是终端式行情面板。

### 顶部区域

- 页面标题：`对冲基金看板 / 交易工具`
- 简短说明：说明这是研究与交易执行前的外部工具入口页
- 保留与现有平台一致的浅色卡片、细边框、圆角和低饱和蓝灰色文本体系

### 主体区域

主体仅包含一个 `加密工具` 模块。

模块内部按组展示：

1. `研报类`
2. `交易类`
3. `基本面类`
4. `媒体类`

每组包含：

- 分组标题
- 分组说明文案
- 工具卡片网格

### 工具卡片

每个工具卡片包含：

- 工具名称
- 简短说明或标签
- 域名信息
- 外链跳转提示

交互规则：

- 点击整个卡片新开标签页访问外部网站
- 使用安全外链属性
- 鼠标悬停时给出轻微抬升和边框强调

## 数据组织

工具数据从页面组件中拆出，单独放在独立数据文件中，避免后续迁移时还要从页面模板里反向提取内容。

建议数据结构：

- 一级：页面模块
- 二级：工具分组
- 三级：工具项数组

每个工具项至少包含：

- `id`
- `name`
- `url`
- `description`
- `domain`
- `tags`

对于文档中多链接条目，拆为多个 `tool item`，各自拥有独立 `id` 和 `url`。

## 组件拆分

为了后续单独移交，页面按“壳、数据、展示”拆开。

### 新建文件

- `src/views/hedgeBoard/tradingTools/index.vue`
  - 交易工具页入口
  - 负责页面标题、说明、模块组合
- `src/views/hedgeBoard/tradingTools/data/cryptoTools.ts`
  - 存放加密工具分组和链接数据
- `src/views/hedgeBoard/tradingTools/components/ToolGroupSection.vue`
  - 单个分组组件
- `src/views/hedgeBoard/tradingTools/components/ToolLinkCard.vue`
  - 单个工具卡片组件

### 设计原则

- 页面入口文件只负责组装，不承载大批量静态数据
- 卡片组件尽量无业务耦合，未来可复用到宏观/股市/金属工具
- 分组组件只处理布局和展示，不嵌入硬编码工具内容

## 视觉约束

视觉不追求新风格，而是对齐当前平台：

- 延续 `hedgeBoard` 的浅色研究面板体系
- 保留蓝灰色文本、轻阴影、细描边
- 网格卡片的密度要适合研究工具目录，而不是营销首页
- 移动端下降为单列或双列，避免卡片挤压

## 文档内容映射

`加密工具` 按以下逻辑落库：

### 研报类

- Glassnode newsletter
- Glassnode market pulse
- Galaxy research
- Coinbase institutional research
- a16z crypto
- VanEck digital assets
- River research
- Grayscale research
- Binance research
- ARK articles
- Bitwise market insights
- Messari / Delphi 链接
- Hayes research
- CoinShares insights
- Unbias analysts
- 贝格先生链上分析

### 交易类

- Coinglass TV
- Coinglass open interest
- Coinglass CME CFTC
- Coinglass long short ratio
- Hyperliquid wallet distribution
- Coinglass liquidation heat map
- Checkonchain term structure
- Greeks.live options lab
- Deribit options metrics
- Coinglass fear and greed
- Coinglass margin fee
- Coinglass funding rate
- CryptoQuant summary
- Checkonchain charts home
- Glassnode studio active addresses
- Coinglass derivative index
- Coinbase premium index
- ETF premium
- Coinglass heatmap
- SoSoValue crypto index
- CryptoBubbles
- CoinMarketCap
- Halving performance

### 基本面类

- Bitcoin Laws
- SoSoValue BTC/ETH ETF
- Coinglass Bitcoin Treasuries
- SoSoValue Bitcoin Treasuries
- BitcoinTreasuries.net
- Strategic ETH Reserve
- Bitcoin government treasuries

### 媒体类

- Foresight News
- 金色财经
- SoSoValue research
- 深潮 TechFlow
- PANews
- The Block
- BlockBeats

## 实现边界

本轮实现应尽量只改动以下区域：

- `src/router/routes/modules/hedge.ts`
- 新增 `src/views/hedgeBoard/tradingTools/` 目录

如需让 `hedgeBoard` 主导航出现 `交易工具`，应优先采用最小修改方式，而不是重写现有 `hedgeBoard/index.vue` 的研究逻辑。

## 测试与验证

最少验证项：

- 路由可进入 `交易工具` 页面
- 四个分组正常渲染
- 每张卡片可点击并新开外链
- 桌面端与窄屏布局不破
- 代码结构中，页面、数据、卡片组件可独立拷走

## 交付标准

完成后应达到以下状态：

- 用户在本地平台可直接访问 `交易工具`
- 页面 UI 与现有平台语言一致
- 加密工具列表已按组整理完成
- 数据和组件拆分清晰，适合后续单独交付程序员并入线上项目
