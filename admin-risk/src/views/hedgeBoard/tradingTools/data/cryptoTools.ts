export interface TradingToolLink {
  id: string;
  name: string;
  url: string;
  description: string;
  domain: string;
  tags: string[];
}

export interface TradingToolGroup {
  id: string;
  title: string;
  description: string;
  tools: TradingToolLink[];
}

function createTool(
  id: string,
  name: string,
  url: string,
  domain: string,
  groupTitle: string,
): TradingToolLink {
  return {
    id,
    name,
    url,
    description: `来源: ${groupTitle}`,
    domain,
    tags: ['加密', groupTitle],
  };
}

const researchTools: TradingToolLink[] = [
  createTool('glassnode-newsletter', 'Glassnode 每周简报', 'https://insights.glassnode.com/tag/newsletter/', 'insights.glassnode.com', '研报类'),
  createTool('glassnode-market-pulse', 'Glassnode 市场脉搏', 'https://research.glassnode.com/tag/market-pulse/', 'research.glassnode.com', '研报类'),
  createTool('galaxy-research', 'Galaxy 研究', 'https://www.galaxy.com/insights/research', 'www.galaxy.com', '研报类'),
  createTool('coinbase-institutional-research', 'Coinbase 机构研究', 'https://www.coinbase.com/zh-cn/institutional/research-insights/research', 'www.coinbase.com', '研报类'),
  createTool('a16z-crypto', 'a16z 加密研究', 'https://a16zcrypto.substack.com/', 'a16zcrypto.substack.com', '研报类'),
  createTool('vaneck-digital-assets', 'VanEck 数字资产', 'https://www.vaneck.com/us/en/insights/digital-assets/?p=1', 'www.vaneck.com', '研报类'),
  createTool('river-research', 'River 比特币研究', 'https://river.com/research', 'river.com', '研报类'),
  createTool('grayscale-research', 'Grayscale 研究', 'https://research.grayscale.com/', 'research.grayscale.com', '研报类'),
  createTool('binance-research', '币安研究院', 'https://www.binance.com/zh-CN/research', 'www.binance.com', '研报类'),
  createTool('ark-articles', 'ARK 研究文章', 'https://www.ark-invest.com/articles', 'www.ark-invest.com', '研报类'),
  createTool('bitwise-market-insights', 'Bitwise 市场洞察', 'https://bitwiseinvestments.com/crypto-market-insights', 'bitwiseinvestments.com', '研报类'),
  createTool('bitwise-weekly-memo', 'Bitwise 每周分析', 'https://experts.bitwiseinvestments.com/cio-memos', 'experts.bitwiseinvestments.com', '研报类'),
  createTool('messari-delphi-report', 'Messari / Delphi 前瞻报告', 'https://members.delphidigital.io/reports/the-year-ahead-for-markets-2026#concluding-thoughts-949c', 'members.delphidigital.io', '研报类'),
  createTool('arthur-hayes-research', 'Arthur Hayes 研究', 'https://cryptohayes.substack.com/', 'cryptohayes.substack.com', '研报类'),
  createTool('coinshares-insights', 'CoinShares 洞察', 'https://coinshares.com/corp/insights/', 'coinshares.com', '研报类'),
  createTool('unbias-analysts', 'Unbias 分析师聚合', 'https://unbias.fyi/analysts?source=all', 'unbias.fyi', '研报类'),
  createTool('market-beggar', 'Market Beggar', 'https://x.com/market_beggar', 'x.com', '研报类'),
  createTool('supersaiyan-weekly', 'BTC 每周深度分析报告 ( + 美股） | 08 03 2026', 'https://supersaiyan1957.substack.com/', 'supersaiyan1957.substack.com', '研报类'),
];

