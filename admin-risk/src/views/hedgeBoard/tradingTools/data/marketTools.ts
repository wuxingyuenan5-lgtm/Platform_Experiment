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

export interface TradingToolCategory {
  id: string;
  title: string;
  description: string;
  groups: TradingToolGroup[];
}

export type TradingToolCategoryId =
  | 'macro'
  | 'equity'
  | 'crypto'
  | 'metal'
  | 'quant'
  | 'general';

export const tradingToolPageMeta = {
  title: '交易工具',
  eyebrow: 'Trading Toolkit',
  summary: '按你最新 Markdown 清单同步后的交易工具页。',
} as const;

export const tradingToolCategories: TradingToolCategory[] = [
    {
        "id":  "macro",
        "title":  "宏观工具",
        "description":  "利率、流动性、债券、经济数据与跨区域宏观跟踪。",
        "groups":  [
                       {
                           "id":  "macro-宏观总览",
                           "title":  "宏观总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027宏观总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "macro-tradingeconomics-com-1",
                                             "name":  "经济日历tradingeconomics",
                                             "url":  "https://tradingeconomics.com/calendar",
                                             "description":  "来源：宏观总览",
                                             "domain":  "tradingeconomics.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-jin10-com-1",
                                             "name":  "金十数据官网站",
                                             "url":  "https://www.jin10.com/",
                                             "description":  "来源：宏观总览",
                                             "domain":  "www.jin10.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-thedailyshot-com-1",
                                             "name":  "每日宏观简讯",
                                             "url":  "https://thedailyshot.com/",
                                             "description":  "来源：宏观总览",
                                             "domain":  "thedailyshot.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-cmegroup-com-1",
                                             "name":  "CME 美联储路径",
                                             "url":  "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
                                             "description":  "来源：宏观总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-datacenter-jin10-com-1",
                                             "name":  "金十数据中心",
                                             "url":  "https://datacenter.jin10.com/",
                                             "description":  "来源：宏观总览",
                                             "domain":  "datacenter.jin10.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-en-macromicro-me-1",
                                             "name":  "macromicro宏观数据日报",
                                             "url":  "https://en.macromicro.me/quickie",
                                             "description":  "来源：宏观总览",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-x-qhkch-com-1",
                                             "name":  "经济数据 - 奇货可查",
                                             "url":  "https://x.qhkch.com/fundamental/nationGdpMetrics?country=%E7%BE%8E%E5%9B%BD",
                                             "description":  "来源：宏观总览",
                                             "domain":  "x.qhkch.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-macro-ops-com-1",
                                             "name":  "宏观交易策略",
                                             "url":  "https://macro-ops.com/",
                                             "description":  "来源：宏观总览",
                                             "domain":  "macro-ops.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-robo-datayes-com-1",
                                             "name":  "宏观经济+股市 萝卜投研",
                                             "url":  "https://robo.datayes.com/v2/landing/macrogrp",
                                             "description":  "来源：宏观总览",
                                             "domain":  "robo.datayes.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-tradingeconomics-com-2",
                                             "name":  "各国宏观经济指标 | 按类别列出",
                                             "url":  "https://tradingeconomics.com/indicators",
                                             "description":  "来源：宏观总览",
                                             "domain":  "tradingeconomics.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-haver-com-1",
                                             "name":  "Haver宏观评论",
                                             "url":  "https://www.haver.com/",
                                             "description":  "来源：宏观总览",
                                             "domain":  "www.haver.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-forexfactory-com-1",
                                             "name":  "日历 | AI好读取",
                                             "url":  "https://www.forexfactory.com/calendar?day=jan3.2026",
                                             "description":  "来源：宏观总览",
                                             "domain":  "www.forexfactory.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-truflation-com-1",
                                             "name":  "其他宏观数据图表库",
                                             "url":  "https://truflation.com/marketplace?auth=google\u0026code=e2e58bd7-c221-4d97-9997-ad2d612810a2\u0026isSigningUp=true\u0026period=annual\u0026stake=false\u0026tier=undefined",
                                             "description":  "来源：宏观总览",
                                             "domain":  "truflation.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-notion-so-1",
                                             "name":  "宏观边际",
                                             "url":  "https://www.notion.so/trusting-glitter-4f0/MacroMargin-27e6782525ab41e188cb81510803d95b",
                                             "description":  "来源：宏观总览",
                                             "domain":  "www.notion.so",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-wx-zsxq-com-1",
                                             "name":  "知识星球",
                                             "url":  "https://wx.zsxq.com/login",
                                             "description":  "来源：宏观总览",
                                             "domain":  "wx.zsxq.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-vaneck-com-1",
                                             "name":  "VanEck 分析",
                                             "url":  "https://www.vaneck.com/asia/en/insights/",
                                             "description":  "来源：宏观总览",
                                             "domain":  "www.vaneck.com",
                                             "tags":  [
                                                          "宏观",
                                                          "宏观总览"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "macro-美联储-美国经济数据",
                           "title":  "美联储、美国经济数据",
                           "description":  "来自你整理后的 Markdown 分组 \u0027美联储、美国经济数据\u0027。",
                           "tools":  [
                                         {
                                             "id":  "macro-www-newyorkfed-org-1",
                                             "name":  "Repo Operations",
                                             "url":  "https://www.newyorkfed.org/markets/desk-operations/repo",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.newyorkfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-sc-macromicro-me-1",
                                             "name":  "利率\u0026美资产负债表vs.黄金",
                                             "url":  "https://sc.macromicro.me/collections/45/mm-gold-price/24057/us-fed-funds-rate-and-total-assets-vs-gold-price",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "sc.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-1",
                                             "name":  "信用利差",
                                             "url":  "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-federalreserve-gov-1",
                                             "name":  "美联储资产负债表",
                                             "url":  "https://www.federalreserve.gov/releases/h41/",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.federalreserve.gov",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-federalreserve-gov-2",
                                             "name":  "美联储 - 会议日程和信息",
                                             "url":  "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.federalreserve.gov",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-federalreserve-gov-3",
                                             "name":  "FOMC会议声明/记者会",
                                             "url":  "https://www.federalreserve.gov/videos.htm",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.federalreserve.gov",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-sc-macromicro-me-2",
                                             "name":  "美国-美联储负债端结构|MacroMicro",
                                             "url":  "https://sc.macromicro.me/collections/4238/us-federal/1320/us-fed-liabilities-structure",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "sc.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-2",
                                             "name":  "担保隔夜融资利率 (SOFR)",
                                             "url":  "https://fred.stlouisfed.org/series/SOFR",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-3",
                                             "name":  "10年期盈亏平衡通胀率 (T10YIE)",
                                             "url":  "https://fred.stlouisfed.org/series/T10YIE",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-4",
                                             "name":  "10年期固定期限美债市场收益率，通胀保值 DFII10)",
                                             "url":  "https://fred.stlouisfed.org/series/DFII10",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-en-macromicro-me-2",
                                             "name":  "各国央行利率",
                                             "url":  "https://en.macromicro.me/central_bank/overview",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-en-macromicro-me-3",
                                             "name":  "各国央行加息/降息预期（2024年）| MacroMicro",
                                             "url":  "https://en.macromicro.me/charts/89119/cbs-interest-rate-cuts-expectation-2024",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-5",
                                             "name":  "利差/标普相关性",
                                             "url":  "https://fred.stlouisfed.org/series/BAMLH0A0HYM2#0",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-newyorkfed-org-2",
                                             "name":  "纽约联邦储备银行",
                                             "url":  "https://www.newyorkfed.org/",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.newyorkfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fraser-stlouisfed-org-1",
                                             "name":  "美联储历史",
                                             "url":  "https://fraser.stlouisfed.org/",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fraser.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-newyorkfed-org-3",
                                             "name":  "咨询小组 - 纽约联邦储备银行",
                                             "url":  "https://www.newyorkfed.org/aboutthefed/external_committees",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.newyorkfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-home-treasury-gov-1",
                                             "name":  "U.S. Department of the Treasury",
                                             "url":  "https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/most-recent-quarterly-refunding-documents,",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "home.treasury.gov",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-6",
                                             "name":  "美联储经济数据",
                                             "url":  "https://fred.stlouisfed.org/",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-atlantafed-org-1",
                                             "name":  "GDPNow - 亚特兰大联邦储备银行",
                                             "url":  "https://www.atlantafed.org/cqer/research/gdpnow",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.atlantafed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-atlantafed-org-2",
                                             "name":  "亚特兰大工资增长追踪",
                                             "url":  "https://www.atlantafed.org/chcs/wage-growth-tracker",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.atlantafed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-7",
                                             "name":  "核心PCE",
                                             "url":  "https://fred.stlouisfed.org/series/DPCCRV1Q225SBEA",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-macromicro-me-1",
                                             "name":  "美国PCE＆corePCE(年增率)",
                                             "url":  "https://www.macromicro.me/charts/107685/mei-guo-PCE-corePCE-nian-zeng-lyu",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-clevelandfed-org-1",
                                             "name":  "10年期通胀预期和风险溢价",
                                             "url":  "https://www.clevelandfed.org/indicators-and-data/inflation-expectations",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.clevelandfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-newyorkfed-org-4",
                                             "name":  "1/3/5消费者通胀预期",
                                             "url":  "https://www.newyorkfed.org/microeconomics/sce#/inflexp-1",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.newyorkfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-clevelandfed-org-2",
                                             "name":  "PCE预测",
                                             "url":  "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.clevelandfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-sc-macromicro-me-3",
                                             "name":  "美国CPI(环比)",
                                             "url":  "https://sc.macromicro.me/collections/5/us-price-relative/89/cpi-items-mom",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "sc.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-8",
                                             "name":  "10年期国债-2年期国债利率（T10Y2Y）",
                                             "url":  "https://fred.stlouisfed.org/series/T10Y2Y",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-9",
                                             "name":  "职位空缺：非农就业数据 (JTSJOL)",
                                             "url":  "https://fred.stlouisfed.org/series/JTSJOL",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-en-macromicro-me-4",
                                             "name":  "美国ADP 非农就业数据",
                                             "url":  "https://en.macromicro.me/collections/4/us-employ-relative/36/adp",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-en-macromicro-me-5",
                                             "name":  "美国劳动力市场",
                                             "url":  "https://en.macromicro.me/collections/4/us-employ-relative/87/jolts",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-10",
                                             "name":  "劳动力参与率 (CIVPART)",
                                             "url":  "https://fred.stlouisfed.org/series/CIVPART",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-11",
                                             "name":  "个人储蓄率 (PSAVERT)",
                                             "url":  "https://fred.stlouisfed.org/series/PSAVERT",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-12",
                                             "name":  "信用卡贷款拖欠率 (DRCCLACBS)",
                                             "url":  "https://fred.stlouisfed.org/series/DRCCLACBS",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-13",
                                             "name":  "美国30年期固定利率抵押贷款平均值 (MORTGAGE30US)",
                                             "url":  "https://fred.stlouisfed.org/series/MORTGAGE30US",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-en-macromicro-me-6",
                                             "name":  "美国——银行收紧商业和工业贷款标准的净百分比",
                                             "url":  "https://en.macromicro.me/charts/1241/us-bank-net-percent-tight-loan",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-redfin-com-1",
                                             "name":  "美国房地产市场和价格",
                                             "url":  "https://www.redfin.com/us-housing-market",
                                             "description":  "来源：美联储、美国经济数据",
                                             "domain":  "www.redfin.com",
                                             "tags":  [
                                                          "宏观",
                                                          "美联储、美国经济数据"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "macro-美债类",
                           "title":  "美债类",
                           "description":  "来自你整理后的 Markdown 分组 \u0027美债类\u0027。",
                           "tools":  [
                                         {
                                             "id":  "macro-treasurydirect-gov-1",
                                             "name":  "美债拍卖时间",
                                             "url":  "https://treasurydirect.gov/auctions/upcoming/",
                                             "description":  "来源：美债类",
                                             "domain":  "treasurydirect.gov",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-treasurydirect-gov-1",
                                             "name":  "国债拍卖",
                                             "url":  "https://www.treasurydirect.gov/auctions/announcements-data-results/announcement-results-press-releases/",
                                             "description":  "来源：美债类",
                                             "domain":  "www.treasurydirect.gov",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-usdebtclock-org-1",
                                             "name":  "美国债务时钟",
                                             "url":  "https://www.usdebtclock.org/",
                                             "description":  "来源：美债类",
                                             "domain":  "www.usdebtclock.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-ticdata-treasury-gov-1",
                                             "name":  "各国美债持有仓位占比",
                                             "url":  "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html",
                                             "description":  "来源：美债类",
                                             "domain":  "ticdata.treasury.gov",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-en-macromicro-me-7",
                                             "name":  "10年期美债买卖比",
                                             "url":  "https://en.macromicro.me/collections/51/us-treasury-bond/30431/us-10y-bid-to-cover-ratio",
                                             "description":  "来源：美债类",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-sc-macromicro-me-4",
                                             "name":  "美国-财政部每月债券发行量 | MacroMicro 财经M平方",
                                             "url":  "https://sc.macromicro.me/charts/4458/us-treasury-issuance-gross",
                                             "description":  "来源：美债类",
                                             "domain":  "sc.macromicro.me",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-fred-stlouisfed-org-14",
                                             "name":  "美国债务占国内生产总值的百分比 (GFDEGDQ188S)",
                                             "url":  "https://fred.stlouisfed.org/series/GFDEGDQ188S",
                                             "description":  "来源：美债类",
                                             "domain":  "fred.stlouisfed.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-pgpf-org-1",
                                             "name":  "国家债务时钟：现在的国家债务是多少？",
                                             "url":  "https://www.pgpf.org/national-debt-clock/",
                                             "description":  "来源：美债类",
                                             "domain":  "www.pgpf.org",
                                             "tags":  [
                                                          "宏观",
                                                          "美债类"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "macro-其他",
                           "title":  "其他",
                           "description":  "来自你整理后的 Markdown 分组 \u0027其他\u0027。",
                           "tools":  [
                                         {
                                             "id":  "macro-www-ici-org-1",
                                             "name":  "机构现金仓位",
                                             "url":  "https://www.ici.org/research/stats/mmf",
                                             "description":  "来源：其他",
                                             "domain":  "www.ici.org",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-data-worldbank-org-1",
                                             "name":  "世界银行开放数据 | 各国长期经济数据对比",
                                             "url":  "https://data.worldbank.org/",
                                             "description":  "来源：其他",
                                             "domain":  "data.worldbank.org",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-worldpopulationreview-com-1",
                                             "name":  "各国债务/GDP占比",
                                             "url":  "https://worldpopulationreview.com/country-rankings/countries-by-national-debt",
                                             "description":  "来源：其他",
                                             "domain":  "worldpopulationreview.com",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-population-pyramid-net-1",
                                             "name":  "世界各国的人口金字塔 2025 - 人口金字塔",
                                             "url":  "https://population-pyramid.net/zh-cn",
                                             "description":  "来源：其他",
                                             "domain":  "population-pyramid.net",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-tradingeconomics-com-3",
                                             "name":  "全球数据",
                                             "url":  "https://tradingeconomics.com/",
                                             "description":  "来源：其他",
                                             "domain":  "tradingeconomics.com",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-imf-org-1",
                                             "name":  "IMF全球金融/外汇/债务指标数据库",
                                             "url":  "https://www.imf.org/en/Data",
                                             "description":  "来源：其他",
                                             "domain":  "www.imf.org",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-news-usni-org-1",
                                             "name":  "美国航母动态",
                                             "url":  "https://news.usni.org/2025/06/09/usni-news-fleet-and-marine-tracker-june-9-2025",
                                             "description":  "来源：其他",
                                             "domain":  "news.usni.org",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         },
                                         {
                                             "id":  "macro-www-flightradar24-com-1",
                                             "name":  "各国领空情况",
                                             "url":  "https://www.flightradar24.com/30.37,52.68/5",
                                             "description":  "来源：其他",
                                             "domain":  "www.flightradar24.com",
                                             "tags":  [
                                                          "宏观",
                                                          "其他"
                                                      ]
                                         }
                                     ]
                       }
                   ]
    },
    {
        "id":  "equity",
        "title":  "股市工具",
        "description":  "股票、ETF、财报、持仓与市场情绪观察。",
        "groups":  [
                       {
                           "id":  "equity-股市总览",
                           "title":  "股市总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027股市总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "equity-pro-openbb-co-1",
                                             "name":  "OpenBB 工作区",
                                             "url":  "https://pro.openbb.co/app/ad4c0196-5796-4114-bcec-cf6dc21f914d",
                                             "description":  "来源：股市总览",
                                             "domain":  "pro.openbb.co",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-companiesmarketcap-com-1",
                                             "name":  "美国公司市值排名",
                                             "url":  "https://companiesmarketcap.com/usa/largest-companies-in-the-usa-by-market-cap/",
                                             "description":  "来源：股市总览",
                                             "domain":  "companiesmarketcap.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-dapanyuntu-com-1",
                                             "name":  "A股板块走势",
                                             "url":  "https://dapanyuntu.com/",
                                             "description":  "来源：股市总览",
                                             "domain":  "dapanyuntu.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-finviz-com-1",
                                             "name":  "股票筛选器和热力图--FINVIZ.com",
                                             "url":  "https://finviz.com/",
                                             "description":  "来源：股市总览",
                                             "domain":  "finviz.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-finviz-com-2",
                                             "name":  "finviz财报可视化",
                                             "url":  "https://finviz.com/quote.ashx?t=AAPL\u0026ty=ea\u0026p=d\u0026b=1",
                                             "description":  "来源：股市总览",
                                             "domain":  "finviz.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-en-macromicro-me-1",
                                             "name":  "美股市场情绪指数",
                                             "url":  "https://en.macromicro.me/charts/80778/US-CNN-Fear-and-Greed-Index",
                                             "description":  "来源：股市总览",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-tickernerd-com-1",
                                             "name":  "Ticker Nerd 股票文件查找",
                                             "url":  "https://tickernerd.com/resources/",
                                             "description":  "来源：股市总览",
                                             "domain":  "tickernerd.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-sec-gov-1",
                                             "name":  "SEC财报",
                                             "url":  "https://www.sec.gov/",
                                             "description":  "来源：股市总览",
                                             "domain":  "www.sec.gov",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-insight-factset-com-1",
                                             "name":  "每季度财报统计及forward EPS/PE",
                                             "url":  "https://insight.factset.com/topic/earnings",
                                             "description":  "来源：股市总览",
                                             "domain":  "insight.factset.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-whalewisdom-com-1",
                                             "name":  "利用13F文件和鲸鱼数据追踪对冲基金投资组合",
                                             "url":  "https://whalewisdom.com/",
                                             "description":  "来源：股市总览",
                                             "domain":  "whalewisdom.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-seekingalpha-com-1",
                                             "name":  "Seeking Alpha | 股市分析及投资者工具",
                                             "url":  "https://seekingalpha.com/",
                                             "description":  "来源：股市总览",
                                             "domain":  "seekingalpha.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-lixinger-com-1",
                                             "name":  "社保机构持仓",
                                             "url":  "https://www.lixinger.com/analytics/shareholders/search",
                                             "description":  "来源：股市总览",
                                             "domain":  "www.lixinger.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-ark-alien-tomato-com-1",
                                             "name":  "Ark基金最新动向",
                                             "url":  "https://ark.alien-tomato.com/",
                                             "description":  "来源：股市总览",
                                             "domain":  "ark.alien-tomato.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-perplexity-ai-1",
                                             "name":  "美国议员投资组合",
                                             "url":  "https://www.perplexity.ai/finance/politicians",
                                             "description":  "来源：股市总览",
                                             "domain":  "www.perplexity.ai",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-cninfo-com-cn-1",
                                             "name":  "A股巨潮资讯网",
                                             "url":  "https://www.cninfo.com.cn/new/index.jsp",
                                             "description":  "来源：股市总览",
                                             "domain":  "www.cninfo.com.cn",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-robo-datayes-com-1",
                                             "name":  "萝卜投研-智能股票投研",
                                             "url":  "https://robo.datayes.com/",
                                             "description":  "来源：股市总览",
                                             "domain":  "robo.datayes.com",
                                             "tags":  [
                                                          "股市",
                                                          "股市总览"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "equity-etf总览",
                           "title":  "ETF总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027ETF总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "equity-www-etf-com-1",
                                             "name":  "ETF 比较工具",
                                             "url":  "https://www.etf.com/tools/etf-comparison",
                                             "description":  "来源：ETF总览",
                                             "domain":  "www.etf.com",
                                             "tags":  [
                                                          "股市",
                                                          "ETF总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-etfrc-com-1",
                                             "name":  "ETF研究中心",
                                             "url":  "https://www.etfrc.com/",
                                             "description":  "来源：ETF总览",
                                             "domain":  "www.etfrc.com",
                                             "tags":  [
                                                          "股市",
                                                          "ETF总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-etfdb-com-1",
                                             "name":  "ETF 数据库：ETF 原创综合指南",
                                             "url":  "https://etfdb.com/",
                                             "description":  "来源：ETF总览",
                                             "domain":  "etfdb.com",
                                             "tags":  [
                                                          "股市",
                                                          "ETF总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-etf-com-2",
                                             "name":  "ETF 基金流量工具",
                                             "url":  "https://www.etf.com/etfanalytics/etf-fund-flows-tool",
                                             "description":  "来源：ETF总览",
                                             "domain":  "www.etf.com",
                                             "tags":  [
                                                          "股市",
                                                          "ETF总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-lazyportfolioetf-com-1",
                                             "name":  "懒惰投资组合和ETF组合",
                                             "url":  "https://www.lazyportfolioetf.com/#google_vignette",
                                             "description":  "来源：ETF总览",
                                             "domain":  "www.lazyportfolioetf.com",
                                             "tags":  [
                                                          "股市",
                                                          "ETF总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-www-portfoliovisualizer-com-1",
                                             "name":  "投资组合可视化工具",
                                             "url":  "https://www.portfoliovisualizer.com/",
                                             "description":  "来源：ETF总览",
                                             "domain":  "www.portfoliovisualizer.com",
                                             "tags":  [
                                                          "股市",
                                                          "ETF总览"
                                                      ]
                                         },
                                         {
                                             "id":  "equity-funddb-cn-1",
                                             "name":  "韭圈儿_基金配置高手聚集地",
                                             "url":  "https://funddb.cn/",
                                             "description":  "来源：ETF总览",
                                             "domain":  "funddb.cn",
                                             "tags":  [
                                                          "股市",
                                                          "ETF总览"
                                                      ]
                                         }
                                     ]
                       }
                   ]
    },
    {
        "id":  "crypto",
        "title":  "加密工具",
        "description":  "研报、交易、链上、基本面与媒体信息入口。",
        "groups":  [
                       {
                           "id":  "crypto-研报类",
                           "title":  "研报类",
                           "description":  "来自你整理后的 Markdown 分组 \u0027研报类\u0027。",
                           "tools":  [
                                         {
                                             "id":  "crypto-insights-glassnode-com-1",
                                             "name":  "Glassnode 每周简报",
                                             "url":  "https://insights.glassnode.com/tag/newsletter/",
                                             "description":  "来源：研报类",
                                             "domain":  "insights.glassnode.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-research-glassnode-com-1",
                                             "name":  "Glassnode 市场脉搏",
                                             "url":  "https://research.glassnode.com/tag/market-pulse/",
                                             "description":  "来源：研报类",
                                             "domain":  "research.glassnode.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-galaxy-com-1",
                                             "name":  "Galaxy 研究",
                                             "url":  "https://www.galaxy.com/insights/research",
                                             "description":  "来源：研报类",
                                             "domain":  "www.galaxy.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinbase-com-1",
                                             "name":  "Coinbase 机构研究",
                                             "url":  "https://www.coinbase.com/zh-cn/institutional/research-insights/research",
                                             "description":  "来源：研报类",
                                             "domain":  "www.coinbase.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-a16zcrypto-substack-com-1",
                                             "name":  "a16z 加密研究",
                                             "url":  "https://a16zcrypto.substack.com/",
                                             "description":  "来源：研报类",
                                             "domain":  "a16zcrypto.substack.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-vaneck-com-1",
                                             "name":  "VanEck 数字资产",
                                             "url":  "https://www.vaneck.com/us/en/insights/digital-assets/?p=1",
                                             "description":  "来源：研报类",
                                             "domain":  "www.vaneck.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-river-com-1",
                                             "name":  "River 比特币研究",
                                             "url":  "https://river.com/research",
                                             "description":  "来源：研报类",
                                             "domain":  "river.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-research-grayscale-com-1",
                                             "name":  "Grayscale 研究",
                                             "url":  "https://research.grayscale.com/",
                                             "description":  "来源：研报类",
                                             "domain":  "research.grayscale.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-binance-com-1",
                                             "name":  "币安研究院",
                                             "url":  "https://www.binance.com/zh-CN/research",
                                             "description":  "来源：研报类",
                                             "domain":  "www.binance.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-ark-invest-com-1",
                                             "name":  "ARK 研究文章",
                                             "url":  "https://www.ark-invest.com/articles",
                                             "description":  "来源：研报类",
                                             "domain":  "www.ark-invest.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-bitwiseinvestments-com-1",
                                             "name":  "Bitwise 市场洞察",
                                             "url":  "https://bitwiseinvestments.com/crypto-market-insights",
                                             "description":  "来源：研报类",
                                             "domain":  "bitwiseinvestments.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-experts-bitwiseinvestments-com-1",
                                             "name":  "Bitwise 每周分析",
                                             "url":  "https://experts.bitwiseinvestments.com/cio-memos",
                                             "description":  "来源：研报类",
                                             "domain":  "experts.bitwiseinvestments.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-members-delphidigital-io-1",
                                             "name":  "Messari / Delphi 前瞻报告",
                                             "url":  "https://members.delphidigital.io/reports/the-year-ahead-for-markets-2026#concluding-thoughts-949c",
                                             "description":  "来源：研报类",
                                             "domain":  "members.delphidigital.io",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-cryptohayes-substack-com-1",
                                             "name":  "Arthur Hayes 研究",
                                             "url":  "https://cryptohayes.substack.com/",
                                             "description":  "来源：研报类",
                                             "domain":  "cryptohayes.substack.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-coinshares-com-1",
                                             "name":  "CoinShares 洞察",
                                             "url":  "https://coinshares.com/corp/insights/",
                                             "description":  "来源：研报类",
                                             "domain":  "coinshares.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-unbias-fyi-1",
                                             "name":  "Unbias 分析师聚合",
                                             "url":  "https://unbias.fyi/analysts?source=all",
                                             "description":  "来源：研报类",
                                             "domain":  "unbias.fyi",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-x-com-1",
                                             "name":  "Market Beggar",
                                             "url":  "https://x.com/market_beggar",
                                             "description":  "来源：研报类",
                                             "domain":  "x.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-supersaiyan1957-substack-com-1",
                                             "name":  "BTC美股周报告",
                                             "url":  "https://supersaiyan1957.substack.com/",
                                             "description":  "来源：研报类",
                                             "domain":  "supersaiyan1957.substack.com",
                                             "tags":  [
                                                          "加密",
                                                          "研报类"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "crypto-交易类",
                           "title":  "交易类",
                           "description":  "来自你整理后的 Markdown 分组 \u0027交易类\u0027。",
                           "tools":  [
                                         {
                                             "id":  "crypto-www-macromicro-me-1",
                                             "name":  "比特币BTC驱动三大因素：流动性＆实际利率＆PE",
                                             "url":  "https://www.macromicro.me/collections/22514/bi-te-bi_418919/111972/bi-te-bi-BTC-qu-dong-san-da-yin-su-liu-dong-xing-shi-ji-li-lyu-GDP",
                                             "description":  "来源：交易类",
                                             "domain":  "www.macromicro.me",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-1",
                                             "name":  "减半后表现",
                                             "url":  "https://www.coinglass.com/pro/i/bitcoin-price-performance-since-halving",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-2",
                                             "name":  "Coinglass 资费+持仓量",
                                             "url":  "https://www.coinglass.com/tv/zh/Binance_BTCUSDT",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-3",
                                             "name":  "爆仓热力图",
                                             "url":  "https://www.coinglass.com/zh/pro/futures/LiquidationHeatMap",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-charts-checkonchain-com-1",
                                             "name":  "BTC 期限结构",
                                             "url":  "https://charts.checkonchain.com/btconchain/derivatives/derivatives_termstructure_0/derivatives_termstructure_0_light.html",
                                             "description":  "来源：交易类",
                                             "domain":  "charts.checkonchain.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-greeks-live-1",
                                             "name":  "Greeks.live BTC 数据实验室",
                                             "url":  "https://www.greeks.live/deribit/tools/datalab/BTC",
                                             "description":  "来源：交易类",
                                             "domain":  "www.greeks.live",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-deribit-com-1",
                                             "name":  "Deribit 期权指标",
                                             "url":  "https://www.deribit.com/statistics/BTC/metrics/options",
                                             "description":  "来源：交易类",
                                             "domain":  "www.deribit.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-4",
                                             "name":  "加密衍生品指数",
                                             "url":  "https://www.coinglass.com/zh/pro/i/CGDI",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-5",
                                             "name":  "Coinbase 溢价指数",
                                             "url":  "https://www.coinglass.com/pro/i/coinbase-bitcoin-premium-index",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-6",
                                             "name":  "ETF 溢折价",
                                             "url":  "https://www.coinglass.com/pro/etf/Premium",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-7",
                                             "name":  "未平仓合约",
                                             "url":  "https://www.coinglass.com/zh/pro/futures/OpenInterest",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-8",
                                             "name":  "恐慌与贪婪指数",
                                             "url":  "https://www.coinglass.com/zh/pro/i/FearGreedIndex",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-9",
                                             "name":  "杠杆借贷成本",
                                             "url":  "https://www.coinglass.com/zh/pro/i/MarginFeeChart",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-10",
                                             "name":  "资金费率",
                                             "url":  "https://www.coinglass.com/FundingRate",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-charts-checkonchain-com-2",
                                             "name":  "Checkonchain 图表库",
                                             "url":  "https://charts.checkonchain.com/",
                                             "description":  "来源：交易类",
                                             "domain":  "charts.checkonchain.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-studio-glassnode-com-1",
                                             "name":  "Glassnode 活跃地址",
                                             "url":  "https://studio.glassnode.com/charts/addresses.ActiveCount?a=BTC",
                                             "description":  "来源：交易类",
                                             "domain":  "studio.glassnode.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-11",
                                             "name":  "加密热力图",
                                             "url":  "https://www.coinglass.com/zh/pro/heatmap/price-change",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-sosovalue-com-1",
                                             "name":  "加密各板块指数",
                                             "url":  "https://sosovalue.com/zh/assets/cryptoindex/verified-index",
                                             "description":  "来源：交易类",
                                             "domain":  "sosovalue.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-cryptobubbles-net-1",
                                             "name":  "CryptoBubbles 泡泡图",
                                             "url":  "https://cryptobubbles.net/",
                                             "description":  "来源：交易类",
                                             "domain":  "cryptobubbles.net",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-coinmarketcap-com-1",
                                             "name":  "CoinMarketCap 市值总览",
                                             "url":  "https://coinmarketcap.com/",
                                             "description":  "来源：交易类",
                                             "domain":  "coinmarketcap.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-12",
                                             "name":  "CME / CFTC 持仓",
                                             "url":  "https://www.coinglass.com/pro/cme/cftc",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-13",
                                             "name":  "多空比",
                                             "url":  "https://www.coinglass.com/LongShortRatio",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-14",
                                             "name":  "Hyperliquid 钱包多空分布",
                                             "url":  "https://www.coinglass.com/hl",
                                             "description":  "来源：交易类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-charts-bgeometrics-com-1",
                                             "name":  "大小鲸鱼购买情况以及其他链上指标",
                                             "url":  "https://charts.bgeometrics.com/bitcoin_distribution_coins_tables.html",
                                             "description":  "来源：交易类",
                                             "domain":  "charts.bgeometrics.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-cryptoquant-com-1",
                                             "name":  "加密各类链上数据 | CryptoQuant",
                                             "url":  "https://cryptoquant.com/asset/btc/summary",
                                             "description":  "来源：交易类",
                                             "domain":  "cryptoquant.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-tokenomist-ai-1",
                                             "name":  "代币解锁 | 追踪最新数据并完成解锁计划",
                                             "url":  "https://tokenomist.ai/",
                                             "description":  "来源：交易类",
                                             "domain":  "tokenomist.ai",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-intel-arkm-com-1",
                                             "name":  "链上 | Arkham",
                                             "url":  "https://intel.arkm.com/",
                                             "description":  "来源：交易类",
                                             "domain":  "intel.arkm.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-oklink-com-1",
                                             "name":  "区块链浏览器查询 | 欧科云链 OKLink",
                                             "url":  "https://www.oklink.com/zh-hans",
                                             "description":  "来源：交易类",
                                             "domain":  "www.oklink.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-stats-hyperliquid-xyz-1",
                                             "name":  "Hyperliquid 统计数据",
                                             "url":  "https://stats.hyperliquid.xyz/",
                                             "description":  "来源：交易类",
                                             "domain":  "stats.hyperliquid.xyz",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-charts-checkonchain-com-3",
                                             "name":  "比特币链上分析与图表",
                                             "url":  "https://charts.checkonchain.com/",
                                             "description":  "来源：交易类",
                                             "domain":  "charts.checkonchain.com",
                                             "tags":  [
                                                          "加密",
                                                          "交易类"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "crypto-基本面类",
                           "title":  "基本面类",
                           "description":  "来自你整理后的 Markdown 分组 \u0027基本面类\u0027。",
                           "tools":  [
                                         {
                                             "id":  "crypto-www-benjamincowen-com-1",
                                             "name":  "Benjamin Cowen网站",
                                             "url":  "https://www.benjamincowen.com/#services",
                                             "description":  "来源：基本面类",
                                             "domain":  "www.benjamincowen.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-bitcoinlaws-io-1",
                                             "name":  "Bitcoin Laws 政策追踪",
                                             "url":  "https://bitcoinlaws.io/",
                                             "description":  "来源：基本面类",
                                             "domain":  "bitcoinlaws.io",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-sosovalue-com-2",
                                             "name":  "SoSoValue BTC / ETH ETF",
                                             "url":  "https://sosovalue.com/zh/assets/etf/us-btc-spot",
                                             "description":  "来源：基本面类",
                                             "domain":  "sosovalue.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-sosovalue-com-3",
                                             "name":  "SoSoValue 比特币储备",
                                             "url":  "https://sosovalue.com/zh/assets/bitcoin-treasuries",
                                             "description":  "来源：基本面类",
                                             "domain":  "sosovalue.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-15",
                                             "name":  "Coinglass 比特币储备总量",
                                             "url":  "https://www.coinglass.com/BitcoinTreasuries",
                                             "description":  "来源：基本面类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-bitcointreasuries-net-1",
                                             "name":  "BTC分布明细",
                                             "url":  "https://bitcointreasuries.net/",
                                             "description":  "来源：基本面类",
                                             "domain":  "bitcointreasuries.net",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-strategicethreserve-xyz-1",
                                             "name":  "战略 ETH 储备",
                                             "url":  "https://www.strategicethreserve.xyz/",
                                             "description":  "来源：基本面类",
                                             "domain":  "www.strategicethreserve.xyz",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coinglass-com-16",
                                             "name":  "政府比特币储备",
                                             "url":  "https://www.coinglass.com/zh/pro/i/bitcoin-government-treasuries",
                                             "description":  "来源：基本面类",
                                             "domain":  "www.coinglass.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-saylortracker-com-1",
                                             "name":  "微策略购买记录",
                                             "url":  "https://saylortracker.com/",
                                             "description":  "来源：基本面类",
                                             "domain":  "saylortracker.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-strc-live-1",
                                             "name":  "STRC",
                                             "url":  "https://strc.live/ticker/strc",
                                             "description":  "来源：基本面类",
                                             "domain":  "strc.live",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-rwa-xyz-1",
                                             "name":  "RWA.xyz",
                                             "url":  "https://app.rwa.xyz/",
                                             "description":  "来源：基本面类",
                                             "domain":  "app.rwa.xyz",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-intothecryptoverse-com-1",
                                             "name":  "仪表板 | ITC",
                                             "url":  "https://app.intothecryptoverse.com/dashboard",
                                             "description":  "来源：基本面类",
                                             "domain":  "app.intothecryptoverse.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-hypurrscan-io-1",
                                             "name":  "HypurrScan",
                                             "url":  "https://hypurrscan.io/address/0x5078C2fBeA2b2aD61bc840Bc023E35Fce56BeDb6?s=09",
                                             "description":  "来源：基本面类",
                                             "domain":  "hypurrscan.io",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-xxi-money-1",
                                             "name":  "21资本官网",
                                             "url":  "https://xxi.money/",
                                             "description":  "来源：基本面类",
                                             "domain":  "xxi.money",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-ishares-com-1",
                                             "name":  "IBIT官网",
                                             "url":  "https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf#/",
                                             "description":  "来源：基本面类",
                                             "domain":  "www.ishares.com",
                                             "tags":  [
                                                          "加密",
                                                          "基本面类"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "crypto-媒体类",
                           "title":  "媒体类",
                           "description":  "来自你整理后的 Markdown 分组 \u0027媒体类\u0027。",
                           "tools":  [
                                         {
                                             "id":  "crypto-foresightnews-pro-1",
                                             "name":  "Foresight News",
                                             "url":  "https://foresightnews.pro/",
                                             "description":  "来源：媒体类",
                                             "domain":  "foresightnews.pro",
                                             "tags":  [
                                                          "加密",
                                                          "媒体类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-jinse2-com-1",
                                             "name":  "金色财经",
                                             "url":  "https://www.jinse2.com/",
                                             "description":  "来源：媒体类",
                                             "domain":  "www.jinse2.com",
                                             "tags":  [
                                                          "加密",
                                                          "媒体类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-sosovalue-com-4",
                                             "name":  "SoSoValue 研究",
                                             "url":  "https://sosovalue.com/zh/research",
                                             "description":  "来源：媒体类",
                                             "domain":  "sosovalue.com",
                                             "tags":  [
                                                          "加密",
                                                          "媒体类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-techflowpost-com-1",
                                             "name":  "TechFlow",
                                             "url":  "https://www.techflowpost.com/",
                                             "description":  "来源：媒体类",
                                             "domain":  "www.techflowpost.com",
                                             "tags":  [
                                                          "加密",
                                                          "媒体类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-panewslab-com-1",
                                             "name":  "PANews",
                                             "url":  "https://www.panewslab.com/zh-hant",
                                             "description":  "来源：媒体类",
                                             "domain":  "www.panewslab.com",
                                             "tags":  [
                                                          "加密",
                                                          "媒体类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-theblock-co-1",
                                             "name":  "The Block",
                                             "url":  "https://www.theblock.co/",
                                             "description":  "来源：媒体类",
                                             "domain":  "www.theblock.co",
                                             "tags":  [
                                                          "加密",
                                                          "媒体类"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-theblockbeats-info-1",
                                             "name":  "BlockBeats",
                                             "url":  "https://www.theblockbeats.info/",
                                             "description":  "来源：媒体类",
                                             "domain":  "www.theblockbeats.info",
                                             "tags":  [
                                                          "加密",
                                                          "媒体类"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "crypto-理财与其他",
                           "title":  "理财与其他",
                           "description":  "来自你整理后的 Markdown 分组 \u0027理财与其他\u0027。",
                           "tools":  [
                                         {
                                             "id":  "crypto-app-barker-money-1",
                                             "name":  "Barker",
                                             "url":  "https://app.barker.money/campaigns",
                                             "description":  "来源：理财与其他",
                                             "domain":  "app.barker.money",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-rootdata-com-1",
                                             "name":  "Web3 热门项目排名",
                                             "url":  "https://www.rootdata.com/zh",
                                             "description":  "来源：理财与其他",
                                             "domain":  "www.rootdata.com",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-ethena-fi-1",
                                             "name":  "Ethena信息",
                                             "url":  "https://app.ethena.fi/dashboards/positions",
                                             "description":  "来源：理财与其他",
                                             "domain":  "app.ethena.fi",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-defillama-com-1",
                                             "name":  "Ethereum - DefiLlama",
                                             "url":  "https://defillama.com/chain/Ethereum",
                                             "description":  "来源：理财与其他",
                                             "domain":  "defillama.com",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-btc-com-1",
                                             "name":  "BTC.com数据与矿池",
                                             "url":  "https://btc.com/zh-CN",
                                             "description":  "来源：理财与其他",
                                             "domain":  "btc.com",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-dexscreener-com-1",
                                             "name":  "DEX Screener",
                                             "url":  "https://dexscreener.com/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "dexscreener.com",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-pendle-finance-1",
                                             "name":  "Pendle",
                                             "url":  "https://app.pendle.finance/trade/markets?utm_source=landing\u0026utm_medium=landing",
                                             "description":  "来源：理财与其他",
                                             "domain":  "app.pendle.finance",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-miningpoolstats-stream-1",
                                             "name":  "挖矿BTC数据",
                                             "url":  "https://miningpoolstats.stream/bitcoin",
                                             "description":  "来源：理财与其他",
                                             "domain":  "miningpoolstats.stream",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-morpho-org-1",
                                             "name":  "Morpho",
                                             "url":  "https://morpho.org/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "morpho.org",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-kamino-finance-1",
                                             "name":  "贷款 | 卡米诺金融",
                                             "url":  "https://app.kamino.finance/earn/lend",
                                             "description":  "来源：理财与其他",
                                             "domain":  "app.kamino.finance",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-lulo-fi-1",
                                             "name":  "Lulo",
                                             "url":  "https://app.lulo.fi/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "app.lulo.fi",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-uniswap-org-1",
                                             "name":  "Uniswap Ethereum 热门资金池",
                                             "url":  "https://app.uniswap.org/explore/pools",
                                             "description":  "来源：理财与其他",
                                             "domain":  "app.uniswap.org",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-app-spark-fi-1",
                                             "name":  "Spark：利用稳定币赚钱",
                                             "url":  "https://app.spark.fi/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "app.spark.fi",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-1key-so-1",
                                             "name":  "OneKey",
                                             "url":  "https://1key.so/earn",
                                             "description":  "来源：理财与其他",
                                             "domain":  "1key.so",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-apeoclock-com-1",
                                             "name":  "defi项目发布日历",
                                             "url":  "https://www.apeoclock.com/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "www.apeoclock.com",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-stake-lido-fi-1",
                                             "name":  "ETH质押",
                                             "url":  "https://stake.lido.fi/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "stake.lido.fi",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-cryptorank-io-1",
                                             "name":  "一级和预测市场：CryptoRank.io",
                                             "url":  "https://cryptorank.io/prediction-markets",
                                             "description":  "来源：理财与其他",
                                             "domain":  "cryptorank.io",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-bitbo-io-1",
                                             "name":  "比特币日历",
                                             "url":  "https://bitbo.io/calendar/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "bitbo.io",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-www-coincarp-com-1",
                                             "name":  "加密货币活动日历 | CoinCarp",
                                             "url":  "https://www.coincarp.com/events/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "www.coincarp.com",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-gmgn-ai-1",
                                             "name":  "聪明钱追踪--GMGN.AI",
                                             "url":  "https://gmgn.ai/?ref=NtZl14CJ\u0026chain=sol",
                                             "description":  "来源：理财与其他",
                                             "domain":  "gmgn.ai",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-axiom-trade-1",
                                             "name":  "聪明钱|discover",
                                             "url":  "https://axiom.trade/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "axiom.trade",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-dune-com-1",
                                             "name":  "Dune — 由社区提供支持的加密分析。",
                                             "url":  "https://dune.com/home",
                                             "description":  "来源：理财与其他",
                                             "domain":  "dune.com",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-uniscan-cc-1",
                                             "name":  "UniScan",
                                             "url":  "https://uniscan.cc/fractal/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "uniscan.cc",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-mempool-space-1",
                                             "name":  "mempool - Bitcoin Explorer",
                                             "url":  "https://mempool.space/zh/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "mempool.space",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-etherscan-io-1",
                                             "name":  "Ethereum Gas Tracker",
                                             "url":  "https://etherscan.io/gastracker",
                                             "description":  "来源：理财与其他",
                                             "domain":  "etherscan.io",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         },
                                         {
                                             "id":  "crypto-ultrasound-money-1",
                                             "name":  "ultrasound.money",
                                             "url":  "https://ultrasound.money/",
                                             "description":  "来源：理财与其他",
                                             "domain":  "ultrasound.money",
                                             "tags":  [
                                                          "加密",
                                                          "理财与其他"
                                                      ]
                                         }
                                     ]
                       }
                   ]
    },
    {
        "id":  "metal",
        "title":  "金属工具",
        "description":  "黄金、商品、库存、期限结构与贵金属观察。",
        "groups":  [
                       {
                           "id":  "metal-黄金总览",
                           "title":  "黄金总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027黄金总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "metal-chartexchange-com-1",
                                             "name":  "GLD 借款利率 (CTB) | ChartExchange",
                                             "url":  "https://chartexchange.com/symbol/nyse-gld/borrow-fee/",
                                             "description":  "来源：黄金总览",
                                             "domain":  "chartexchange.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-lbma-org-uk-1",
                                             "name":  "伦敦金库数据 | LBMA",
                                             "url":  "https://www.lbma.org.uk/prices-and-data/london-vault-data",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.lbma.org.uk",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-commoditieschart-net-1",
                                             "name":  "Comex 金库存",
                                             "url":  "https://commoditieschart.net/zh/metals/gold/comex-gold-stocks",
                                             "description":  "来源：黄金总览",
                                             "domain":  "commoditieschart.net",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-china-gold-org-1",
                                             "name":  "世界黄金协会：黄金ETF的持有量和流量 | World Gold Council",
                                             "url":  "https://china.gold.org/goldhub/data/gold-etfs-holdings-and-flows#from-login=1\u0026login-type=wechat",
                                             "description":  "来源：黄金总览",
                                             "domain":  "china.gold.org",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-gold-org-1",
                                             "name":  "各国央行黄金储备 | 世界黄金协会",
                                             "url":  "https://www.gold.org/goldhub/data/gold-reserves-by-country",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.gold.org",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-gold-org-2",
                                             "name":  "各大交易所未平仓合约数",
                                             "url":  "https://www.gold.org/goldhub/data/gold-open-interest",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.gold.org",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-china-gold-org-2",
                                             "name":  "黄金期货价格曲线｜世界黄金协会",
                                             "url":  "https://china.gold.org/goldhub/data/gold-futures-curves#from-login=1\u0026login-type=wechat",
                                             "description":  "来源：黄金总览",
                                             "domain":  "china.gold.org",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-sc-macromicro-me-1",
                                             "name":  "SPDR黄金ETF流量",
                                             "url":  "https://sc.macromicro.me/collections/45/mm-gold-price/23274/gld-fund-flow",
                                             "description":  "来源：黄金总览",
                                             "domain":  "sc.macromicro.me",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-sc-macromicro-me-2",
                                             "name":  "SPDR黄金ETF持仓量",
                                             "url":  "https://sc.macromicro.me/collections/45/mm-gold-price/712/spdr-gold-trust-etf-gold-price",
                                             "description":  "来源：黄金总览",
                                             "domain":  "sc.macromicro.me",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-jiaoyifamen-com-1",
                                             "name":  "交易法门",
                                             "url":  "https://www.jiaoyifamen.com/variety/positionAnalysis-CFTC",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.jiaoyifamen.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-cmegroup-com-1",
                                             "name":  "CVOL",
                                             "url":  "https://www.cmegroup.com/market-data/cme-group-benchmark-administration/cme-group-volatility-indexes.html",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-cmegroup-com-2",
                                             "name":  "黄金期货交易量与持仓量-CME",
                                             "url":  "https://www.cmegroup.com/markets/metals/precious/gold.volume.html?utm_source=chatgpt.com",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-cmegroup-com-3",
                                             "name":  "COT报告持仓",
                                             "url":  "https://www.cmegroup.com/tools-information/quikstrike/commitment-of-traders.html?pid=40#cmeloginteaser1",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-giresearch-substack-com-1",
                                             "name":  "黄金投资者研究|Chris Rutherglen博士|Substack",
                                             "url":  "https://giresearch.substack.com/?utm_source=%2Fsearch%2FGold%2520Investor%2520Research\u0026utm_medium=reader2\u0026utm_campaign=reader2",
                                             "description":  "来源：黄金总览",
                                             "domain":  "giresearch.substack.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-incrementum-li-1",
                                             "name":  "期刊 - Incrementum",
                                             "url":  "https://www.incrementum.li/en/journal/",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.incrementum.li",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-cmegroup-com-4",
                                             "name":  "Gold Option Volume \u0026 Open Interest",
                                             "url":  "https://www.cmegroup.com/markets/metals/precious/gold.volume.options.html#optionProductId=192",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-cmegroup-com-5",
                                             "name":  "金属每日交易量及未平仓合约",
                                             "url":  "https://www.cmegroup.com/market-data/browse-data/metals-volume.html",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-lbma-org-uk-2",
                                             "name":  "Clearing Data | LBMA",
                                             "url":  "https://www.lbma.org.uk/prices-and-data/clearing-data",
                                             "description":  "来源：黄金总览",
                                             "domain":  "www.lbma.org.uk",
                                             "tags":  [
                                                          "金属",
                                                          "黄金总览"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "metal-商品总览",
                           "title":  "商品总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027商品总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "metal-www-jiaoyifamen-com-2",
                                             "name":  "交易法门",
                                             "url":  "https://www.jiaoyifamen.com/variety/varieties-varieties",
                                             "description":  "来源：商品总览",
                                             "domain":  "www.jiaoyifamen.com",
                                             "tags":  [
                                                          "金属",
                                                          "商品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-x-qhkch-com-1",
                                             "name":  "国内商品期货各类数据- 奇货可查",
                                             "url":  "https://x.qhkch.com/variety/position",
                                             "description":  "来源：商品总览",
                                             "domain":  "x.qhkch.com",
                                             "tags":  [
                                                          "金属",
                                                          "商品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-en-macromicro-me-1",
                                             "name":  "US - Crack Spread vs. Oil Price",
                                             "url":  "https://en.macromicro.me/collections/19/mm-oil-price/4376/crude-oil-cracking-spread-vs-wti",
                                             "description":  "来源：商品总览",
                                             "domain":  "en.macromicro.me",
                                             "tags":  [
                                                          "金属",
                                                          "商品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-www-1qh-cn-1",
                                             "name":  "期货套利分析_跨期价差查询",
                                             "url":  "https://www.1qh.cn/tools/spread.html",
                                             "description":  "来源：商品总览",
                                             "domain":  "www.1qh.cn",
                                             "tags":  [
                                                          "金属",
                                                          "商品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-business-ucdenver-edu-1",
                                             "name":  "摩根大通商品与能源管理中心",
                                             "url":  "https://business.ucdenver.edu/jpmorgancenter",
                                             "description":  "来源：商品总览",
                                             "domain":  "business.ucdenver.edu",
                                             "tags":  [
                                                          "金属",
                                                          "商品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-ent-htfc-com-1",
                                             "name":  "工作台-华泰天玑",
                                             "url":  "https://ent.htfc.com/#/homePage/index?reportId\u0026catalogId",
                                             "description":  "来源：商品总览",
                                             "domain":  "ent.htfc.com",
                                             "tags":  [
                                                          "金属",
                                                          "商品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "metal-hq-smm-cn-1",
                                             "name":  "有色金属期货进口盈亏率_上海有色网",
                                             "url":  "https://hq.smm.cn/data/arbi",
                                             "description":  "来源：商品总览",
                                             "domain":  "hq.smm.cn",
                                             "tags":  [
                                                          "金属",
                                                          "商品总览"
                                                      ]
                                         }
                                     ]
                       }
                   ]
    },
    {
        "id":  "general",
        "title":  "综合工具",
        "description":  "新闻、衍生品、跨市场辅助工具与综合观察。",
        "groups":  [
                       {
                           "id":  "general-交易新闻和高手跟踪类总览",
                           "title":  "交易新闻和高手跟踪类总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027交易新闻和高手跟踪类总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "general-xnews-jin10-com-1",
                                             "name":  "金十数据-我的订阅",
                                             "url":  "https://xnews.jin10.com/topic/group/my",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "xnews.jin10.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-polymarket-com-1",
                                             "name":  "Polymarket | The World\u0027s Largest Prediction Market",
                                             "url":  "https://polymarket.com/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "polymarket.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-app-hedgeye-com-1",
                                             "name":  "很杂的分析",
                                             "url":  "https://app.hedgeye.com/?",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "app.hedgeye.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-x-com-1",
                                             "name":  "(28) Home / X",
                                             "url":  "https://x.com/home",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "x.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-wallstreetcn-com-1",
                                             "name":  "华尔街见闻",
                                             "url":  "https://wallstreetcn.com/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "wallstreetcn.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-financialjuice-com-1",
                                             "name":  "FinancialJuice适合看实时的",
                                             "url":  "https://www.financialjuice.com/home",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.financialjuice.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-cointelegraph-com-1",
                                             "name":  "Cointelegraph 杂志的加密货币深度探索",
                                             "url":  "https://cointelegraph.com/magazine/features/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "cointelegraph.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-foresightnews-pro-1",
                                             "name":  "Foresight News",
                                             "url":  "https://foresightnews.pro/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "foresightnews.pro",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-jinse-cn-1",
                                             "name":  "金色财经",
                                             "url":  "https://www.jinse.cn/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.jinse.cn",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-panewslab-com-1",
                                             "name":  "PANews",
                                             "url":  "https://www.panewslab.com/zh",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.panewslab.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-techflowpost-com-1",
                                             "name":  "深潮TechFlow",
                                             "url":  "https://www.techflowpost.com/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.techflowpost.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-coindesk-com-1",
                                             "name":  "CoinDesk",
                                             "url":  "https://www.coindesk.com/?_gl=1*v3vlyj*_up*MQ..*_ga*MTA4MTg5NzY1LjE3MjA2MTQ0Nzg.*_ga_VM3STRYVN8*MTcyMjMwNTY2OS4xMC4xLjE3MjIzMDcyMDQuMC4wLjU3MTY4MDIyNg..",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.coindesk.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-odaily-news-1",
                                             "name":  "Odaily星球日报",
                                             "url":  "https://www.odaily.news/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.odaily.news",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-coinpedia-org-1",
                                             "name":  "Coinpedia",
                                             "url":  "https://coinpedia.org/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "coinpedia.org",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-theblock-co-1",
                                             "name":  "the block",
                                             "url":  "https://www.theblock.co/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.theblock.co",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-m-weibo-cn-1",
                                             "name":  "柳大波浪",
                                             "url":  "https://m.weibo.cn/u/1644724561?wm=3333_2001\u0026from=10F1293010\u0026sourcetype=weixin\u0026s_trans=7101261740_\u0026s_channel=4",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "m.weibo.cn",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-flowus-cn-1",
                                             "name":  "Web3区别地",
                                             "url":  "https://flowus.cn/qubiedi/share/8827172d-31de-4486-8571-f1172cbe7fdd?code=UMMDMR",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "flowus.cn",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-investing-com-1",
                                             "name":  "Investing.com",
                                             "url":  "https://www.investing.com/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.investing.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-reuters-com-1",
                                             "name":  "路透社",
                                             "url":  "https://www.reuters.com/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.reuters.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-marketwatch-com-1",
                                             "name":  "MarketWatch：股市新闻",
                                             "url":  "https://www.marketwatch.com/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.marketwatch.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-forbes-com-1",
                                             "name":  "《福布斯》",
                                             "url":  "https://www.forbes.com/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.forbes.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-hibor-com-cn-1",
                                             "name":  "慧博投研资讯",
                                             "url":  "https://www.hibor.com.cn/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.hibor.com.cn",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-worldmonitor-app-1",
                                             "name":  "世界监测 - 实时全球情报仪表盘",
                                             "url":  "https://worldmonitor.app/?lat=8.0000\u0026lon=0.0000\u0026zoom=1.00\u0026view=global\u0026timeRange=7d\u0026layers=conflicts%2Cbases%2Chotspots%2Cnuclear%2Csanctions%2Cweather%2Ceconomic%2Cwaterways%2Coutages%2Cmilitary%2Cnatural",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "worldmonitor.app",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-pizzint-watch-1",
                                             "name":  "Polyglobe - 实时地缘政治市场情报 | PizzINT",
                                             "url":  "https://www.pizzint.watch/polyglobe",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.pizzint.watch",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-reuters-com-2",
                                             "name":  "全球市场头条 |  路透社",
                                             "url":  "https://www.reuters.com/markets/",
                                             "description":  "来源：交易新闻和高手跟踪类总览",
                                             "domain":  "www.reuters.com",
                                             "tags":  [
                                                          "综合",
                                                          "交易新闻和高手跟踪类总览"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "general-其他总览",
                           "title":  "其他总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027其他总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "general-fintel-io-1",
                                             "name":  "IBIT-监管信息披露平台",
                                             "url":  "https://fintel.io/so/us/ibit",
                                             "description":  "来源：其他总览",
                                             "domain":  "fintel.io",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-ycharts-com-1",
                                             "name":  "GBTC 折价或溢价至 NAV 分析",
                                             "url":  "https://ycharts.com/stocks",
                                             "description":  "来源：其他总览",
                                             "domain":  "ycharts.com",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-sec-gov-1",
                                             "name":  "SEC13F季度持仓",
                                             "url":  "https://www.sec.gov/edgar/search/",
                                             "description":  "来源：其他总览",
                                             "domain":  "www.sec.gov",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-sec-gov-2",
                                             "name":  "SEC FORM 13-F",
                                             "url":  "https://www.sec.gov/Archives/edgar/data/1166588/000116658824000009/xslForm13F_X02/PBI13f03312024.xml",
                                             "description":  "来源：其他总览",
                                             "domain":  "www.sec.gov",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-cmegroup-com-1",
                                             "name":  "CME",
                                             "url":  "https://www.cmegroup.com/tools-information/quikstrike/vol2vol-expected-range.html",
                                             "description":  "来源：其他总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-cmegroup-com-2",
                                             "name":  "投资者持仓报告用户指南",
                                             "url":  "https://www.cmegroup.com/cn-s/tools-information/quikstrike/quikstrike-cftc-commitment-of-traders-report-user-guide.html",
                                             "description":  "来源：其他总览",
                                             "domain":  "www.cmegroup.com",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-cftc-gov-1",
                                             "name":  "交易员持仓承诺",
                                             "url":  "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
                                             "description":  "来源：其他总览",
                                             "domain":  "www.cftc.gov",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-spotgamma-com-1",
                                             "name":  "期权深度分析--SpotGamma",
                                             "url":  "https://spotgamma.com/",
                                             "description":  "来源：其他总览",
                                             "domain":  "spotgamma.com",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-p-pandaremit-com-1",
                                             "name":  "熊猫速汇",
                                             "url":  "https://p.pandaremit.com/h5activity/launchInvitationCode?countryCode=HKG\u0026shareCode=MTE1NTQ4OTE%3D\u0026lang=zh-hans",
                                             "description":  "来源：其他总览",
                                             "domain":  "p.pandaremit.com",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-cftc-gov-2",
                                             "name":  "交易者承诺 | CFTC",
                                             "url":  "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm?utm_source=chatgpt.com",
                                             "description":  "来源：其他总览",
                                             "domain":  "www.cftc.gov",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-chartexchange-com-1",
                                             "name":  "CFEGF股票价格及图表",
                                             "url":  "https://chartexchange.com/symbol/otc-cfegf/",
                                             "description":  "来源：其他总览",
                                             "domain":  "chartexchange.com",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-tradingster-com-1",
                                             "name":  "COT报告：美元指数COT图表",
                                             "url":  "https://www.tradingster.com/cot/futures/fin/098662",
                                             "description":  "来源：其他总览",
                                             "domain":  "www.tradingster.com",
                                             "tags":  [
                                                          "综合",
                                                          "其他总览"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "general-衍生品总览",
                           "title":  "衍生品总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027衍生品总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "general-www-openvlab-cn-1",
                                             "name":  "OpenVlab分析平台",
                                             "url":  "https://www.openvlab.cn/",
                                             "description":  "来源：衍生品总览",
                                             "domain":  "www.openvlab.cn",
                                             "tags":  [
                                                          "综合",
                                                          "衍生品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-cboe-com-1",
                                             "name":  "芝加哥期权交易所全球市场",
                                             "url":  "https://www.cboe.com/",
                                             "description":  "来源：衍生品总览",
                                             "domain":  "www.cboe.com",
                                             "tags":  [
                                                          "综合",
                                                          "衍生品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-bybit-com-1",
                                             "name":  "期权计算器",
                                             "url":  "https://www.bybit.com/trade/option/usdt/pb/BTC",
                                             "description":  "来源：衍生品总览",
                                             "domain":  "www.bybit.com",
                                             "tags":  [
                                                          "综合",
                                                          "衍生品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-www-theblock-co-2",
                                             "name":  "加密期权未平仓合约、成交量和隐含波动率图表",
                                             "url":  "https://www.theblock.co/data/crypto-markets/options",
                                             "description":  "来源：衍生品总览",
                                             "domain":  "www.theblock.co",
                                             "tags":  [
                                                          "综合",
                                                          "衍生品总览"
                                                      ]
                                         },
                                         {
                                             "id":  "general-squeezemetrics-com-1",
                                             "name":  "sqzme股票数据的新视角",
                                             "url":  "https://squeezemetrics.com/monitor",
                                             "description":  "来源：衍生品总览",
                                             "domain":  "squeezemetrics.com",
                                             "tags":  [
                                                          "综合",
                                                          "衍生品总览"
                                                      ]
                                         }
                                     ]
                       }
                   ]
    },
    {
        "id":  "quant",
        "title":  "量化工具",
        "description":  "量化研究、接口、平台、回测与文章资料。",
        "groups":  [
                       {
                           "id":  "quant-量化总览",
                           "title":  "量化总览",
                           "description":  "来自你整理后的 Markdown 分组 \u0027量化总览\u0027。",
                           "tools":  [
                                         {
                                             "id":  "quant-www-wolai-com-1",
                                             "name":  "2025年8月 量化金工月度热点研报",
                                             "url":  "https://www.wolai.com/ustfinance/uyMty39PGZafSZa2YU93mQ",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.wolai.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-wolai-com-2",
                                             "name":  "量化学习路径",
                                             "url":  "https://www.wolai.com/ustfinance/uQLt7axQsJBeTdJaMiNvW9",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.wolai.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-blog-csdn-net-1",
                                             "name":  "CSDN博客",
                                             "url":  "https://blog.csdn.net/weixin_42219751/article/details/93621991",
                                             "description":  "来源：量化总览",
                                             "domain":  "blog.csdn.net",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-bigquant-com-1",
                                             "name":  "bigquant:【历史文档】策略示例-期货策略-基于协整的跨期套利 v1.0",
                                             "url":  "https://bigquant.com/wiki/doc/Tqrre7n7tb",
                                             "description":  "来源：量化总览",
                                             "domain":  "bigquant.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-joinquant-com-1",
                                             "name":  "社区 - JoinQuant",
                                             "url":  "https://www.joinquant.com/view/community/list?listType=1",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.joinquant.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-joinquant-com-2",
                                             "name":  "JoinQuant聚宽量化投研平台",
                                             "url":  "https://www.joinquant.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.joinquant.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-quantconnect-com-1",
                                             "name":  "开源算法交易平台。 - QuantConnect.com",
                                             "url":  "https://www.quantconnect.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.quantconnect.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-uqer-datayes-com-1",
                                             "name":  "优矿 - 大数据时代的量化投资 - 通联量化实验室",
                                             "url":  "https://uqer.datayes.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "uqer.datayes.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-uqer-datayes-com-2",
                                             "name":  "labs - 知识库 - 优矿",
                                             "url":  "https://uqer.datayes.com/labs/knowledge/%E4%BC%98%E7%9F%BF%E4%BA%A7%E5%93%81%E7%99%BD%E7%9A%AE%E4%B9%A6%2F%E9%87%8F%E5%8C%96%E6%8A%95%E8%B5%84%E5%8F%8A%E5%85%B6%E7%A0%94%E7%A9%B6%E6%96%B9%E6%B3%95.nb",
                                             "description":  "来源：量化总览",
                                             "domain":  "uqer.datayes.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-tushare-pro-1",
                                             "name":  "Tushare数据",
                                             "url":  "https://tushare.pro/",
                                             "description":  "来源：量化总览",
                                             "domain":  "tushare.pro",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-quantopian-github-io-1",
                                             "name":  "Alphalens — Alphalens 0.2.1+48.gad0be10 文档",
                                             "url":  "https://quantopian.github.io/alphalens/",
                                             "description":  "来源：量化总览",
                                             "domain":  "quantopian.github.io",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-gallery-pyecharts-org-1",
                                             "name":  "Document",
                                             "url":  "https://gallery.pyecharts.org/#/",
                                             "description":  "来源：量化总览",
                                             "domain":  "gallery.pyecharts.org",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-substack-com-1",
                                             "name":  "加密量化博主",
                                             "url":  "https://substack.com/@unexpectedcorrelations",
                                             "description":  "来源：量化总览",
                                             "domain":  "substack.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-ptradeapi-com-1",
                                             "name":  "Ptrade 量化交易 API接口文档",
                                             "url":  "https://ptradeapi.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "ptradeapi.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-thinktrader-net-1",
                                             "name":  "迅投-以思考的速度交易qmt-（官方）",
                                             "url":  "https://www.thinktrader.net/",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.thinktrader.net",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-docs-pandas-ai-com-1",
                                             "name":  "PandasAI简介 - PandasAI",
                                             "url":  "https://docs.pandas-ai.com/v2/intro",
                                             "description":  "来源：量化总览",
                                             "domain":  "docs.pandas-ai.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-quantpedia-com-1",
                                             "name":  "主页 - QuantPedia",
                                             "url":  "https://quantpedia.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "quantpedia.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-mp-weixin-qq-com-1",
                                             "name":  "「量化界」年度最受欢迎的10篇博客",
                                             "url":  "https://mp.weixin.qq.com/s/CYZ7tPcNYxGr3pSVkd2NSQ",
                                             "description":  "来源：量化总览",
                                             "domain":  "mp.weixin.qq.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-quantpedia-com-2",
                                             "name":  "如何利用比特币隔夜交易获利？ - QuantPedia",
                                             "url":  "https://quantpedia.com/how-to-profitably-trade-bitcoins-overnight-sessions/",
                                             "description":  "来源：量化总览",
                                             "domain":  "quantpedia.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-quantpedia-com-3",
                                             "name":  "我们应该在投资组合中分配多少比特币？ - QuantPedia",
                                             "url":  "https://quantpedia.com/how-much-bitcoin-should-we-allocate-to-the-portfolio/",
                                             "description":  "来源：量化总览",
                                             "domain":  "quantpedia.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-chartjs-org-1",
                                             "name":  "Chart.js Samples | Chart.js",
                                             "url":  "https://www.chartjs.org/docs/latest/samples/information.html",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.chartjs.org",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-pandaai-online-1",
                                             "name":  "Panda AI - 量变学院，可以agent交易",
                                             "url":  "https://www.pandaai.online/",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.pandaai.online",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-vnpy-com-1",
                                             "name":  "开源量化平台vnpy",
                                             "url":  "https://www.vnpy.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.vnpy.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-zhuanlan-zhihu-com-1",
                                             "name":  "vnpy：国内最受欢迎的开源量化交易平台深度解析 - 知乎",
                                             "url":  "https://zhuanlan.zhihu.com/p/1934373021193343584",
                                             "description":  "来源：量化总览",
                                             "domain":  "zhuanlan.zhihu.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-jupyter-org-1",
                                             "name":  "JupyterLite",
                                             "url":  "https://jupyter.org/try-jupyter/lab/",
                                             "description":  "来源：量化总览",
                                             "domain":  "jupyter.org",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-joinquant-com-3",
                                             "name":  "聚宽",
                                             "url":  "https://www.joinquant.com/view/user/floor?type=mainFloor",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.joinquant.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-backtest-10jqka-com-cn-1",
                                             "name":  "自然语言即可回测：BackTest 量化策略平台",
                                             "url":  "https://backtest.10jqka.com.cn/",
                                             "description":  "来源：量化总览",
                                             "domain":  "backtest.10jqka.com.cn",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-bigquant-com-2",
                                             "name":  "解锁 AI 量化新境界：Qbot 携手 iTick - BigQuant量化交易",
                                             "url":  "https://bigquant.com/wiki/doc/kq9FxV9GUg",
                                             "description":  "来源：量化总览",
                                             "domain":  "bigquant.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-quantstart-com-1",
                                             "name":  "量化自学：算法交易、量化交易、交易策略、回测与实施 | QuantStart",
                                             "url":  "https://www.quantstart.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.quantstart.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-blog-headlandstech-com-1",
                                             "name":  "Headlands Technologies LLC 博客",
                                             "url":  "https://blog.headlandstech.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "blog.headlandstech.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-aurora-gold-insight-pages-dev-1",
                                             "name":  "Aurora Gold Insight",
                                             "url":  "https://aurora-gold-insight.pages.dev/#knowledge",
                                             "description":  "来源：量化总览",
                                             "domain":  "aurora-gold-insight.pages.dev",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-cn-tradingview-com-1",
                                             "name":  "BTCUSD 88,957.39 ▲ +0.25% 大类资产",
                                             "url":  "https://cn.tradingview.com/chart/QlE64yj4/",
                                             "description":  "来源：量化总览",
                                             "domain":  "cn.tradingview.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-calendarific-com-1",
                                             "name":  "全球节假日日历 API，涵盖国家和宗教节日。",
                                             "url":  "https://calendarific.com/",
                                             "description":  "来源：量化总览",
                                             "domain":  "calendarific.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-fmz-com-1",
                                             "name":  "资费的参考资管平台",
                                             "url":  "https://www.fmz.com/m/dashboard",
                                             "description":  "来源：量化总览",
                                             "domain":  "www.fmz.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-gitee-com-1",
                                             "name":  "gitee",
                                             "url":  "https://gitee.com/JavaLionLi/plus-ui",
                                             "description":  "来源：量化总览",
                                             "domain":  "gitee.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化总览"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "quant-量化类好文章",
                           "title":  "量化类好文章",
                           "description":  "来自你整理后的 Markdown 分组 \u0027量化类好文章\u0027。",
                           "tools":  [
                                         {
                                             "id":  "quant-bigquant-com-3",
                                             "name":  "金工CTA系列之一：基于基本面多因子模型的黄金交易策略",
                                             "url":  "https://bigquant.com/wiki/doc/oiVYuLosvU",
                                             "description":  "来源：量化类好文章",
                                             "domain":  "bigquant.com",
                                             "tags":  [
                                                          "量化",
                                                          "量化类好文章"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-blog-csdn-net-2",
                                             "name":  "统计套利策略的五大主流策略分析与优缺点_copula函数的缺点",
                                             "url":  "https://blog.csdn.net/zk168_net/article/details/107536782",
                                             "description":  "来源：量化类好文章",
                                             "domain":  "blog.csdn.net",
                                             "tags":  [
                                                          "量化",
                                                          "量化类好文章"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-myquant-cn-1",
                                             "name":  "跨期套利(期货)",
                                             "url":  "https://www.myquant.cn/docs/python_strategyies/107",
                                             "description":  "来源：量化类好文章",
                                             "domain":  "www.myquant.cn",
                                             "tags":  [
                                                          "量化",
                                                          "量化类好文章"
                                                      ]
                                         }
                                     ]
                       },
                       {
                           "id":  "quant-接口",
                           "title":  "接口",
                           "description":  "来自你整理后的 Markdown 分组 \u0027接口\u0027。",
                           "tools":  [
                                         {
                                             "id":  "quant-tushare-pro-2",
                                             "name":  "Tushare数据",
                                             "url":  "https://tushare.pro/document/2?doc_id=284",
                                             "description":  "来源：接口",
                                             "domain":  "tushare.pro",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-alphavantage-co-1",
                                             "name":  "API Documentation | Alpha Vantage",
                                             "url":  "https://www.alphavantage.co/documentation/",
                                             "description":  "来源：接口",
                                             "domain":  "www.alphavantage.co",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-akshare-akfamily-xyz-1",
                                             "name":  "AKShare 外汇数据 — AKShare 1.17.83 文档",
                                             "url":  "https://akshare.akfamily.xyz/data/fx/fx.html",
                                             "description":  "来源：接口",
                                             "domain":  "akshare.akfamily.xyz",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-tushare-pro-3",
                                             "name":  "Tushare数据",
                                             "url":  "https://tushare.pro/document/2",
                                             "description":  "来源：接口",
                                             "domain":  "tushare.pro",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-juejinshuju-com-1",
                                             "name":  "掘金：国内期货历史数据-主连分钟K线-期货主连历史分钟数据下载",
                                             "url":  "http://www.juejinshuju.com/future_continue_min/",
                                             "description":  "来源：接口",
                                             "domain":  "www.juejinshuju.com",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-ricequant-com-1",
                                             "name":  "RQData Python API 手册 | Ricequant Docs",
                                             "url":  "https://www.ricequant.com/doc/rqdata/python/index-rqdatac",
                                             "description":  "来源：接口",
                                             "domain":  "www.ricequant.com",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-itick-org-1",
                                             "name":  "量化交易接口 - iTick",
                                             "url":  "https://itick.org/",
                                             "description":  "来源：接口",
                                             "domain":  "itick.org",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-docs-itick-org-1",
                                             "name":  "文档说明 - iTick 文档",
                                             "url":  "https://docs.itick.org/",
                                             "description":  "来源：接口",
                                             "domain":  "docs.itick.org",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-dataroma-com-1",
                                             "name":  "DATAROMA 超级投资者持股摘要",
                                             "url":  "https://www.dataroma.com/m/managers.php",
                                             "description":  "来源：接口",
                                             "domain":  "www.dataroma.com",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-doc-shinnytech-com-1",
                                             "name":  "十分钟快速入门 — TianQin Python SDK 3.8.7 文档",
                                             "url":  "https://doc.shinnytech.com/tqsdk/latest/quickstart.html#quickstart-0",
                                             "description":  "来源：接口",
                                             "domain":  "doc.shinnytech.com",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-www-ivolatility-com-1",
                                             "name":  "付费API，但很便宜",
                                             "url":  "https://www.ivolatility.com/data-cloud-api/?gad_source=1\u0026gad_campaignid=20419477335\u0026gbraid=0AAAAADyngPXx6BuAUQUg015xdcmQ1rc_M\u0026gclid=CjwKCAiAssfLBhBDEiwAcLpwfulC_7LbiHzzBFUPw60W144ByHitONsLKbUJQo9B58SCDD_1ktS0NhoCyUsQAvD_BwE",
                                             "description":  "来源：接口",
                                             "domain":  "www.ivolatility.com",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         },
                                         {
                                             "id":  "quant-alltick-co-1",
                                             "name":  "API- AllTick",
                                             "url":  "https://alltick.co/#pricing",
                                             "description":  "来源：接口",
                                             "domain":  "alltick.co",
                                             "tags":  [
                                                          "量化",
                                                          "接口"
                                                      ]
                                         }
                                     ]
                       }
                   ]
    }
];

export const tradingToolCategoryMap = tradingToolCategories.reduce(
  (map, category) => {
    map[category.id as TradingToolCategoryId] = category;
    return map;
  },
  {} as Record<TradingToolCategoryId, TradingToolCategory>,
);
