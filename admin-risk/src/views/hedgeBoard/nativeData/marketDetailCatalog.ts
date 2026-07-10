export type CatalogMarketId = 'macro' | 'us' | 'aShare' | 'gold' | 'crypto';

export interface CatalogRow {
  id: string;
  name: string;
  symbol: string;
  tvSymbol?: string;
}

export interface CatalogGroup {
  label: string;
  rows: CatalogRow[];
}

export const marketDetailCatalog: Record<CatalogMarketId, CatalogGroup[]> = {
  macro: [
    {
      label: '流动性',
      rows: [
        { id: 'macro-netliq', name: '美元净流动性', symbol: 'NETLIQ', tvSymbol: 'FRED:WALCL-FRED:WDTGAL-FRED:RRPONTTLD' },
        { id: 'macro-m2sl', name: '美国 M2', symbol: 'M2SL', tvSymbol: 'FRED:M2SL' },
        { id: 'macro-walcl', name: '美联储总资产', symbol: 'WALCL', tvSymbol: 'FRED:WALCL' },
        { id: 'macro-wdtgal', name: 'TGA 余额', symbol: 'WDTGAL', tvSymbol: 'FRED:WDTGAL' },
        { id: 'macro-rrp', name: '逆回购余额', symbol: 'RRPONTTLD', tvSymbol: 'FRED:RRPONTTLD' },
      ],
    },
    {
      label: '利率/汇率',
      rows: [
        { id: 'macro-dxy', name: '美元指数', symbol: 'DXY', tvSymbol: 'INDEX:DXY' },
        { id: 'macro-usdcnh', name: '离岸人民币', symbol: 'USDCNH', tvSymbol: 'FX_IDC:USDCNH' },
        { id: 'macro-dff', name: '联邦基金利率', symbol: 'DFF', tvSymbol: 'FRED:DFF' },
        { id: 'macro-sofr', name: 'SOFR', symbol: 'SOFR', tvSymbol: 'FRED:SOFR' },
        { id: 'macro-us2y', name: '美国 2Y', symbol: 'US2Y', tvSymbol: 'PYTH:US02Y' },
        { id: 'macro-us10y', name: '美国 10Y', symbol: 'US10Y', tvSymbol: 'PYTH:US10Y' },
        { id: 'macro-us30y', name: '美国 30Y', symbol: 'US30Y', tvSymbol: 'PYTH:US30Y' },
        { id: 'macro-dfii10', name: '美国 10Y 实际利率', symbol: 'DFII10', tvSymbol: 'FRED:DFII10' },
        { id: 'macro-t10yie', name: '美国 10Y 通胀预期', symbol: 'T10YIE', tvSymbol: 'FRED:T10YIE' },
        { id: 'macro-tlt', name: '长久期美债 ETF', symbol: 'TLT', tvSymbol: 'NASDAQ:TLT' },
        { id: 'macro-hyg', name: '高收益债 ETF', symbol: 'HYG', tvSymbol: 'AMEX:HYG' },
        { id: 'macro-cn2y', name: '中国 2Y', symbol: 'CN02Y', tvSymbol: 'TVC:CN02Y' },
        { id: 'macro-cn10y', name: '中国 10Y', symbol: 'CN10Y', tvSymbol: 'TVC:CN10Y' },
        { id: 'macro-cn30y', name: '中国 30Y', symbol: 'CN30Y', tvSymbol: 'TVC:CN30Y' },
      ],
    },
    {
      label: '风险偏好',
      rows: [
        { id: 'macro-vix', name: 'VIX 波动率', symbol: 'VIX', tvSymbol: 'CAPITALCOM:VIX' },
        { id: 'macro-move', name: 'MOVE 债券波动率', symbol: 'MOVE', tvSymbol: 'TVC:MOVE' },
        { id: 'macro-dspx', name: '标普分散度', symbol: 'DSPX', tvSymbol: 'INDEX:DSPX' },
      ],
    },
    {
      label: '经济',
      rows: [
        { id: 'macro-cpi', name: '美国 CPI', symbol: 'CPIAUCSL', tvSymbol: 'FRED:CPIAUCSL' },
        { id: 'macro-pce', name: '美国 PCE', symbol: 'PCEPI', tvSymbol: 'FRED:PCEPI' },
        { id: 'macro-unrate', name: '美国失业率', symbol: 'UNRATE', tvSymbol: 'FRED:UNRATE' },
      ],
    },
  ],
  gold: [
    {
      label: '金属',
      rows: [
        { id: 'gold-xauusd', name: '现货黄金', symbol: 'XAUUSD', tvSymbol: 'OANDA:XAUUSD' },
        { id: 'gold-au1', name: '沪金主力', symbol: 'AU1!', tvSymbol: 'SHFE:AU1!' },
        { id: 'gold-xagusd', name: '现货白银', symbol: 'XAGUSD', tvSymbol: 'OANDA:XAGUSD' },
        { id: 'gold-ag1', name: '沪银主力', symbol: 'AG1!', tvSymbol: 'SHFE:AG1!' },
        { id: 'gold-copper', name: '美元铜', symbol: 'COPPER', tvSymbol: 'VANTAGE:COPPER' },
        { id: 'gold-plat', name: '铂金', symbol: 'PLATINUM', tvSymbol: 'TVC:PLATINUM' },
        { id: 'gold-pall', name: '钯金', symbol: 'PALLADIUM', tvSymbol: 'TVC:PALLADIUM' },
      ],
    },
    {
      label: '矿股',
      rows: [
        { id: 'gold-zijin', name: '紫金矿业', symbol: '601899', tvSymbol: 'SSE:601899' },
        { id: 'gold-luoyang', name: '洛阳钼业', symbol: '603993', tvSymbol: 'SSE:603993' },
        { id: 'gold-tongling', name: '铜陵有色', symbol: '000630', tvSymbol: 'SZSE:000630' },
      ],
    },
    {
      label: '相对比价',
      rows: [
        { id: 'gold-ratio-xauxag', name: '金银比', symbol: 'XAU/XAG', tvSymbol: 'OANDA:XAUUSD/OANDA:XAGUSD' },
        { id: 'gold-ratio-xaucopper', name: '金铜比', symbol: 'XAU/COPPER', tvSymbol: 'OANDA:XAUUSD/VANTAGE:COPPER' },
        { id: 'gold-ratio-xauoil', name: '金油比', symbol: 'XAU/OIL', tvSymbol: 'OANDA:XAUUSD/TVC:USOIL' },
        { id: 'gold-ratio-xauspy', name: '金股比', symbol: 'XAU/SPY', tvSymbol: 'OANDA:XAUUSD/AMEX:SPY' },
      ],
    },
    {
      label: '其他',
      rows: [
        { id: 'gold-bcom', name: '彭博商品指数', symbol: 'BCOM', tvSymbol: 'BBG:BCOM' },
        { id: 'gold-spgsci', name: '高盛商品指数', symbol: 'SPGSCI', tvSymbol: 'SP:SPGSCI' },
        { id: 'gold-usoil', name: 'WTI 原油', symbol: 'USOIL', tvSymbol: 'TVC:USOIL' },
        { id: 'gold-brent', name: '布伦特原油', symbol: 'BRENT', tvSymbol: 'SKILLING:BRENT' },
        { id: 'gold-xng', name: '天然气', symbol: 'XNGUSD', tvSymbol: 'EIGHTCAP:XNGUSD' },
      ],
    },
  ],
  crypto: [
    {
      label: '主流币',
      rows: [
        { id: 'crypto-btcusd', name: '比特币', symbol: 'BTCUSD', tvSymbol: 'COINBASE:BTCUSD' },
        { id: 'crypto-ibit', name: 'IBIT', symbol: 'IBIT', tvSymbol: 'NASDAQ:IBIT' },
        { id: 'crypto-ethusd', name: '以太坊', symbol: 'ETHUSD', tvSymbol: 'COINBASE:ETHUSD' },
        { id: 'crypto-solusd', name: 'Solana', symbol: 'SOLUSD', tvSymbol: 'COINBASE:SOLUSD' },
        { id: 'crypto-bnbusd', name: 'BNB', symbol: 'BNBUSD', tvSymbol: 'COINBASE:BNBUSD' },
        { id: 'crypto-xrpusd', name: 'XRP', symbol: 'XRPUSD', tvSymbol: 'COINBASE:XRPUSD' },
        { id: 'crypto-dogeusd', name: '狗狗币', symbol: 'DOGEUSD', tvSymbol: 'COINBASE:DOGEUSD' },
        { id: 'crypto-aaveusd', name: 'AAVE', symbol: 'AAVEUSD', tvSymbol: 'COINBASE:AAVEUSD' },
        { id: 'crypto-uniusd', name: 'UNI', symbol: 'UNIUSD', tvSymbol: 'COINBASE:UNIUSD' },
        { id: 'crypto-crvusd', name: 'CRV', symbol: 'CRVUSD', tvSymbol: 'COINBASE:CRVUSD' },
        { id: 'crypto-humausd', name: 'HUMA', symbol: 'HUMAUSD', tvSymbol: 'COINBASE:HUMAUSD' },
        { id: 'crypto-ondousd', name: 'ONDO', symbol: 'ONDOUSD', tvSymbol: 'COINBASE:ONDOUSD' },
        { id: 'crypto-plumeusd', name: 'PLUME', symbol: 'PLUMEUSD', tvSymbol: 'COINBASE:PLUMEUSD' },
        { id: 'crypto-pepeusd', name: 'PEPE', symbol: 'PEPEUSD', tvSymbol: 'COINBASE:PEPEUSD' },
        { id: 'crypto-suiusd', name: 'SUI', symbol: 'SUIUSD', tvSymbol: 'COINBASE:SUIUSD' },
      ],
    },
    {
      label: '币股',
      rows: [
        { id: 'crypto-mstr', name: 'MicroStrategy', symbol: 'MSTR', tvSymbol: 'NASDAQ:MSTR' },
        { id: 'crypto-crcl', name: 'Circle', symbol: 'CRCL', tvSymbol: 'NYSE:CRCL' },
        { id: 'crypto-coin', name: 'Coinbase', symbol: 'COIN', tvSymbol: 'NASDAQ:COIN' },
        { id: 'crypto-bmnr', name: 'BMNR', symbol: 'BMNR', tvSymbol: 'NASDAQ:BMNR' },
        { id: 'crypto-hood', name: 'Robinhood', symbol: 'HOOD', tvSymbol: 'NASDAQ:HOOD' },
      ],
    },
    {
      label: '相对比价',
      rows: [
        { id: 'crypto-usdtusd', name: 'USDT/USD', symbol: 'USDTUSD', tvSymbol: 'COINBASE:USDTUSD' },
        { id: 'crypto-ratio-mstrbtc', name: 'MSTR / BTC', symbol: 'MSTR/BTC', tvSymbol: 'NASDAQ:MSTR/COINBASE:BTCUSD' },
        { id: 'crypto-ratio-crclbtc', name: 'CRCL / BTC', symbol: 'CRCL/BTC', tvSymbol: 'NYSE:CRCL/COINBASE:BTCUSD' },
        { id: 'crypto-ratio-coinbtc', name: 'COIN / BTC', symbol: 'COIN/BTC', tvSymbol: 'NASDAQ:COIN/COINBASE:BTCUSD' },
        { id: 'crypto-ratio-ethbtc', name: 'ETH / BTC', symbol: 'ETH/BTC', tvSymbol: 'COINBASE:ETHUSD/COINBASE:BTCUSD' },
        { id: 'crypto-ratio-btcxau', name: 'BTC / XAU', symbol: 'BTC/XAU', tvSymbol: 'COINBASE:BTCUSD/OANDA:XAUUSD' },
        { id: 'crypto-ratio-btcspy', name: 'BTC / SPY', symbol: 'BTC/SPY', tvSymbol: 'COINBASE:BTCUSD/AMEX:SPY' },
        { id: 'crypto-ratio-ethsol', name: 'ETH / SOL', symbol: 'ETH/SOL', tvSymbol: 'COINBASE:ETHUSD/COINBASE:SOLUSD' },
      ],
    },
    {
      label: '市占率',
      rows: [
        { id: 'crypto-btcd', name: 'BTC 市占率', symbol: 'BTC.D', tvSymbol: 'CRYPTOCAP:BTC.D' },
        { id: 'crypto-usdtd', name: 'USDT 市占率', symbol: 'USDT.D', tvSymbol: 'CRYPTOCAP:USDT.D' },
        { id: 'crypto-usdc', name: 'USDC', symbol: 'USDC', tvSymbol: 'CRYPTOCAP:USDC' },
        { id: 'crypto-total', name: '总市值', symbol: 'TOTAL', tvSymbol: 'CRYPTOCAP:TOTAL' },
        { id: 'crypto-total2', name: '除 BTC 市值', symbol: 'TOTAL2', tvSymbol: 'CRYPTOCAP:TOTAL2' },
        { id: 'crypto-total3', name: '除 BTC/ETH 市值', symbol: 'TOTAL3', tvSymbol: 'CRYPTOCAP:TOTAL3' },
        { id: 'crypto-othersd', name: 'Others 市占率', symbol: 'OTHERS.D', tvSymbol: 'CRYPTOCAP:OTHERS.D' },
      ],
    },
  ],
  us: [
    {
      label: '指数',
      rows: [
        { id: 'us-spy', name: '标普 500', symbol: 'SPY', tvSymbol: 'AMEX:SPY' },
        { id: 'us-ndx', name: '纳指 100', symbol: 'NDX', tvSymbol: 'SPREADEX:NDX' },
        { id: 'us-dia', name: '道指 ETF', symbol: 'DIA', tvSymbol: 'AMEX:DIA' },
        { id: 'us-iwm', name: '罗素 2000', symbol: 'IWM', tvSymbol: 'AMEX:IWM' },
        { id: 'us-mdy', name: '中盘股', symbol: 'MDY', tvSymbol: 'AMEX:MDY' },
        { id: 'us-mags', name: '七巨头 ETF', symbol: 'MAGS', tvSymbol: 'CBOE:MAGS' },
      ],
    },
    {
      label: '板块',
      rows: [
        { id: 'us-cost', name: 'Costco', symbol: 'COST', tvSymbol: 'NASDAQ:COST' },
        { id: 'us-jnk', name: '高收益债 ETF', symbol: 'JNK', tvSymbol: 'NASDAQ:JNK' },
        { id: 'us-moat', name: '护城河 ETF', symbol: 'MOAT', tvSymbol: 'BATS:MOAT' },
        { id: 'us-vnq', name: 'REITs ETF', symbol: 'VNQ', tvSymbol: 'AMEX:VNQ' },
        { id: 'us-xlb', name: '材料', symbol: 'XLB', tvSymbol: 'AMEX:XLB' },
        { id: 'us-xlc', name: '通信服务', symbol: 'XLC', tvSymbol: 'AMEX:XLC' },
        { id: 'us-xle', name: '能源', symbol: 'XLE', tvSymbol: 'AMEX:XLE' },
        { id: 'us-xlf', name: '金融', symbol: 'XLF', tvSymbol: 'AMEX:XLF' },
        { id: 'us-xli', name: '工业', symbol: 'XLI', tvSymbol: 'AMEX:XLI' },
        { id: 'us-xlk', name: '科技', symbol: 'XLK', tvSymbol: 'AMEX:XLK' },
        { id: 'us-xlp', name: '必需消费', symbol: 'XLP', tvSymbol: 'AMEX:XLP' },
        { id: 'us-xlre', name: '房地产', symbol: 'XLRE', tvSymbol: 'AMEX:XLRE' },
        { id: 'us-xlu', name: '公用事业', symbol: 'XLU', tvSymbol: 'AMEX:XLU' },
        { id: 'us-xlv', name: '医疗', symbol: 'XLV', tvSymbol: 'AMEX:XLV' },
        { id: 'us-xly', name: '可选消费', symbol: 'XLY', tvSymbol: 'AMEX:XLY' },
      ],
    },
    {
      label: '主题',
      rows: [
        { id: 'us-soxx', name: '半导体 ETF', symbol: 'SOXX', tvSymbol: 'NASDAQ:SOXX' },
        { id: 'us-ita', name: '军工 ETF', symbol: 'ITA', tvSymbol: 'AMEX:ITA' },
        { id: 'us-schd', name: '高股息 ETF', symbol: 'SCHD', tvSymbol: 'AMEX:SCHD' },
        { id: 'us-ibb', name: '生物科技 ETF', symbol: 'IBB', tvSymbol: 'NASDAQ:IBB' },
        { id: 'us-arkk', name: 'ARK 创新', symbol: 'ARKK', tvSymbol: 'AMEX:ARKK' },
        { id: 'us-botz', name: '机器人 ETF', symbol: 'BOTZ', tvSymbol: 'NASDAQ:BOTZ' },
        { id: 'us-clou', name: '云计算 ETF', symbol: 'CLOU', tvSymbol: 'NASDAQ:CLOU' },
      ],
    },
    {
      label: '个股',
      rows: [
        { id: 'us-aapl', name: '苹果', symbol: 'AAPL', tvSymbol: 'NASDAQ:AAPL' },
        { id: 'us-nvda', name: '英伟达', symbol: 'NVDA', tvSymbol: 'NASDAQ:NVDA' },
        { id: 'us-tsla', name: '特斯拉', symbol: 'TSLA', tvSymbol: 'NASDAQ:TSLA' },
        { id: 'us-amzn', name: '亚马逊', symbol: 'AMZN', tvSymbol: 'NASDAQ:AMZN' },
        { id: 'us-googl', name: '谷歌', symbol: 'GOOGL', tvSymbol: 'NASDAQ:GOOGL' },
        { id: 'us-meta', name: 'Meta', symbol: 'META', tvSymbol: 'NASDAQ:META' },
        { id: 'us-msft', name: '微软', symbol: 'MSFT', tvSymbol: 'NASDAQ:MSFT' },
        { id: 'us-pltr', name: 'Palantir', symbol: 'PLTR', tvSymbol: 'NASDAQ:PLTR' },
        { id: 'us-sndk', name: 'Sandisk', symbol: 'SNDK', tvSymbol: 'NASDAQ:SNDK' },
        { id: 'us-amd', name: 'AMD', symbol: 'AMD', tvSymbol: 'NASDAQ:AMD' },
        { id: 'us-bac', name: '美国银行', symbol: 'BAC', tvSymbol: 'NYSE:BAC' },
        { id: 'us-mu', name: '美光', symbol: 'MU', tvSymbol: 'NASDAQ:MU' },
        { id: 'us-tsm', name: '台积电', symbol: 'TSM', tvSymbol: 'NYSE:TSM' },
      ],
    },
  ],
  aShare: [
    {
      label: '指数',
      rows: [
        { id: 'ashare-000001', name: '上证指数', symbol: '000001', tvSymbol: 'SSE:000001' },
        { id: 'ashare-000300', name: '沪深 300', symbol: '000300', tvSymbol: 'SSE:000300' },
        { id: 'ashare-000016', name: '上证 50', symbol: '000016', tvSymbol: 'SSE:000016' },
        { id: 'ashare-399673', name: '创业板 50', symbol: '399673', tvSymbol: 'SZSE:399673' },
        { id: 'ashare-000688', name: '科创 50', symbol: '000688', tvSymbol: 'SSE:000688' },
        { id: 'ashare-000905', name: '中证 500', symbol: '000905', tvSymbol: 'SSE:000905' },
        { id: 'ashare-930050', name: '中证 A50', symbol: '930050', tvSymbol: 'CSI:930050' },
      ],
    },
    {
      label: '板块与主题',
      rows: [
        { id: 'ashare-512000', name: '券商 ETF', symbol: '512000', tvSymbol: 'SSE:512000' },
        { id: 'ashare-512760', name: '芯片 ETF', symbol: '512760', tvSymbol: 'SSE:512760' },
        { id: 'ashare-159755', name: '电新 ETF', symbol: '159755', tvSymbol: 'SZSE:159755' },
        { id: 'ashare-512800', name: '银行 ETF', symbol: '512800', tvSymbol: 'SSE:512800' },
        { id: 'ashare-159928', name: '消费 ETF', symbol: '159928', tvSymbol: 'SZSE:159928' },
        { id: 'ashare-000932', name: '中证消费', symbol: '000932', tvSymbol: 'CSI:000932' },
        { id: 'ashare-000933', name: '中证医药', symbol: '000933', tvSymbol: 'CSI:000933' },
        { id: 'ashare-000965', name: '中证能源', symbol: '000965', tvSymbol: 'CSI:000965' },
        { id: 'ashare-000994', name: '中证信息', symbol: '000994', tvSymbol: 'CSI:000994' },
        { id: 'ashare-399395', name: '国证有色', symbol: '399395', tvSymbol: 'SZSE:399395' },
        { id: 'ashare-399432', name: '国证汽车', symbol: '399432', tvSymbol: 'SZSE:399432' },
        { id: 'ashare-399808', name: '中证新能源', symbol: '399808', tvSymbol: 'SZSE:399808' },
        { id: 'ashare-399959', name: '央企红利', symbol: '399959', tvSymbol: 'SZSE:399959' },
        { id: 'ashare-399971', name: '中证传媒', symbol: '399971', tvSymbol: 'SZSE:399971' },
        { id: 'ashare-399975', name: '证券公司', symbol: '399975', tvSymbol: 'SZSE:399975' },
        { id: 'ashare-399997', name: '中证白酒', symbol: '399997', tvSymbol: 'SZSE:399997' },
        { id: 'ashare-931087', name: '中证机器人', symbol: '931087', tvSymbol: 'CSI:931087' },
      ],
    },
    {
      label: '个股',
      rows: [
        { id: 'ashare-300750', name: '宁德时代', symbol: '300750', tvSymbol: 'SZSE:300750' },
        { id: 'ashare-600519', name: '贵州茅台', symbol: '600519', tvSymbol: 'SSE:600519' },
        { id: 'ashare-688041', name: '海光信息', symbol: '688041', tvSymbol: 'SSE:688041' },
        { id: 'ashare-688981', name: '中芯国际', symbol: '688981', tvSymbol: 'SSE:688981' },
        { id: 'ashare-688256', name: '寒武纪', symbol: '688256', tvSymbol: 'SSE:688256' },
      ],
    },
  ],
};