const tradingTools: TradingToolLink[] = [
  createTool('btc-macromicro-driver', '比特币BTC驱动三大因素：流动性＆实际利率＆PE', 'https://www.macromicro.me/collections/22514/bi-te-bi_418919/111972/bi-te-bi-BTC-qu-dong-san-da-yin-su-liu-dong-xing-shi-ji-li-lyu-GDP', 'www.macromicro.me', '交易类'),
  createTool('bitcoin-halving-performance', '减半后表现', 'https://www.coinglass.com/pro/i/bitcoin-price-performance-since-halving', 'www.coinglass.com', '交易类'),
  createTool('coinglass-tv', 'Coinglass 资费+持仓量', 'https://www.coinglass.com/tv/zh/Binance_BTCUSDT', 'www.coinglass.com', '交易类'),
  createTool('liquidation-heatmap', '爆仓热力图', 'https://www.coinglass.com/zh/pro/futures/LiquidationHeatMap', 'www.coinglass.com', '交易类'),
  createTool('btc-term-structure', 'BTC 期限结构', 'https://charts.checkonchain.com/btconchain/derivatives/derivatives_termstructure_0/derivatives_termstructure_0_light.html', 'charts.checkonchain.com', '交易类'),
  createTool('greeks-btc-lab', 'Greeks.live BTC 数据实验室', 'https://www.greeks.live/deribit/tools/datalab/BTC', 'www.greeks.live', '交易类'),
  createTool('deribit-options-metrics', 'Deribit 期权指标', 'https://www.deribit.com/statistics/BTC/metrics/options', 'www.deribit.com', '交易类'),
  createTool('crypto-derivatives-index', '加密衍生品指数', 'https://www.coinglass.com/zh/pro/i/CGDI', 'www.coinglass.com', '交易类'),
  createTool('coinbase-premium-index', 'Coinbase 溢价指数', 'https://www.coinglass.com/pro/i/coinbase-bitcoin-premium-index', 'www.coinglass.com', '交易类'),
  createTool('etf-premium', 'ETF 溢折价', 'https://www.coinglass.com/pro/etf/Premium', 'www.coinglass.com', '交易类'),
  createTool('open-interest', '未平仓合约', 'https://www.coinglass.com/zh/pro/futures/OpenInterest', 'www.coinglass.com', '交易类'),
  createTool('fear-greed-index', '恐慌与贪婪指数', 'https://www.coinglass.com/zh/pro/i/FearGreedIndex', 'www.coinglass.com', '交易类'),
  createTool('margin-fee-chart', '杠杆借贷成本', 'https://www.coinglass.com/zh/pro/i/MarginFeeChart', 'www.coinglass.com', '交易类'),
  createTool('funding-rate', '资金费率', 'https://www.coinglass.com/FundingRate', 'www.coinglass.com', '交易类'),
  createTool('checkonchain-home', 'Checkonchain 图表库', 'https://charts.checkonchain.com/', 'charts.checkonchain.com', '交易类'),
  createTool('glassnode-active-addresses', 'Glassnode 活跃地址', 'https://studio.glassnode.com/charts/addresses.ActiveCount?a=BTC', 'studio.glassnode.com', '交易类'),
  createTool('crypto-heatmap', '加密热力图', 'https://www.coinglass.com/zh/pro/heatmap/price-change', 'www.coinglass.com', '交易类'),
  createTool('crypto-sector-index', '加密各板块指数', 'https://sosovalue.com/zh/assets/cryptoindex/verified-index', 'sosovalue.com', '交易类'),
  createTool('cryptobubbles', 'CryptoBubbles 泡泡图', 'https://cryptobubbles.net/', 'cryptobubbles.net', '交易类'),
  createTool('coinmarketcap-overview', 'CoinMarketCap 市值总览', 'https://coinmarketcap.com/', 'coinmarketcap.com', '交易类'),
  createTool('cme-cftc-positioning', 'CME / CFTC 持仓', 'https://www.coinglass.com/pro/cme/cftc', 'www.coinglass.com', '交易类'),
  createTool('long-short-ratio', '多空比', 'https://www.coinglass.com/LongShortRatio', 'www.coinglass.com', '交易类'),
  createTool('hyperliquid-wallet-positioning', 'Hyperliquid 钱包多空分布', 'https://www.coinglass.com/hl', 'www.coinglass.com', '交易类'),
  createTool('bgeometrics-whales', '大小鲸鱼购买情况以及其他链上指标', 'https://charts.bgeometrics.com/bitcoin_distribution_coins_tables.html', 'charts.bgeometrics.com', '交易类'),
  createTool('cryptoquant-summary', '加密各类链上数据 | CryptoQuant', 'https://cryptoquant.com/asset/btc/summary', 'cryptoquant.com', '交易类'),
  createTool('tokenomist', '代币解锁 | 追踪最新数据并完成解锁计划', 'https://tokenomist.ai/', 'tokenomist.ai', '交易类'),
  createTool('arkham', '链上 | Arkham', 'https://intel.arkm.com/', 'intel.arkm.com', '交易类'),
  createTool('oklink', '区块链浏览器查询 | 欧科云链 OKLink', 'https://www.oklink.com/zh-hans', 'www.oklink.com', '交易类'),
  createTool('hyperliquid-stats', 'Hyperliquid 统计数据', 'https://stats.hyperliquid.xyz/', 'stats.hyperliquid.xyz', '交易类'),
  createTool('checkonchain-btc-analysis', '比特币链上分析与图表 - _checkonchain | BTC 指标、指数与市场数据', 'https://charts.checkonchain.com/', 'charts.checkonchain.com', '交易类'),
];

