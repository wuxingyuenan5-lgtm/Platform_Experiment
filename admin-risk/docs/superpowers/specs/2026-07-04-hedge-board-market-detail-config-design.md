# 对冲基金看板市场明细改造设计

## 目标

本轮只做对冲基金看板的结构调整与标的清单更新，不做“特殊权限账号可编辑、其他用户只读”的权限化编辑能力。

交付目标：

- 按用户给定清单，重排 `宏观 / 黄金 / 加密 / 美股 / A股` 看板里的市场明细
- 删除宏观看板里两块无效或不需要的组件
- 把 `流动性总图` 提到 `宏观市场明细` 之前
- 为所有市场明细区增加“可添加标的并保存”的能力，但先按本地共享配置实现
- 尽量复用现有 UI 语言，不重写整张对冲基金看板

## 当前生效代码路径

这轮应以当前正在生效的原生对冲基金看板链路为准：

- [src/views/hedgeBoard/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/hedgeBoard/index.vue)
- [src/views/hedgeBoard/nativeData/dashboardClean.ts](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/hedgeBoard/nativeData/dashboardClean.ts)
- [src/views/hedgeBoard/nativeData/marketTerminal.ts](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/hedgeBoard/nativeData/marketTerminal.ts)
- [src/views/hedgeBoard/components/TerminalDetailPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/hedgeBoard/components/TerminalDetailPanel.vue)

结论：

- `dashboardClean.ts` 控制各看板版块顺序与组件编排
- `marketTerminal.ts` 提供市场明细分组、行项目与 TradingView 符号
- `index.vue` 当前仍直接渲染 `TerminalDetailPanel`
- 市场明细存在重复配置痕迹，不能只改一处后就假设全站同步

## 本轮范围

### 1. 宏观看板

- `流动性总图` 移到 `宏观市场明细` 上方
- 删除公式说明条：
  - `DLI = policy liquidity + funding liquidity + credit liquidity + risk liquidity`
- 删除两组旧组件：
  - `通胀主线`
  - `风险资产传导`
- 重做 `宏观市场明细` 分组与排序：
  - 流动性：`NETLIQ`、`M2SL`、`WALCL`、`WDTGAL`、`RRPONTTLD`
  - 利率/汇率：`DXY`、`USDCNH`、`DFF`、`SOFR`、`US2Y`、`US10Y`、`US30Y`、`DFII10`、`T10YIE`、`TLT`、`HYG`、`CN02Y`、`CN10Y`、`CN30Y`
  - 风险偏好：`VIX`、`MOVE`、`DSPX`
  - 经济：`CPIAUCSL`、`PCEPI`、`UNRATE`
- 修正 TradingView 符号：
  - `DXY` -> `INDEX:DXY`
  - `US2Y` -> `PYTH:US02Y`
  - `US10Y` -> `PYTH:US10Y`
  - `US30Y` -> `PYTH:US30Y`
  - `VIX` -> `CAPITALCOM:VIX`

### 2. 黄金看板

- 重做市场明细分组与排序
- 分组：
  - 金属：`XAUUSD`、`AU1!`、`XAGUSD`、`AG1!`、`COPPER`、`PLATINUM`、`PALLADIUM`
  - 矿股：`601899`、`603993`、`000630`
  - 相对比价：`XAU/XAG`、`XAU/COPPER`、`XAU/OIL`、`XAU/SPY`
  - 其他：`BCOM`、`SPGSCI`、`USOIL`、`BRENT`、`XNGUSD`
- 修正 TradingView 符号：
  - `COPPER` -> `VANTAGE:COPPER`
  - `PLATINUM` -> `TVC:PLATINUM`
  - `PALLADIUM` -> `TVC:PALLADIUM`
  - `BCOM` -> `BBG:BCOM`
  - `BRENT` -> `SKILLING:BRENT`
  - `XNGUSD` -> `EIGHTCAP:XNGUSD`

### 3. 加密看板

- 重做市场明细分组与排序
- 分组：
  - 主流币：`BTCUSD`、`IBIT`、`ETHUSD`、`SOLUSD`、`BNBUSD`、`XRPUSD`、`DOGEUSD`、`AAVEUSD`、`UNIUSD`、`CRVUSD`、`HUMAUSD`、`ONDOUSD`、`PLUMEUSD`、`PEPEUSD`、`SUIUSD`
  - 币股：`MSTR`、`CRCL`、`COIN`、`BMNR`、`HOOD`
  - 相对比价：`USDTUSD`、`MSTR/BTC`、`CRCL/BTC`、`COIN/BTC`、`ETH/BTC`、`BTC/XAU`、`BTC/SPY`、`ETH/SOL`
  - 市占率：`BTC.D`、`USDT.D`、`USDC`、`TOTAL`、`TOTAL2`、`TOTAL3`、`OTHERS.D`
- 修正 TradingView 符号：
  - `BTCUSD` -> `COINBASE:BTCUSD`
  - `ETHUSD` -> `COINBASE:ETHUSD`
  - `SOLUSD` -> `COINBASE:SOLUSD`
  - `BNBUSD` -> `COINBASE:BNBUSD`
  - `XRPUSD` -> `COINBASE:XRPUSD`
  - `DOGEUSD` -> `COINBASE:DOGEUSD`
  - `AAVEUSD` -> `COINBASE:AAVEUSD`
  - `UNIUSD` -> `COINBASE:UNIUSD`
  - `CRVUSD` -> `COINBASE:CRVUSD`
  - `HUMAUSD` -> `COINBASE:HUMAUSD`
  - `ONDOUSD` -> `COINBASE:ONDOUSD`
  - `PLUMEUSD` -> `COINBASE:PLUMEUSD`
  - `PEPEUSD` -> `COINBASE:PEPEUSD`
  - `SUIUSD` -> `COINBASE:SUIUSD`
  - `USDTUSD` -> `COINBASE:USDTUSD`
  - `ETH/BTC` -> `COINBASE:ETHUSD/COINBASE:BTCUSD`
  - `ETH/SOL` -> `COINBASE:ETHUSD/COINBASE:SOLUSD`