const fundamentalTools: TradingToolLink[] = [
  createTool('benjamin-cowen', 'Benjamin Cowen | Macroeconomic Analyst & Data Scientist', 'https://www.benjamincowen.com/#services', 'www.benjamincowen.com', '基本面类'),
  createTool('bitcoin-laws', 'Bitcoin Laws 政策追踪', 'https://bitcoinlaws.io/', 'bitcoinlaws.io', '基本面类'),
  createTool('sosovalue-btc-eth-etf', 'SoSoValue BTC / ETH ETF', 'https://sosovalue.com/zh/assets/etf/us-btc-spot', 'sosovalue.com', '基本面类'),
  createTool('sosovalue-bitcoin-treasuries', 'SoSoValue 比特币储备', 'https://sosovalue.com/zh/assets/bitcoin-treasuries', 'sosovalue.com', '基本面类'),
  createTool('coinglass-bitcoin-treasuries', 'Coinglass 比特币储备总量', 'https://www.coinglass.com/BitcoinTreasuries', 'www.coinglass.com', '基本面类'),
  createTool('bitcoin-treasuries-detail', 'BTC分布明细', 'https://bitcointreasuries.net/', 'bitcointreasuries.net', '基本面类'),
  createTool('strategic-eth-reserve', '战略 ETH 储备', 'https://www.strategicethreserve.xyz/', 'www.strategicethreserve.xyz', '基本面类'),
  createTool('government-bitcoin-treasuries', '政府比特币储备', 'https://www.coinglass.com/zh/pro/i/bitcoin-government-treasuries', 'www.coinglass.com', '基本面类'),
  createTool('saylortracker', '微策略购买记录', 'https://saylortracker.com/', 'saylortracker.com', '基本面类'),
  createTool('strc-live', 'STRC', 'https://strc.live/ticker/strc', 'strc.live', '基本面类'),
  createTool('rwa-xyz', 'RWA.xyz | 区块链现实世界资产分析---RWA.xyz |代币化现实世界资产分析', 'https://app.rwa.xyz/', 'app.rwa.xyz', '基本面类'),
  createTool('intothecryptoverse-dashboard', '仪表板 | ITC', 'https://app.intothecryptoverse.com/dashboard', 'app.intothecryptoverse.com', '基本面类'),
  createTool('hypurrscan', 'HypurrScan | Hyperliquid Explorer', 'https://hypurrscan.io/address/0x5078C2fBeA2b2aD61bc840Bc023E35Fce56BeDb6?s=09', 'hypurrscan.io', '基本面类'),
  createTool('xxi-money', '21资本官网', 'https://xxi.money/', 'xxi.money', '基本面类'),
  createTool('ibit-official', 'IBIT官网', 'https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf#/', 'www.ishares.com', '基本面类'),
];

const mediaTools: TradingToolLink[] = [
  createTool('foresight-news', 'Foresight News', 'https://foresightnews.pro/', 'foresightnews.pro', '媒体类'),
  createTool('jinse', '金色财经', 'https://www.jinse2.com/', 'www.jinse2.com', '媒体类'),
  createTool('sosovalue-research', 'SoSoValue 研究', 'https://sosovalue.com/zh/research', 'sosovalue.com', '媒体类'),
  createTool('techflow', 'TechFlow', 'https://www.techflowpost.com/', 'www.techflowpost.com', '媒体类'),
  createTool('panews', 'PANews', 'https://www.panewslab.com/zh-hant', 'www.panewslab.com', '媒体类'),
  createTool('the-block', 'The Block', 'https://www.theblock.co/', 'www.theblock.co', '媒体类'),
  createTool('blockbeats', 'BlockBeats', 'https://www.theblockbeats.info/', 'www.theblockbeats.info', '媒体类'),
];

const utilityTools: TradingToolLink[] = [
  createTool('barker', 'Barker - Find the Best Stablecoin Yields', 'https://app.barker.money/campaigns', 'app.barker.money', '理财与其他'),
  createTool('rootdata', 'Web3 热门项目排名', 'https://www.rootdata.com/zh', 'www.rootdata.com', '理财与其他'),
  createTool('ethena', 'Ethena信息', 'https://app.ethena.fi/dashboards/positions', 'app.ethena.fi', '理财与其他'),
  createTool('defillama-ethereum', 'Ethereum - DefiLlama', 'https://defillama.com/chain/Ethereum', 'defillama.com', '理财与其他'),
  createTool('btc-com', 'BTC.com 为全球区块链爱好者提供专业的数据与矿池服务', 'https://btc.com/zh-CN', 'btc.com', '理财与其他'),
  createTool('dexscreener', 'DEX Screener', 'https://dexscreener.com/', 'dexscreener.com', '理财与其他'),
  createTool('pendle', 'Pendle', 'https://app.pendle.finance/trade/markets?utm_source=landing&utm_medium=landing', 'app.pendle.finance', '理财与其他'),
  createTool('miningpoolstats', '挖矿BTC数据', 'https://miningpoolstats.stream/bitcoin', 'miningpoolstats.stream', '理财与其他'),
  createTool('morpho', 'Morpho | The most trusted network for onchain loans', 'https://morpho.org/', 'morpho.org', '理财与其他'),
  createTool('kamino-lend', '贷款 | 卡米诺金融', 'https://app.kamino.finance/earn/lend', 'app.kamino.finance', '理财与其他'),
  createTool('lulo', 'Lulo', 'https://app.lulo.fi/', 'app.lulo.fi', '理财与其他'),
  createTool('uniswap-pools', '在 Uniswap 上探索 Ethereum 的热门资金池', 'https://app.uniswap.org/explore/pools', 'app.uniswap.org', '理财与其他'),
  createTool('spark', 'Spark：利用稳定币赚钱', 'https://app.spark.fi/', 'app.spark.fi', '理财与其他'),
  createTool('onekey-earn', 'OneKey', 'https://1key.so/earn', '1key.so', '理财与其他'),
  createTool('apeoclock', 'defi项目发布日历', 'https://www.apeoclock.com/', 'www.apeoclock.com', '理财与其他'),
  createTool('lido-staking', 'ETH质押', 'https://stake.lido.fi/', 'stake.lido.fi', '理财与其他'),
  createTool('cryptorank-prediction-markets', '一级和预测市场：CryptoRank.io', 'https://cryptorank.io/prediction-markets', 'cryptorank.io', '理财与其他'),
  createTool('bitbo-calendar', '比特币日历', 'https://bitbo.io/calendar/', 'bitbo.io', '理财与其他'),
  createTool('coincarp-events', '加密货币活动日历 | CoinCarp', 'https://www.coincarp.com/events/', 'www.coincarp.com', '理财与其他'),
  createTool('gmgn', '聪明钱追踪--GMGN.AI', 'https://gmgn.ai/?ref=NtZl14CJ&chain=sol', 'gmgn.ai', '理财与其他'),
  createTool('axiom-trade', '聪明钱|discover', 'https://axiom.trade/', 'axiom.trade', '理财与其他'),
  createTool('dune', 'Dune — 由社区提供支持的加密分析。', 'https://dune.com/home', 'dune.com', '理财与其他'),
  createTool('uniscan', 'UniScan', 'https://uniscan.cc/fractal/', 'uniscan.cc', '理财与其他'),
  createTool('mempool-space', 'mempool - Bitcoin Explorer', 'https://mempool.space/zh/', 'mempool.space', '理财与其他'),
  createTool('etherscan-gas-tracker', 'Ethereum Gas Tracker | Etherscan', 'https://etherscan.io/gastracker', 'etherscan.io', '理财与其他'),
  createTool('ultrasound-money', '0 Gwei | $4,481 | ultrasound.money', 'https://ultrasound.money/', 'ultrasound.money', '理财与其他'),
];

export const cryptoToolGroups: TradingToolGroup[] = [
  {
    id: 'research',
    title: '研报类',
    description: '机构研报、主题研究与分析师观察。',
    tools: researchTools,
  },
  {
    id: 'trading',
    title: '交易类',
    description: '链上指标、衍生品、资金费率与交易监控工具。',
    tools: tradingTools,
  },
  {
    id: 'fundamental',
    title: '基本面类',
    description: '政策、ETF、储备、链上分布与核心基本面跟踪。',
    tools: fundamentalTools,
  },
  {
    id: 'media',
    title: '媒体类',
    description: '新闻入口、研究专栏与中文媒体追踪。',
    tools: mediaTools,
  },
  {
    id: 'utility',
    title: '理财与其他',
    description: '理财、DeFi、活动日历与生态辅助工具。',
    tools: utilityTools,
  },
];

export const cryptoToolPageMeta = {
  title: '加密工具',
  eyebrow: '加密工具箱',
  summary: '按你当前 Markdown 清单同步后的加密工具页。',
} as const;