### 4. 美股看板

- 重做市场明细分组与排序
- 分组：
  - 指数：`SPY`、`NDX`、`DIA`、`IWM`、`MDY`、`MAGS`
  - 板块：`COST`、`JNK`、`MOAT`、`VNQ`、`XLB`、`XLC`、`XLE`、`XLF`、`XLI`、`XLK`、`XLP`、`XLRE`、`XLU`、`XLV`、`XLY`
  - 主题：`SOXX`、`ITA`、`SCHD`、`IBB`、`ARKK`、`BOTZ`、`CLOU`
  - 个股：`AAPL`、`NVDA`、`TSLA`、`AMZN`、`GOOGL`、`META`、`MSFT`、`PFF`、`RSP`、`PLTR`、`SNDK`、`AMD`、`BAC`、`MU`、`TSM`
- 修正 TradingView 符号：
  - `NDX` -> `SPREADEX:NDX`
  - `MAGS` -> `CBOE:MAGS`
  - `BOTZ` -> `NASDAQ:BOTZ`
  - `AAPL` -> `NASDAQ:AAPL`

### 5. A股看板

- 重做市场明细分组与排序
- 分组：
  - 指数：`000001`、`000300`、`000016`、`399673`、`000688`、`000905`、`930050`
  - 板块与主题：`512000`、`512760`、`159755`、`512800`、`159928`、`000932`、`000933`、`000965`、`000994`、`399395`、`399432`、`399808`、`399959`、`399971`、`399975`、`399997`、`931087`
  - 个股：`300750`、`600519`、`688041`、`688981`、`688256`

## 本轮不做

- 不做“特殊权限账号可编辑、其他用户只读”
- 不接真实后端数据库
- 不做多用户协同冲突处理
- 不做实时行情抓取或自动同步行情字段
- 不做整页全量重写

## 推荐实现方案

### 方案核心

把“市场明细配置”从当前硬编码数据里再抽一层，形成单独的共享配置源，然后由 `marketTerminal.ts` 消费这份配置生成各页的 `detailGroups`。

### 原因

- 这次改动集中在“分组 + 排序 + 符号映射”，本质是配置问题，不是页面结构问题
- 后面要做“添加、删减、排序、保存”，如果仍把行项目散落在多个文件里，后续会越改越乱
- 先抽配置层，后续接 `md/json/api` 都有落点

### 建议拆分

- 新增一份市场明细配置文件，例如：
  - `src/views/hedgeBoard/nativeData/marketDetailCatalog.ts`
- 内容包括：
  - 市场维度 `marketId`
  - 分组 `groupLabel`
  - 行项目 `id / name / symbol / tvSymbol`
  - 初始展示顺序
  - 预留扩展字段，例如 `editable`, `source`, `note`

### 页面消费方式

- `marketTerminal.ts`
  - 保留当前页面所需的 `MarketTerminalPageConfig`
  - 但 `detailGroups` 改为从 `marketDetailCatalog.ts` 组装
- `TerminalDetailPanel.vue`
  - 不再自行维护第二套标的映射
  - 只消费统一传入的 `groups`
- `dashboardClean.ts`
  - 只负责版块顺序与宏观页删除/移动组件

## “可添加标的并保存”建议

虽然本轮先不做权限控制，但可以先把保存路径做成本地共享配置友好的结构。

### 这一版建议

- 在市场明细面板增加轻量编辑入口：
  - 添加标的
  - 删除标的
  - 上移/下移排序
- 保存目标先采用一个前端侧静态配置文件对应的序列化结构
- 第一阶段可以先做“页面内编辑 + 导出/回写配置结构”

### 更稳的落地方式

如果希望这一轮就能真保存并在刷新后保留，而不碰权限系统，建议用：

- 一个独立 `md/json` 配置文件作为单一真源
- 前端编辑后写回该文件

这和你之前交易工具页采用 `md` 驱动的思路一致，也最适合你本地先整理内容。

## 实现顺序

1. 清理宏观页结构
2. 抽离统一市场明细配置源
3. 更新五个看板的分组、顺序与 `tvSymbol`
4. 去掉市场明细里的重复旧映射
5. 再补“添加/删减/排序/保存”的交互壳子

## 风险与假设

### 明确假设

- 本轮先不做权限控制，所以编辑入口默认对当前本地环境可见
- 价格、涨跌幅、火花线等展示数据仍允许先沿用静态占位结构
- 重点先保证分组、顺序、符号、组件顺序正确

### 待确认但可以先按常识处理

- 用户原文里 `SOLUSD` 重复了一次，默认去重
- 用户原文里 `SCHD` 重复了一次，默认去重
- 用户原文里 `BTC/SPY` 对应 API 写成了 `XAUUSD/AMEX:SPY`，大概率是笔误
- `XAU/SPY`、`BTC/XAU`、`MSTR/BTC` 这类比价符号是否直接支持，需要按现有 TradingView 组合符号写法或本地比值图方案处理

## 验收标准

- 宏观看板中 `流动性总图` 已位于 `宏观市场明细` 上方
- 宏观公式条已删除
- 宏观两组旧组件已删除
- 五个看板的市场明细分组与排序按清单落地
- 关键 `tvSymbol` 错误项已修正
- 市场明细来源只保留一套主配置，不再到处重复定义
- 为后续“添加/删减/排序/保存”保留清晰扩展位

