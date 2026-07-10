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
  title: "\u4ea4\u6613\u5de5\u5177",
  eyebrow: "Bookmark Library",
  summary: "\u57fa\u4e8e\u4f60\u672c\u673a Chrome \u4e66\u7b7e\u81ea\u52a8\u6574\u7406\u7684\u5de5\u5177\u5e93\uff0c\u5df2\u6309\u5b8f\u89c2\u3001\u80a1\u5e02\u3001\u52a0\u5bc6\u3001\u91d1\u5c5e\u3001\u91cf\u5316\u7b49\u6846\u67b6\u91cd\u7ec4\u3002",
} as const;

export const tradingToolCategories: TradingToolCategory[] = [
        {
      "id": "macro",
      "title": "\u5b8f\u89c2\u5de5\u5177",
      "description": "\u5229\u7387\u3001\u6d41\u52a8\u6027\u3001\u503a\u5238\u3001\u7ecf\u6d4e\u6570\u636e\u4e0e\u8de8\u533a\u57df\u5b8f\u89c2\u8ddf\u8e2a\u3002",
      "groups": [
          {
              "id": "macro-\u5b8f\u89c2\u603b\u89c8",
              "title": "\u5b8f\u89c2\u603b\u89c8",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u5b8f\u89c2\u603b\u89c8\u201d\u3002",
              "tools": [
                  {
                      "id": "macro-tradingeconomics-com-1",
                      "name": "\u7ecf\u6d4e\u65e5\u5386tradingeconomics",
                      "url": "https://tradingeconomics.com/calendar",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "tradingeconomics.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-www-jin10-com-1",
                      "name": "\u91d1\u5341\u6570\u636e \u5b98\u65b9\u7f51\u7ad9 - \u4e00\u4e2a\u4ea4\u6613\u5de5\u5177\uff01",
                      "url": "https://www.jin10.com/",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "www.jin10.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-thedailyshot-com-1",
                      "name": "\u6bcf\u65e5\u5b8f\u89c2\u7b80\u8baf",
                      "url": "https://thedailyshot.com/",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "thedailyshot.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-www-cmegroup-com-1",
                      "name": "CME \u7f8e\u8054\u50a8\u8def\u5f84 - \u829d\u5546\u6240",
                      "url": "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "www.cmegroup.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-datacenter-jin10-com-1",
                      "name": "\u91d1\u5341\u6570\u636e\u4e2d\u5fc3",
                      "url": "https://datacenter.jin10.com/",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "datacenter.jin10.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-en-macromicro-me-1",
                      "name": "macromicro\u5b8f\u89c2\u6570\u636e\u65e5\u62a5",
                      "url": "https://en.macromicro.me/quickie",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-x-qhkch-com-1",
                      "name": "\u7ecf\u6d4e\u6570\u636e - \u5947\u8d27\u53ef\u67e5",
                      "url": "https://x.qhkch.com/fundamental/nationGdpMetrics?country=%E7%BE%8E%E5%9B%BD",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "x.qhkch.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-macro-ops-com-1",
                      "name": "\u5b8f\u89c2\u4ea4\u6613\u7b56\u7565",
                      "url": "https://macro-ops.com/",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "macro-ops.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-robo-datayes-com-1",
                      "name": "\u5b8f\u89c2\u7ecf\u6d4e+\u80a1\u5e02 \u841d\u535c\u6295\u7814",
                      "url": "https://robo.datayes.com/v2/landing/macrogrp",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "robo.datayes.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-tradingeconomics-com-2",
                      "name": "\u5404\u56fd\u5b8f\u89c2\u7ecf\u6d4e\u6307\u6807 | \u6309\u7c7b\u522b\u5217\u51fa",
                      "url": "https://tradingeconomics.com/indicators",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "tradingeconomics.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-www-haver-com-1",
                      "name": "Haver\u5b8f\u89c2\u8bc4\u8bba",
                      "url": "https://www.haver.com/",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "www.haver.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-www-forexfactory-com-1",
                      "name": "\u65e5\u5386 | AI\u597d\u8bfb\u53d6",
                      "url": "https://www.forexfactory.com/calendar?day=jan3.2026",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "www.forexfactory.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-truflation-com-1",
                      "name": "\u5176\u4ed6\u5b8f\u89c2\u6570\u636e\u56fe\u8868\u5e93",
                      "url": "https://truflation.com/marketplace?auth=google&code=e2e58bd7-c221-4d97-9997-ad2d612810a2&isSigningUp=true&period=annual&stake=false&tier=undefined",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "truflation.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-www-notion-so-1",
                      "name": "\u5b8f\u89c2\u8fb9\u9645MacroMargin",
                      "url": "https://www.notion.so/trusting-glitter-4f0/MacroMargin-27e6782525ab41e188cb81510803d95b",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "www.notion.so",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-wx-zsxq-com-1",
                      "name": "\u77e5\u8bc6\u661f\u7403",
                      "url": "https://wx.zsxq.com/login",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "wx.zsxq.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "macro-www-vaneck-com-1",
                      "name": "VanEck \u5206\u6790",
                      "url": "https://www.vaneck.com/asia/en/insights/",
                      "description": "\u6765\u6e90: \u5b8f\u89c2\u603b\u89c8",
                      "domain": "www.vaneck.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5b8f\u89c2\u603b\u89c8"
                      ]
                  }
              ]
          },
          {
              "id": "macro-\u7f8e\u8054\u50a8-\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
              "title": "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e\u201d\u3002",
              "tools": [
                  {
                      "id": "macro-www-newyorkfed-org-1",
                      "name": "Repo Operations - FEDERAL RESERVE BANK of NEW YORK",
                      "url": "https://www.newyorkfed.org/markets/desk-operations/repo",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.newyorkfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-sc-macromicro-me-1",
                      "name": "\u57fa\u51c6\u5229\u7387&\u7f8e\u8054\u50a8\u8d44\u4ea7\u8d1f\u503a\u8868\u89c4\u6a21vs.\u9ec4\u91d1 | \u9ec4\u91d1 | \u56fe\u7ec4 | MacroMicro \u8d22\u7ecfM\u5e73\u65b9",
                      "url": "https://sc.macromicro.me/collections/45/mm-gold-price/24057/us-fed-funds-rate-and-total-assets-vs-gold-price",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "sc.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-1",
                      "name": "\u4fe1\u7528\u5229\u5dee",
                      "url": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-federalreserve-gov-1",
                      "name": "\u7f8e\u8054\u50a8\u8d44\u4ea7\u8d1f\u503a\u8868",
                      "url": "https://www.federalreserve.gov/releases/h41/",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.federalreserve.gov",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-federalreserve-gov-2",
                      "name": "\u7f8e\u8054\u50a8 - \u4f1a\u8bae\u65e5\u7a0b\u548c\u4fe1\u606f",
                      "url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.federalreserve.gov",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-federalreserve-gov-3",
                      "name": "FOMC\u4f1a\u8bae\u58f0\u660e/\u8bb0\u8005\u4f1a",
                      "url": "https://www.federalreserve.gov/videos.htm",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.federalreserve.gov",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-sc-macromicro-me-2",
                      "name": "\u7f8e\u56fd-\u7f8e\u8054\u50a8\u8d1f\u503a\u7aef\u7ed3\u6784 | \u7f8e\u56fd-\u7f8e\u8054\u50a8 | \u56fe\u7ec4 | MacroMicro \u8d22\u7ecfM\u5e73\u65b9",
                      "url": "https://sc.macromicro.me/collections/4238/us-federal/1320/us-fed-liabilities-structure",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "sc.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-2",
                      "name": "\u62c5\u4fdd\u9694\u591c\u878d\u8d44\u5229\u7387 (SOFR) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/SOFR",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-3",
                      "name": "10\u5e74\u671f\u76c8\u4e8f\u5e73\u8861\u901a\u80c0\u7387 (T10YIE) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/T10YIE",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-4",
                      "name": "10\u5e74\u671f\u56fa\u5b9a\u671f\u9650\u7f8e\u56fd\u56fd\u503a\u5e02\u573a\u6536\u76ca\u7387\uff0c\u4ee5\u6295\u8d44\u4e3a\u57fa\u7840\u62a5\u4ef7\uff0c\u901a\u80c0\u4fdd\u503c (DFII10) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/DFII10",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-en-macromicro-me-2",
                      "name": "\u5404\u56fd\u592e\u884c\u5229\u7387",
                      "url": "https://en.macromicro.me/central_bank/overview",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-en-macromicro-me-3",
                      "name": "\u5404\u56fd\u592e\u884c\u52a0\u606f/\u964d\u606f\u9884\u671f\uff082024\u5e74\uff09| MacroMicro",
                      "url": "https://en.macromicro.me/charts/89119/cbs-interest-rate-cuts-expectation-2024",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-5",
                      "name": "\u5229\u5dee/\u6807\u666e\u76f8\u5173\u6027",
                      "url": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2#0",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-newyorkfed-org-2",
                      "name": "\u7ebd\u7ea6\u8054\u90a6\u50a8\u5907\u94f6\u884c\u2014\u2014\u670d\u52a1\u4e8e\u7b2c\u4e8c\u533a\u53ca\u5168\u7f8e\u2014\u2014\u7ebd\u7ea6\u8054\u90a6\u50a8\u5907\u94f6\u884c",
                      "url": "https://www.newyorkfed.org/",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.newyorkfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fraser-stlouisfed-org-1",
                      "name": "\u7f8e\u8054\u50a8\u5386\u53f2",
                      "url": "https://fraser.stlouisfed.org/",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fraser.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-newyorkfed-org-3",
                      "name": "\u54a8\u8be2\u5c0f\u7ec4 - \u7ebd\u7ea6\u8054\u90a6\u50a8\u5907\u94f6\u884c",
                      "url": "https://www.newyorkfed.org/aboutthefed/external_committees",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.newyorkfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-home-treasury-gov-1",
                      "name": "U.S. Department of the Treasury",
                      "url": "https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/most-recent-quarterly-refunding-documents,",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "home.treasury.gov",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-6",
                      "name": "\u7f8e\u8054\u50a8\u7ecf\u6d4e\u6570\u636e | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-atlantafed-org-1",
                      "name": "GDPNow - \u4e9a\u7279\u5170\u5927\u8054\u90a6\u50a8\u5907\u94f6\u884c",
                      "url": "https://www.atlantafed.org/cqer/research/gdpnow",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.atlantafed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-atlantafed-org-2",
                      "name": "\u4e9a\u7279\u5170\u5927\u5de5\u8d44\u589e\u957f\u8ffd\u8e2a",
                      "url": "https://www.atlantafed.org/chcs/wage-growth-tracker",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.atlantafed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-7",
                      "name": "\u6838\u5fc3PCE",
                      "url": "https://fred.stlouisfed.org/series/DPCCRV1Q225SBEA",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-macromicro-me-1",
                      "name": "\u7f8e\u56fdPCE\uff06corePCE(\u5e74\u589e\u7387) | MacroMicro \u8d22\u7ecfM\u5e73\u65b9",
                      "url": "https://www.macromicro.me/charts/107685/mei-guo-PCE-corePCE-nian-zeng-lyu",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-clevelandfed-org-1",
                      "name": "10\u5e74\u671f\u901a\u80c0\u9884\u671f\u548c\u98ce\u9669\u6ea2\u4ef7",
                      "url": "https://www.clevelandfed.org/indicators-and-data/inflation-expectations",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.clevelandfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-newyorkfed-org-4",
                      "name": "1/3/5\u6d88\u8d39\u8005\u901a\u80c0\u9884\u671f",
                      "url": "https://www.newyorkfed.org/microeconomics/sce#/inflexp-1",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.newyorkfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-clevelandfed-org-2",
                      "name": "PCE\u9884\u6d4b",
                      "url": "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.clevelandfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-item-1",
                      "name": "\u7f8e\u56fd-\u6d88\u8d39\u8005\u7269\u4ef7\u7ec6\u9879[CPI",
                      "url": "\u73af\u6bd4",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-8",
                      "name": "10\u5e74\u671f\u56fd\u503a-2\u5e74\u671f\u56fd\u503a\u56fa\u5b9a\u5230\u671f\u65e5\uff08T10Y2Y\uff09| FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/T10Y2Y",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-9",
                      "name": "\u804c\u4f4d\u7a7a\u7f3a\uff1a\u975e\u519c\u5c31\u4e1a\u6570\u636e (JTSJOL) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/JTSJOL",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-en-macromicro-me-4",
                      "name": "\u7f8e\u56fd - ADP \u975e\u519c\u5c31\u4e1a\u6570\u636e | \u7f8e\u56fd\u5c31\u4e1a\u6570\u636e | \u6570\u636e\u6536\u96c6 | MacroMicro",
                      "url": "https://en.macromicro.me/collections/4/us-employ-relative/36/adp",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-en-macromicro-me-5",
                      "name": "\u7f8e\u56fd\u52b3\u52a8\u529b\u5e02\u573a",
                      "url": "https://en.macromicro.me/collections/4/us-employ-relative/87/jolts",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-10",
                      "name": "\u52b3\u52a8\u529b\u53c2\u4e0e\u7387 (CIVPART) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/CIVPART",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-11",
                      "name": "\u4e2a\u4eba\u50a8\u84c4\u7387 (PSAVERT) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/PSAVERT",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-12",
                      "name": "\u4fe1\u7528\u5361\u8d37\u6b3e\u62d6\u6b20\u7387 (DRCCLACBS) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/DRCCLACBS",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-13",
                      "name": "\u7f8e\u56fd 30 \u5e74\u671f\u56fa\u5b9a\u5229\u7387\u62b5\u62bc\u8d37\u6b3e\u5e73\u5747\u503c (MORTGAGE30US) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/MORTGAGE30US",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-en-macromicro-me-6",
                      "name": "\u7f8e\u56fd\u2014\u2014\u94f6\u884c\u6536\u7d27\u5546\u4e1a\u548c\u5de5\u4e1a\u8d37\u6b3e\u6807\u51c6\u7684\u51c0\u767e\u5206\u6bd4 | MacroMicro",
                      "url": "https://en.macromicro.me/charts/1241/us-bank-net-percent-tight-loan",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  },
                  {
                      "id": "macro-www-redfin-com-1",
                      "name": "\u7f8e\u56fd\u623f\u5730\u4ea7\u5e02\u573a\u548c\u4ef7\u683c | Redfin",
                      "url": "https://www.redfin.com/us-housing-market",
                      "description": "\u6765\u6e90: \u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e",
                      "domain": "www.redfin.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u8054\u50a8\u3001\u7f8e\u56fd\u7ecf\u6d4e\u6570\u636e"
                      ]
                  }
              ]
          },
          {
              "id": "macro-\u7f8e\u503a\u7c7b",
              "title": "\u7f8e\u503a\u7c7b",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u7f8e\u503a\u7c7b\u201d\u3002",
              "tools": [
                  {
                      "id": "macro-treasurydirect-gov-1",
                      "name": "\u7f8e\u503a\u62cd\u5356\u65f6\u95f4",
                      "url": "https://treasurydirect.gov/auctions/upcoming/",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "treasurydirect.gov",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  },
                  {
                      "id": "macro-www-treasurydirect-gov-1",
                      "name": "\u56fd\u503a\u62cd\u5356",
                      "url": "https://www.treasurydirect.gov/auctions/announcements-data-results/announcement-results-press-releases/",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "www.treasurydirect.gov",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  },
                  {
                      "id": "macro-www-usdebtclock-org-1",
                      "name": "\u7f8e\u56fd\u503a\u52a1\u65f6\u949f",
                      "url": "https://www.usdebtclock.org/",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "www.usdebtclock.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  },
                  {
                      "id": "macro-ticdata-treasury-gov-1",
                      "name": "\u5404\u56fd\u7f8e\u503a\u6301\u6709\u4ed3\u4f4d\u5360\u6bd4",
                      "url": "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.html",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "ticdata.treasury.gov",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  },
                  {
                      "id": "macro-en-macromicro-me-7",
                      "name": "10\u5e74\u671f\u56fd\u503a\u4e70\u5356\u6bd4 | \u7f8e\u56fd\u56fd\u503a | \u6536\u85cf | MacroMicro",
                      "url": "https://en.macromicro.me/collections/51/us-treasury-bond/30431/us-10y-bid-to-cover-ratio",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  },
                  {
                      "id": "macro-sc-macromicro-me-3",
                      "name": "\u7f8e\u56fd-\u8d22\u653f\u90e8\u6bcf\u6708\u503a\u5238\u53d1\u884c\u91cf | MacroMicro \u8d22\u7ecfM\u5e73\u65b9",
                      "url": "https://sc.macromicro.me/charts/4458/us-treasury-issuance-gross",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "sc.macromicro.me",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  },
                  {
                      "id": "macro-fred-stlouisfed-org-14",
                      "name": "\u7f8e\u56fd\u503a\u52a1\u5360\u56fd\u5185\u751f\u4ea7\u603b\u503c\u7684\u767e\u5206\u6bd4 (GFDEGDQ188S) | FRED | \u5723\u8def\u6613\u65af\u8054\u50a8",
                      "url": "https://fred.stlouisfed.org/series/GFDEGDQ188S",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "fred.stlouisfed.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  },
                  {
                      "id": "macro-www-pgpf-org-1",
                      "name": "\u56fd\u5bb6\u503a\u52a1\u65f6\u949f\uff1a\u73b0\u5728\u7684\u56fd\u5bb6\u503a\u52a1\u662f\u591a\u5c11\uff1f",
                      "url": "https://www.pgpf.org/national-debt-clock/",
                      "description": "\u6765\u6e90: \u7f8e\u503a\u7c7b",
                      "domain": "www.pgpf.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u7f8e\u503a\u7c7b"
                      ]
                  }
              ]
          },
          {
              "id": "macro-\u5176\u4ed6",
              "title": "\u5176\u4ed6",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u5176\u4ed6\u201d\u3002",
              "tools": [
                  {
                      "id": "macro-www-ici-org-1",
                      "name": "\u673a\u6784\u73b0\u91d1\u4ed3\u4f4d",
                      "url": "https://www.ici.org/research/stats/mmf",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "www.ici.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  },
                  {
                      "id": "macro-data-worldbank-org-1",
                      "name": "\u4e16\u754c\u94f6\u884c\u5f00\u653e\u6570\u636e | \u5404\u56fd\u957f\u671f\u7ecf\u6d4e\u6570\u636e\u5bf9\u6bd4",
                      "url": "https://data.worldbank.org/",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "data.worldbank.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  },
                  {
                      "id": "macro-worldpopulationreview-com-1",
                      "name": "\u5404\u56fd\u503a\u52a1/GDP\u5360\u6bd4",
                      "url": "https://worldpopulationreview.com/country-rankings/countries-by-national-debt",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "worldpopulationreview.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  },
                  {
                      "id": "macro-population-pyramid-net-1",
                      "name": "\u4e16\u754c\u5404\u56fd\u7684\u4eba\u53e3\u91d1\u5b57\u5854 2025 - \u4eba\u53e3\u91d1\u5b57\u5854",
                      "url": "https://population-pyramid.net/zh-cn",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "population-pyramid.net",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  },
                  {
                      "id": "macro-tradingeconomics-com-3",
                      "name": "\u5168\u7403\u6570\u636e",
                      "url": "https://tradingeconomics.com/",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "tradingeconomics.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  },
                  {
                      "id": "macro-www-imf-org-1",
                      "name": "IMF\u5168\u7403\u91d1\u878d/\u5916\u6c47/\u503a\u52a1\u6307\u6807\u6570\u636e\u5e93",
                      "url": "https://www.imf.org/en/Data",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "www.imf.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  },
                  {
                      "id": "macro-news-usni-org-1",
                      "name": "\u7f8e\u56fd\u822a\u6bcd\u52a8\u6001\uff1aUSNI News Fleet and Marine Tracker: June 9, 2025",
                      "url": "https://news.usni.org/2025/06/09/usni-news-fleet-and-marine-tracker-june-9-2025",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "news.usni.org",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  },
                  {
                      "id": "macro-www-flightradar24-com-1",
                      "name": "\u5404\u56fd\u9886\u7a7a\u60c5\u51b5\uff1aFlightradar24: Live Flight Tracker - Real-Time Flight Tracker Map",
                      "url": "https://www.flightradar24.com/30.37,52.68/5",
                      "description": "\u6765\u6e90: \u5176\u4ed6",
                      "domain": "www.flightradar24.com",
                      "tags": [
                          "\u5b8f\u89c2",
                          "\u5176\u4ed6"
                      ]
                  }
              ]
          }
      ]
  },
      {
      "id": "equity",
      "title": "\u80a1\u5e02\u5de5\u5177",
      "description": "\u4e2a\u80a1\u3001ETF\u3001\u884d\u751f\u54c1\u3001\u6301\u4ed3\u8ffd\u8e2a\u4e0e\u5e02\u573a\u60c5\u7eea\u5de5\u5177\u3002",
      "groups": [
          {
              "id": "equity-\u80a1\u5e02\u603b\u89c8",
              "title": "\u80a1\u5e02\u603b\u89c8",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u80a1\u5e02\u603b\u89c8\u201d\u3002",
              "tools": [
                  {
                      "id": "equity-pro-openbb-co-1",
                      "name": "OpenBB \u5de5\u4f5c\u533a",
                      "url": "https://pro.openbb.co/app/ad4c0196-5796-4114-bcec-cf6dc21f914d",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "pro.openbb.co",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-companiesmarketcap-com-1",
                      "name": "\u7f8e\u56fd\u516c\u53f8\u5e02\u503c\u6392\u540d",
                      "url": "https://companiesmarketcap.com/usa/largest-companies-in-the-usa-by-market-cap/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "companiesmarketcap.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-dapanyuntu-com-1",
                      "name": "A\u80a1\u677f\u5757\u8d70\u52bf",
                      "url": "https://dapanyuntu.com/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "dapanyuntu.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-finviz-com-1",
                      "name": "\u80a1\u7968\u7b5b\u9009\u5668\u548c\u70ed\u529b\u56fe--FINVIZ.com",
                      "url": "https://finviz.com/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "finviz.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-finviz-com-2",
                      "name": "finviz\u8d22\u62a5\u53ef\u89c6\u5316",
                      "url": "https://finviz.com/quote.ashx?t=AAPL&ty=ea&p=d&b=1",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "finviz.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-en-macromicro-me-1",
                      "name": "\u7f8e\u80a1\u5e02\u573a\u60c5\u7eea\u6307\u6570 | MacroMicro",
                      "url": "https://en.macromicro.me/charts/80778/US-CNN-Fear-and-Greed-Index",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "en.macromicro.me",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-tickernerd-com-1",
                      "name": "Ticker Nerd \u80a1\u7968\u6587\u4ef6\u67e5\u627e",
                      "url": "https://tickernerd.com/resources/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "tickernerd.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-sec-gov-1",
                      "name": "SEC\u8d22\u62a5",
                      "url": "https://www.sec.gov/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "www.sec.gov",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-insight-factset-com-1",
                      "name": "\u6bcf\u5b63\u5ea6\u8d22\u62a5\u7edf\u8ba1\u53caforward EPS/PE",
                      "url": "https://insight.factset.com/topic/earnings",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "insight.factset.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-whalewisdom-com-1",
                      "name": "\u5229\u752813F\u6587\u4ef6\u548c\u9cb8\u9c7c\u6570\u636e\u8ffd\u8e2a\u5bf9\u51b2\u57fa\u91d1\u6295\u8d44\u7ec4\u5408",
                      "url": "https://whalewisdom.com/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "whalewisdom.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-seekingalpha-com-1",
                      "name": "Seeking Alpha | \u80a1\u5e02\u5206\u6790\u53ca\u6295\u8d44\u8005\u5de5\u5177",
                      "url": "https://seekingalpha.com/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "seekingalpha.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-lixinger-com-1",
                      "name": "\u793e\u4fdd\u673a\u6784\u6301\u4ed3",
                      "url": "https://www.lixinger.com/analytics/shareholders/search",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "www.lixinger.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-ark-alien-tomato-com-1",
                      "name": "Ark\u57fa\u91d1\u6700\u65b0\u52a8\u5411",
                      "url": "https://ark.alien-tomato.com/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "ark.alien-tomato.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-perplexity-ai-1",
                      "name": "\u7f8e\u56fd\u8bae\u5458\u6295\u8d44\u7ec4\u5408",
                      "url": "https://www.perplexity.ai/finance/politicians",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "www.perplexity.ai",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-cninfo-com-cn-1",
                      "name": "A\u80a1\u5de8\u6f6e\u8d44\u8baf\u7f51",
                      "url": "https://www.cninfo.com.cn/new/index.jsp",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "www.cninfo.com.cn",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-robo-datayes-com-1",
                      "name": "\u841d\u535c\u6295\u7814-\u667a\u80fd\u80a1\u7968\u6295\u7814|\u9009\u80a1_\u57fa\u672c\u9762\u5206\u6790|\u9009\u80a1|\u7814\u7a76|\u6295\u7814_\u770b\u7814\u62a5",
                      "url": "https://robo.datayes.com/",
                      "description": "\u6765\u6e90: \u80a1\u5e02\u603b\u89c8",
                      "domain": "robo.datayes.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "\u80a1\u5e02\u603b\u89c8"
                      ]
                  }
              ]
          },
          {
              "id": "equity-etf\u603b\u89c8",
              "title": "ETF\u603b\u89c8",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201cETF\u603b\u89c8\u201d\u3002",
              "tools": [
                  {
                      "id": "equity-www-etf-com-1",
                      "name": "ETF \u6bd4\u8f83\u5de5\u5177 - \u8f7b\u677e\u6bd4\u8f83\u57fa\u91d1 | etf.com",
                      "url": "https://www.etf.com/tools/etf-comparison",
                      "description": "\u6765\u6e90: ETF\u603b\u89c8",
                      "domain": "www.etf.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "ETF\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-etfrc-com-1",
                      "name": "ETF\u7814\u7a76\u4e2d\u5fc3",
                      "url": "https://www.etfrc.com/",
                      "description": "\u6765\u6e90: ETF\u603b\u89c8",
                      "domain": "www.etfrc.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "ETF\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-etfdb-com-1",
                      "name": "ETF \u6570\u636e\u5e93\uff1aETF \u539f\u521b\u7efc\u5408\u6307\u5357",
                      "url": "https://etfdb.com/",
                      "description": "\u6765\u6e90: ETF\u603b\u89c8",
                      "domain": "etfdb.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "ETF\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-etf-com-2",
                      "name": "ETF \u57fa\u91d1\u6d41\u91cf\u5de5\u5177\uff1a\u641c\u7d22\u6d41\u5165\u548c\u6d41\u51fa\u6700\u591a\u7684\u8d44\u91d1",
                      "url": "https://www.etf.com/etfanalytics/etf-fund-flows-tool",
                      "description": "\u6765\u6e90: ETF\u603b\u89c8",
                      "domain": "www.etf.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "ETF\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-lazyportfolioetf-com-1",
                      "name": "\u61d2\u60f0\u6295\u8d44\u7ec4\u5408\u548cETF\u7ec4\u5408",
                      "url": "https://www.lazyportfolioetf.com/#google_vignette",
                      "description": "\u6765\u6e90: ETF\u603b\u89c8",
                      "domain": "www.lazyportfolioetf.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "ETF\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-www-portfoliovisualizer-com-1",
                      "name": "\u6295\u8d44\u7ec4\u5408\u53ef\u89c6\u5316\u5de5\u5177",
                      "url": "https://www.portfoliovisualizer.com/",
                      "description": "\u6765\u6e90: ETF\u603b\u89c8",
                      "domain": "www.portfoliovisualizer.com",
                      "tags": [
                          "\u80a1\u5e02",
                          "ETF\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "equity-funddb-cn-1",
                      "name": "\u97ed\u5708\u513f_\u57fa\u91d1\u914d\u7f6e\u9ad8\u624b\u805a\u96c6\u5730",
                      "url": "https://funddb.cn/",
                      "description": "\u6765\u6e90: ETF\u603b\u89c8",
                      "domain": "funddb.cn",
                      "tags": [
                          "\u80a1\u5e02",
                          "ETF\u603b\u89c8"
                      ]
                  }
              ]
          }
      ]
  },
  {
    "id": "crypto",
    "title": "\u52a0\u5bc6\u5de5\u5177",
    "description": "\u94fe\u4e0a\u3001\u884d\u751f\u54c1\u3001\u673a\u6784\u7814\u7a76\u3001\u4e00\u7ea7\u5e02\u573a\u4e0e\u52a0\u5bc6\u65b0\u95fb\u8d44\u6e90\u3002",
    "groups": [
      {
        "id": "crypto-item",
        "title": "\u6838\u5fc3\u770b\u677f",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u6838\u5fc3\u770b\u677f\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "crypto-btcdayu-gitbook-io-1",
            "name": "\u5e01\u5708\u79d1\u666e\uff1a\u4e0d\u51bb\u5361\u51fa\u91d1\u3001\u7092\u7f8e\u80a1\uff0c\u4e00\u6b21\u5168\u641e\u5b9a | \u806a\u660e\u7684\u6295\u8d44\u8005\uff08\u5e01\u5708\u7248\uff09",
            "url": "https://btcdayu.gitbook.io/dayu/dao-hang-yu-ru-men/xin-shou-ru-men/bu-dong-ka-chu-jin-chao-mei-gu-yi-ci-quan-gao-ding",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "btcdayu.gitbook.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-charts-bgeometrics-com-2",
            "name": "\u5927\u5c0f\u9cb8\u9c7c\u94fe\u4e0a\u5730\u5740\u8d2d\u4e70\u60c5\u51b5",
            "url": "https://charts.bgeometrics.com/bitcoin_distribution_coins_tables.html",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "charts.bgeometrics.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-charts-bgeometrics-com-3",
            "name": "URPD",
            "url": "https://charts.bgeometrics.com/distribution_realized_price.html",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "charts.bgeometrics.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-insights-glassnode-com-4",
            "name": "\u94fe\u4e0a\u90e8\u5206\u6559\u5b66",
            "url": "https://insights.glassnode.com/tag/product/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "insights.glassnode.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-insights-glassnode-com-5",
            "name": "Glassnode \u94fe\u4e0a\u6bcf\u5468\u7b80\u62a5",
            "url": "https://insights.glassnode.com/tag/newsletter/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "insights.glassnode.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-studio-glassnode-com-6",
            "name": "Glassnode Studio - \u94fe\u4e0a\u5404\u7c7b\u6570\u636e",
            "url": "https://studio.glassnode.com/charts/addresses.ActiveCount?a=BTC",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "studio.glassnode.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-cryptoquant-com-7",
            "name": "\u52a0\u5bc6\u5404\u7c7b\u94fe\u4e0a\u6570\u636e | CryptoQuant",
            "url": "https://cryptoquant.com/asset/btc/summary",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "cryptoquant.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-valuescan-io-8",
            "name": "\u52a0\u5bc6AI\u76d1\u63a7\u8d44\u91d1\u6d41valuescan",
            "url": "https://www.valuescan.io/tokenDetails?keyword=1",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.valuescan.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-coinglass-com-9",
            "name": "\u6301\u4ed3\u8d44\u8d39\u8ffd\u8e2a | CoinGlass",
            "url": "https://www.coinglass.com/tv/zh/Binance_BTCUSDT",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.coinglass.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-coinglass-com-10",
            "name": "CoinGlass\u9996\u9875",
            "url": "https://www.coinglass.com/zh",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.coinglass.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-farside-co-uk-11",
            "name": "\u6bd4\u7279\u5e01 ETF \u6d41\u5411 \u2013 Farside \u6295\u8d44\u8005",
            "url": "https://farside.co.uk/?p=997",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "farside.co.uk",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-sosovalue-com-12",
            "name": "sosovalue\u52a0\u5bc6\u5404\u9879\u6570\u636e",
            "url": "https://sosovalue.com/zh/assets/etf/us-btc-spot",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "sosovalue.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-greeks-live-13",
            "name": "\u52a0\u5bc6\u671f\u6743\u6570\u636e--greeks",
            "url": "https://www.greeks.live/#/deribit/tools/datalab?currency=BTC",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.greeks.live",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-deribit-com-14",
            "name": "Bitcoin Metrics - Deribit by Coinbase",
            "url": "https://www.deribit.com/statistics/BTC/metrics/options",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.deribit.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-charts-checkonchain-com-15",
            "name": "BTC\u671f\u8d27\u671f\u9650\u7ed3\u6784",
            "url": "https://charts.checkonchain.com/btconchain/derivatives/derivatives_termstructure_0/derivatives_termstructure_0_light.html",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "charts.checkonchain.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-saylortracker-com-16",
            "name": "\u5fae\u7b56\u7565\u8d2d\u4e70\u8bb0\u5f55",
            "url": "https://saylortracker.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "saylortracker.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-bitcointreasuries-net-17",
            "name": "BTC\u516c\u53f8\u3001ETF\u3001\u653f\u5e9c\u7b49\u8d2d\u4e70\u548c\u5206\u5e03\u60c5\u51b5",
            "url": "https://bitcointreasuries.net/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "bitcointreasuries.net",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-strategicethreserve-xyz-18",
            "name": "E\u7b56\u7565\u6570\u636e",
            "url": "https://www.strategicethreserve.xyz/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.strategicethreserve.xyz",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-validatorqueue-com-19",
            "name": "ETH\u9a8c\u8bc1\u8005\u961f\u5217",
            "url": "https://www.validatorqueue.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.validatorqueue.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-bitcoinlaws-io-20",
            "name": "\u7f8e\u56fd\u52a0\u5bc6\u653f\u7b56\u8ddf\u8e2a",
            "url": "https://bitcoinlaws.io/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "bitcoinlaws.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-cryptobubbles-net-21",
            "name": "Crypto Bubbles",
            "url": "https://cryptobubbles.net/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "cryptobubbles.net",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-coinmarketcap-com-22",
            "name": "\u52a0\u5bc6\u8d5b\u9053\u548c\u5e02\u503cCoinMarketCap",
            "url": "https://coinmarketcap.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "coinmarketcap.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-intothecryptoverse-com-23",
            "name": "\u8ba2\u9605\u7cbe\u7b80\u7248\u8ba1\u5212 \u2013 \u8fdb\u5165\u52a0\u5bc6\u8d27\u5e01\u4e16\u754c",
            "url": "https://intothecryptoverse.com/product-lite-plan/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "intothecryptoverse.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-tokenomist-ai-24",
            "name": "\u4ee3\u5e01\u89e3\u9501 | \u8ffd\u8e2a\u6700\u65b0\u6570\u636e\u5e76\u5b8c\u6210\u89e3\u9501\u8ba1\u5212",
            "url": "https://tokenomist.ai/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "tokenomist.ai",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-intel-arkm-com-25",
            "name": "\u94fe\u4e0a | Arkham",
            "url": "https://intel.arkm.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "intel.arkm.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-intel-arkm-com-26",
            "name": "\u7f8e\u56fd\u653f\u5e9c\u6301\u5e01\u6570",
            "url": "https://intel.arkm.com/explorer/entity/usg",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "intel.arkm.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-oklink-com-27",
            "name": "\u533a\u5757\u94fe\u6d4f\u89c8\u5668\u67e5\u8be2 | \u6b27\u79d1\u4e91\u94fe OKLink",
            "url": "https://www.oklink.com/zh-hans",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.oklink.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-app-rwa-xyz-28",
            "name": "RWA.xyz | \u533a\u5757\u94fe\u73b0\u5b9e\u4e16\u754c\u8d44\u4ea7\u5206\u6790---RWA.xyz |\u4ee3\u5e01\u5316\u73b0\u5b9e\u4e16\u754c\u8d44\u4ea7\u5206\u6790",
            "url": "https://app.rwa.xyz/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "app.rwa.xyz",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-app-intothecryptoverse-com-29",
            "name": "\u4eea\u8868\u677f | ITC",
            "url": "https://app.intothecryptoverse.com/dashboard",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "app.intothecryptoverse.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-stats-hyperliquid-xyz-30",
            "name": "Hyperliquid \u7edf\u8ba1\u6570\u636e",
            "url": "https://stats.hyperliquid.xyz/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "stats.hyperliquid.xyz",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-hypurrscan-io-31",
            "name": "HypurrScan | Hyperliquid Explorer",
            "url": "https://hypurrscan.io/address/0x5078C2fBeA2b2aD61bc840Bc023E35Fce56BeDb6?s=09",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "hypurrscan.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-chaincatcher-com-32",
            "name": "\u94fe\u6355\u624bChainCatcher \u2014 \u4e13\u4e1a\u7684\u533a\u5757\u94fe\u6280\u672f\u7814\u7a76\u4e0e\u8d44\u8baf\u5e73\u53f0-Chain Catcher",
            "url": "https://www.chaincatcher.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.chaincatcher.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-wintermute-com-33",
            "name": "\u505a\u5e02\u5546Wintermute",
            "url": "https://www.wintermute.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.wintermute.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-signalplus-com-34",
            "name": "\u505a\u671f\u6743\u7684\uff1aSignalPlus - Democratizing Options for Digital Assets",
            "url": "https://www.signalplus.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.signalplus.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-github-com-35",
            "name": "\u533a\u5757\u94fe\u6697\u68ee\u6797\u81ea\u536b\u624b\u518c",
            "url": "https://github.com/slowmist/Blockchain-dark-forest-selfguard-handbook",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "github.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-github-com-36",
            "name": "\u9ed1\u6697\u624b\u518c\u62d3\u5c55",
            "url": "https://github.com/evilcos/darkhandbook",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "github.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-unbias-fyi-37",
            "name": "\u6240\u6709\u5206\u6790\u5e08\u2014\u2014\u516c\u6b63\u65e0\u504f",
            "url": "https://unbias.fyi/analysts?source=all",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "unbias.fyi",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-www-benjamincowen-com-38",
            "name": "Benjamin Cowen | Macroeconomic Analyst & Data Scientist",
            "url": "https://www.benjamincowen.com/#services",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "www.benjamincowen.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-charts-checkonchain-com-39",
            "name": "\u6bd4\u7279\u5e01\u94fe\u4e0a\u5206\u6790\u4e0e\u56fe\u8868 - _checkonchain | BTC \u6307\u6807\u3001\u6307\u6570\u4e0e\u5e02\u573a\u6570\u636e",
            "url": "https://charts.checkonchain.com/",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "charts.checkonchain.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-strc-live-40",
            "name": "\u91cd\u8981\uff1aSTRC Price Today | Live Quote, 11.5% Yield & ATM Tracker",
            "url": "https://strc.live/ticker/strc",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "strc.live",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          },
          {
            "id": "crypto-cryptorank-io-41",
            "name": "\u505a\u7684\u633a\u597d\uff0c\u5c24\u5176\u4e00\u7ea7\u548c\u9884\u6d4b\u5e02\u573a\uff1aCryptoRank.io",
            "url": "https://cryptorank.io/prediction-markets",
            "description": "\u6765\u6e90: \u52a0\u5bc6",
            "domain": "cryptorank.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177"
            ]
          }
        ]
      },
      {
        "id": "crypto-kronos-btc",
        "title": "Kronos\u5b9e\u65f6\u9884\u6d4b | BTC",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201cKronos\u5b9e\u65f6\u9884\u6d4b | BTC\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "crypto-shiyu-coder-github-io-1",
            "name": "Kronos\u5b9e\u65f6\u9884\u6d4b | BTC/USDT",
            "url": "https://shiyu-coder.github.io/Kronos-demo/",
            "description": "\u6765\u6e90: Kronos\u5b9e\u65f6\u9884\u6d4b | BTC",
            "domain": "shiyu-coder.github.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "Kronos\u5b9e\u65f6\u9884\u6d4b | BTC"
            ]
          }
        ]
      },
      {
        "id": "crypto-item",
        "title": "\u5176\u4ed6",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u5176\u4ed6\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "crypto-www-aicoinzh-com-1",
            "name": "\u770b\u76d8\u8f6f\u4ef6--AICoin",
            "url": "https://www.aicoinzh.com/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.aicoinzh.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-aggr-trade-2",
            "name": "\u52a0\u5bc6\u53e6\u4e00\u4e2a\u770b\u76d8\u8f6f\u4ef6\uff0c\u8c8c\u4f3c\u53ef\u770b\u8ba2\u5355\u6d41",
            "url": "https://aggr.trade/bi81",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "aggr.trade",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-tradinglite-com-3",
            "name": "\u6d41\u52a8\u6027\u548c\u8ba2\u5355\u6d41--TradingLite \u4ea4\u6613\u5e73\u53f0",
            "url": "https://tradinglite.com/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "tradinglite.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-bitbo-io-4",
            "name": "\u6bd4\u7279\u5e01\u65e5\u5386",
            "url": "https://bitbo.io/calendar/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "bitbo.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-www-coincarp-com-5",
            "name": "\u52a0\u5bc6\u8d27\u5e01\u6d3b\u52a8\u65e5\u5386 | CoinCarp",
            "url": "https://www.coincarp.com/events/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.coincarp.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-gmgn-ai-6",
            "name": "\u806a\u660e\u94b1\u8ffd\u8e2a--GMGN.AI",
            "url": "https://gmgn.ai/?ref=NtZl14CJ&chain=sol",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "gmgn.ai",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-axiom-trade-7",
            "name": "\u806a\u660e\u94b1|discover",
            "url": "https://axiom.trade/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "axiom.trade",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-xxi-money-8",
            "name": "21\u8d44\u672c\u5b98\u7f51",
            "url": "https://xxi.money/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "xxi.money",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-www-ishares-com-9",
            "name": "IBIT\u5b98\u7f51",
            "url": "https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf#/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.ishares.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-www-bitcoinmagazinepro-com-10",
            "name": "\u548cglassnode\u7c7b\u4f3c | BM Pro",
            "url": "https://www.bitcoinmagazinepro.com/charts/mvrv-zscore/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.bitcoinmagazinepro.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-cn-investing-com-11",
            "name": "\u6bd4\u7279\u5e01\u5386\u53f2\u6570\u636e\u514d\u8d39\u4e0b\u8f7d--\u82f1\u4e3a\u8d22\u60c5",
            "url": "https://cn.investing.com/crypto/bitcoin/historical-data",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "cn.investing.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-www-cryptodatadownload-com-12",
            "name": "\u52a0\u5bc6\u514d\u8d39\u6570\u636e",
            "url": "https://www.cryptodatadownload.com/data/gemini/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.cryptodatadownload.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-www-amberdata-io-13",
            "name": "\u52a0\u5bc6\u673a\u6784\u7ea7\u671f\u6743\u5206\u6790",
            "url": "https://www.amberdata.io/ad-derivatives",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.amberdata.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-coinmetrics-io-14",
            "name": "\u4e3b\u9875 - Coin Metrics",
            "url": "https://coinmetrics.io/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "coinmetrics.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-santiment-net-15",
            "name": "\u52a0\u5bc6\u7814\u7a76\u3001\u6570\u636e\u3001\u5de5\u5177 - \u63a2\u7d22\u884c\u4e3a\u5206\u6790",
            "url": "https://santiment.net/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "santiment.net",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-www-chainalysis-com-16",
            "name": "The Blockchain Data Platform - Chainalysis",
            "url": "https://www.chainalysis.com/#research",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.chainalysis.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-messari-io-17",
            "name": "\u52a0\u5bc6\u8d27\u5e01\u7814\u7a76\u3001\u62a5\u544a\u3001\u4eba\u5de5\u667a\u80fd\u65b0\u95fb\u3001\u5b9e\u65f6\u4ef7\u683c\u3001\u4ee3\u5e01\u89e3\u9501\u548c\u7b79\u6b3e\u6570\u636e",
            "url": "https://messari.io/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "messari.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-dune-com-18",
            "name": "Dune \u2014 \u7531\u793e\u533a\u63d0\u4f9b\u652f\u6301\u7684\u52a0\u5bc6\u5206\u6790\u3002",
            "url": "https://dune.com/home",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "dune.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-uniscan-cc-19",
            "name": "UniScan | \u652f\u6301\u5e8f\u6570\u8bcd\u3001\u7b26\u6587\u3001\u70f7\u70c3",
            "url": "https://uniscan.cc/fractal/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "uniscan.cc",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-mempool-space-20",
            "name": "mempool - Bitcoin Explorer",
            "url": "https://mempool.space/zh/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "mempool.space",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-etherscan-io-21",
            "name": "Ethereum Gas Tracker | Etherscan",
            "url": "https://etherscan.io/gastracker",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "etherscan.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-ultrasound-money-22",
            "name": "0 Gwei | $4,481 | ultrasound.money",
            "url": "https://ultrasound.money/",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "ultrasound.money",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-platform-spotonchain-ai-23",
            "name": "Spot On Chain - \u5e73\u53f0",
            "url": "https://platform.spotonchain.ai/zh",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "platform.spotonchain.ai",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-www-macromicro-me-24",
            "name": "\u6bd4\u7279\u5e01BTC\u9a71\u52a8\u4e09\u5927\u56e0\u7d20\uff1a\u6d41\u52a8\u6027\uff06\u5b9e\u9645\u5229\u7387\uff06PE | \u7528\u6237\u56fe\u7ec4| MacroMicro \u8d22\u7ecfM\u5e73\u65b9",
            "url": "https://www.macromicro.me/collections/22514/bi-te-bi_418919/111972/bi-te-bi-BTC-qu-dong-san-da-yin-su-liu-dong-xing-shi-ji-li-lyu-GDP",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "www.macromicro.me",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          },
          {
            "id": "crypto-chart-kiyotaka-ai-25",
            "name": "\u770b\u8ba2\u5355\u6d41\u548c\u52a0\u603bOI\u7684\u770b\u76d8\u8f6f\u4ef6",
            "url": "https://chart.kiyotaka.ai/JF9o688G",
            "description": "\u6765\u6e90: \u5176\u4ed6",
            "domain": "chart.kiyotaka.ai",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5176\u4ed6"
            ]
          }
        ]
      },
      {
        "id": "crypto-item",
        "title": "\u673a\u6784",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u673a\u6784\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "crypto-coinshares-com-1",
            "name": "CoinShares | \u6253\u9020\u6295\u8d44\u7684\u672a\u6765",
            "url": "https://coinshares.com/corp/",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "coinshares.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-a16zcrypto-substack-com-2",
            "name": "\u6765\u81ea a16zcrypto \u7684 web3 \u4fe1\u4ef6 | a16z \u52a0\u5bc6 | Substack",
            "url": "https://a16zcrypto.substack.com/",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "a16zcrypto.substack.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-www-vaneck-com-3",
            "name": "\u6570\u5b57\u8d44\u4ea7 | \u6d1e\u5bdf | VanEck",
            "url": "https://www.vaneck.com/us/en/insights/digital-assets/?p=1",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "www.vaneck.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-blog-river-com-4",
            "name": "Bitcoin Research\u7814\u62a5- River Intelligence Unit | River Financial",
            "url": "https://blog.river.com/tag/river-research/",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "blog.river.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-bitwiseinvestments-com-5",
            "name": "Insights | Bitwise Investments",
            "url": "https://bitwiseinvestments.com/crypto-market-insights",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "bitwiseinvestments.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-experts-bitwiseinvestments-com-5b",
            "name": "Bitwise \u6bcf\u5468\u5206\u6790",
            "url": "https://experts.bitwiseinvestments.com/cio-memos",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "experts.bitwiseinvestments.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784",
              "\u7814\u62a5"
            ]
          },
          {
            "id": "crypto-www-coinbase-com-6",
            "name": "Research - Coinbase Research & Insights Hub",
            "url": "https://www.coinbase.com/zh-cn/institutional/research-insights/research",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "www.coinbase.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-research-grayscale-com-7",
            "name": "\u7814\u7a76\u4e0e\u5e02\u573a\u5206\u6790 | \u7070\u5ea6",
            "url": "https://research.grayscale.com/",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "research.grayscale.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-www-binance-com-8",
            "name": "\u5e01\u5b89\u7814\u7a76\u9662",
            "url": "https://www.binance.com/zh-CN/research",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "www.binance.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-www-ark-invest-com-9",
            "name": "Innovation Research and Models by ARK Invest",
            "url": "https://www.ark-invest.com/articles",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "www.ark-invest.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-cryptohayes-substack-com-10",
            "name": "\u52a0\u5bc6\u8d27\u5e01\u4ea4\u6613\u8005\u6587\u6458 | Arthur Hayes | Substack",
            "url": "https://cryptohayes.substack.com/",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "cryptohayes.substack.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-4pillars-io-11",
            "name": "\u56db\u5927\u652f\u67f1",
            "url": "https://4pillars.io/en",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "4pillars.io",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          },
          {
            "id": "crypto-supersaiyan1957-substack-com-12",
            "name": "BTC \u6bcf\u5468\u6df1\u5ea6\u5206\u6790\u62a5\u544a ( + \u7f8e\u80a1\uff09 | 08 03 2026",
            "url": "https://supersaiyan1957.substack.com/p/btc-08-03-2026?r=1edbq9&utm_campaign=post&utm_medium=web&triedRedirect=true&_src_ref=bit.ly",
            "description": "\u6765\u6e90: \u673a\u6784",
            "domain": "supersaiyan1957.substack.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u673a\u6784"
            ]
          }
        ]
      },
      {
        "id": "crypto-item",
        "title": "\u7406\u8d22\u548c\u4e00\u7ea7",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u7406\u8d22\u548c\u4e00\u7ea7\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "crypto-www-rootdata-com-1",
            "name": "Web3 \u70ed\u95e8\u9879\u76ee\u6392\u540d",
            "url": "https://www.rootdata.com/zh",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "www.rootdata.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-www-theblockbeats-info-2",
            "name": "BlockBeats - \u4e13\u4e1a\u7684\u533a\u5757\u94fe\u7814\u7a76\u673a\u6784\u4e0e\u8d44\u8baf\u5e73\u53f0",
            "url": "https://www.theblockbeats.info/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "www.theblockbeats.info",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-www-bybit-com-3",
            "name": "Launchpool",
            "url": "https://www.bybit.com/zh-MY/trade/spot/launchpool",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "www.bybit.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-app-ethena-fi-4",
            "name": "\u804c\u4f4d | Ethena",
            "url": "https://app.ethena.fi/dashboards/positions",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "app.ethena.fi",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-defillama-com-5",
            "name": "Ethereum - DefiLlama",
            "url": "https://defillama.com/chain/Ethereum",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "defillama.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-btc-com-6",
            "name": "BTC.com \u4e3a\u5168\u7403\u533a\u5757\u94fe\u7231\u597d\u8005\u63d0\u4f9b\u4e13\u4e1a\u7684\u6570\u636e\u4e0e\u77ff\u6c60\u670d\u52a1",
            "url": "https://btc.com/zh-CN",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "btc.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-dexscreener-com-7",
            "name": "DEX Screener",
            "url": "https://dexscreener.com/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "dexscreener.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-app-pendle-finance-8",
            "name": "Pendle",
            "url": "https://app.pendle.finance/trade/markets?utm_source=landing&utm_medium=landing",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "app.pendle.finance",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-miningpoolstats-stream-9",
            "name": "\u6316\u77ffBTC\u6570\u636e",
            "url": "https://miningpoolstats.stream/bitcoin",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "miningpoolstats.stream",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-morpho-org-10",
            "name": "Morpho | The most trusted network for onchain loans",
            "url": "https://morpho.org/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "morpho.org",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-app-kamino-finance-11",
            "name": "\u8d37\u6b3e | \u5361\u7c73\u8bfa\u91d1\u878d",
            "url": "https://app.kamino.finance/earn/lend",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "app.kamino.finance",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-app-lulo-fi-12",
            "name": "Lulo",
            "url": "https://app.lulo.fi/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "app.lulo.fi",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-app-uniswap-org-13",
            "name": "\u5728 Uniswap \u4e0a\u63a2\u7d22 Ethereum \u7684\u70ed\u95e8\u8d44\u91d1\u6c60",
            "url": "https://app.uniswap.org/explore/pools",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "app.uniswap.org",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-app-spark-fi-14",
            "name": "Spark\uff1a\u5229\u7528\u7a33\u5b9a\u5e01\u8d5a\u94b1",
            "url": "https://app.spark.fi/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "app.spark.fi",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-1key-so-15",
            "name": "OneKey",
            "url": "https://1key.so/earn",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "1key.so",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-www-apeoclock-com-16",
            "name": "defi\u9879\u76ee\u53d1\u5e03\u65e5\u5386",
            "url": "https://www.apeoclock.com/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "www.apeoclock.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-stake-lido-fi-17",
            "name": "ETH\u8d28\u62bc",
            "url": "https://stake.lido.fi/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "stake.lido.fi",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-web3daoge-com-18",
            "name": "\u7a33\u5b9a\u5e01\u7406\u8d22\u770b\u677f",
            "url": "https://web3daoge.com/",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "web3daoge.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          },
          {
            "id": "crypto-app-barker-money-19",
            "name": "Barker - Find the Best Stablecoin Yields",
            "url": "https://app.barker.money/campaigns",
            "description": "\u6765\u6e90: \u7406\u8d22\u548c\u4e00\u7ea7",
            "domain": "app.barker.money",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u7406\u8d22\u548c\u4e00\u7ea7"
            ]
          }
        ]
      },
      {
        "id": "crypto-item",
        "title": "\u5f71\u5b50\u94f6\u884c\u7b49",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u5f71\u5b50\u94f6\u884c\u7b49\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "crypto-hackernoon-com-1",
            "name": "\u5f71\u5b50\u94f6\u884c",
            "url": "https://hackernoon.com/u/antongolub",
            "description": "\u6765\u6e90: \u5f71\u5b50\u94f6\u884c\u7b49",
            "domain": "hackernoon.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5f71\u5b50\u94f6\u884c\u7b49"
            ]
          },
          {
            "id": "crypto-blog-bitmex-com-2",
            "name": "\u60a8\u641c\u7d22\u7684\u662f\u201cReckless \u2013 Chapter\u201d | BitMEX \u535a\u5ba2",
            "url": "https://blog.bitmex.com/?s=Reckless+%E2%80%93+Chapter&lang=en_us",
            "description": "\u6765\u6e90: \u5f71\u5b50\u94f6\u884c\u7b49",
            "domain": "blog.bitmex.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5f71\u5b50\u94f6\u884c\u7b49"
            ]
          }
        ]
      }
    ]
  },
  {
    "id": "metal",
    "title": "\u91d1\u5c5e\u5de5\u5177",
    "description": "\u9ec4\u91d1\u3001\u8d35\u91d1\u5c5e\u4e0e\u5546\u54c1\u94fe\u6761\u76f8\u5173\u4ea4\u6613\u5de5\u5177\u3002",
    "groups": [
      {
        "id": "metal-item",
        "title": "\u9ec4\u91d1",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u9ec4\u91d1\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "metal-chartexchange-com-1",
            "name": "GLD \u501f\u6b3e\u5229\u7387 (CTB) | ChartExchange",
            "url": "https://chartexchange.com/symbol/nyse-gld/borrow-fee/",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "chartexchange.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-lbma-org-uk-2",
            "name": "\u4f26\u6566\u91d1\u5e93\u6570\u636e | LBMA",
            "url": "https://www.lbma.org.uk/prices-and-data/london-vault-data",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.lbma.org.uk",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-commoditieschart-net-3",
            "name": "Comex \u91d1\u5e93\u5b58",
            "url": "https://commoditieschart.net/zh/metals/gold/comex-gold-stocks",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "commoditieschart.net",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-china-gold-org-4",
            "name": "\u4e16\u754c\u9ec4\u91d1\u534f\u4f1a\uff1a\u9ec4\u91d1ETF\u7684\u6301\u6709\u91cf\u548c\u6d41\u91cf | World Gold Council",
            "url": "https://china.gold.org/goldhub/data/gold-etfs-holdings-and-flows#from-login=1&login-type=wechat",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "china.gold.org",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-gold-org-5",
            "name": "\u5404\u56fd\u592e\u884c\u9ec4\u91d1\u50a8\u5907 | \u4e16\u754c\u9ec4\u91d1\u534f\u4f1a",
            "url": "https://www.gold.org/goldhub/data/gold-reserves-by-country",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.gold.org",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-gold-org-6",
            "name": "\u5404\u5927\u4ea4\u6613\u6240\u672a\u5e73\u4ed3\u5408\u7ea6\u6570",
            "url": "https://www.gold.org/goldhub/data/gold-open-interest",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.gold.org",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-china-gold-org-7",
            "name": "\u9ec4\u91d1\u671f\u8d27\u4ef7\u683c\u66f2\u7ebf\uff5c\u4e16\u754c\u9ec4\u91d1\u534f\u4f1a",
            "url": "https://china.gold.org/goldhub/data/gold-futures-curves#from-login=1&login-type=wechat",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "china.gold.org",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-jiaoyifamen-com-8",
            "name": "\u4ea4\u6613\u6cd5\u95e8",
            "url": "https://www.jiaoyifamen.com/variety/positionAnalysis-CFTC",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.jiaoyifamen.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-cmegroup-com-9",
            "name": "CME Group Volatility Indexes (CVOL) - CME Group",
            "url": "https://www.cmegroup.com/market-data/cme-group-benchmark-administration/cme-group-volatility-indexes.html",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.cmegroup.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-cmegroup-com-10",
            "name": "\u9ec4\u91d1\u671f\u8d27\u4ea4\u6613\u91cf\u4e0e\u6301\u4ed3\u91cf - CME \u96c6\u56e2 --- Gold Futures Volume & Open Interest - CME Group",
            "url": "https://www.cmegroup.com/markets/metals/precious/gold.volume.html?utm_source=chatgpt.com",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.cmegroup.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-cmegroup-com-11",
            "name": "COT\u62a5\u544a\u6301\u4ed3",
            "url": "https://www.cmegroup.com/tools-information/quikstrike/commitment-of-traders.html?pid=40#cmeloginteaser1",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.cmegroup.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-giresearch-substack-com-12",
            "name": "\u9ec4\u91d1\u6295\u8d44\u8005\u7814\u7a76 | Chris Rutherglen \u535a\u58eb | Substack",
            "url": "https://giresearch.substack.com/?utm_source=%2Fsearch%2FGold%2520Investor%2520Research&utm_medium=reader2&utm_campaign=reader2",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "giresearch.substack.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-incrementum-li-13",
            "name": "\u671f\u520a - Incrementum",
            "url": "https://www.incrementum.li/en/journal/",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.incrementum.li",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-cmegroup-com-14",
            "name": "Gold Option Volume & Open Interest - CME Group",
            "url": "https://www.cmegroup.com/markets/metals/precious/gold.volume.options.html#optionProductId=192",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.cmegroup.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-cmegroup-com-15",
            "name": "\u91d1\u5c5e\u6bcf\u65e5\u4ea4\u6613\u91cf\u53ca\u672a\u5e73\u4ed3\u5408\u7ea6 - \u829d\u5546\u6240\u96c6\u56e2",
            "url": "https://www.cmegroup.com/market-data/browse-data/metals-volume.html",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.cmegroup.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          },
          {
            "id": "metal-www-lbma-org-uk-16",
            "name": "Clearing Data | LBMA",
            "url": "https://www.lbma.org.uk/prices-and-data/clearing-data",
            "description": "\u6765\u6e90: \u9ec4\u91d1",
            "domain": "www.lbma.org.uk",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u9ec4\u91d1"
            ]
          }
        ]
      },
      {
        "id": "metal-item",
        "title": "\u5546\u54c1",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u5546\u54c1\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "metal-www-jiaoyifamen-com-1",
            "name": "\u4ea4\u6613\u6cd5\u95e8",
            "url": "https://www.jiaoyifamen.com/variety/varieties-varieties",
            "description": "\u6765\u6e90: \u5546\u54c1",
            "domain": "www.jiaoyifamen.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5546\u54c1"
            ]
          },
          {
            "id": "metal-x-qhkch-com-2",
            "name": "\u56fd\u5185\u5546\u54c1\u671f\u8d27\u5404\u7c7b\u6570\u636e- \u5947\u8d27\u53ef\u67e5",
            "url": "https://x.qhkch.com/variety/position",
            "description": "\u6765\u6e90: \u5546\u54c1",
            "domain": "x.qhkch.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5546\u54c1"
            ]
          },
          {
            "id": "metal-en-macromicro-me-3",
            "name": "US - Crack Spread vs. Oil Price | Crude Oil | Collection | MacroMicro",
            "url": "https://en.macromicro.me/collections/19/mm-oil-price/4376/crude-oil-cracking-spread-vs-wti",
            "description": "\u6765\u6e90: \u5546\u54c1",
            "domain": "en.macromicro.me",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5546\u54c1"
            ]
          },
          {
            "id": "metal-www-1qh-cn-4",
            "name": "\u671f\u8d27\u5957\u5229\u5206\u6790_\u8de8\u671f\u4ef7\u5dee\u67e5\u8be2_\u6700\u65b0\u4ef7\u5dee\u8d70\u52bf\u56fe-\u4e00\u671f\u8d27",
            "url": "https://www.1qh.cn/tools/spread.html",
            "description": "\u6765\u6e90: \u5546\u54c1",
            "domain": "www.1qh.cn",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5546\u54c1"
            ]
          },
          {
            "id": "metal-business-ucdenver-edu-5",
            "name": "\u6469\u6839\u5927\u901a\u5546\u54c1\u4e0e\u80fd\u6e90\u7ba1\u7406\u4e2d\u5fc3 | \u79d1\u7f57\u62c9\u591a\u5927\u5b66\u4e39\u4f5b\u5546\u5b66\u9662",
            "url": "https://business.ucdenver.edu/jpmorgancenter",
            "description": "\u6765\u6e90: \u5546\u54c1",
            "domain": "business.ucdenver.edu",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5546\u54c1"
            ]
          },
          {
            "id": "metal-ent-htfc-com-6",
            "name": "\u5de5\u4f5c\u53f0-\u534e\u6cf0\u5929\u7391",
            "url": "https://ent.htfc.com/#/homePage/index?reportId&catalogId",
            "description": "\u6765\u6e90: \u5546\u54c1",
            "domain": "ent.htfc.com",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5546\u54c1"
            ]
          },
          {
            "id": "metal-hq-smm-cn-7",
            "name": "\u6709\u8272\u91d1\u5c5e\u671f\u8d27\u8fdb\u53e3\u76c8\u4e8f\u7387_\u4e0a\u6d77\u6709\u8272\u7f51",
            "url": "https://hq.smm.cn/data/arbi",
            "description": "\u6765\u6e90: \u5546\u54c1",
            "domain": "hq.smm.cn",
            "tags": [
              "\u4ea4\u6613\u5de5\u5177",
              "\u5546\u54c1"
            ]
          }
        ]
      }
    ]
  },
  {
    "id": "quant",
    "title": "\u91cf\u5316\u5de5\u5177",
    "description": "\u91cf\u5316\u7814\u7a76\u3001\u6570\u636e\u63a5\u53e3\u3001\u56de\u6d4b\u6846\u67b6\u4e0e\u91cf\u5316\u793e\u533a\u3002",
    "groups": [
      {
        "id": "quant-item",
        "title": "\u91cf\u5316\u7c7b\u597d\u6587\u7ae0",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u91cf\u5316\u7c7b\u597d\u6587\u7ae0\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-bigquant-com-1",
            "name": "\u91d1\u5de5CTA\u7cfb\u5217\u4e4b\u4e00\uff1a\u57fa\u4e8e\u57fa\u672c\u9762\u591a\u56e0\u5b50\u6a21\u578b\u7684\u9ec4\u91d1\u4ea4\u6613\u7b56\u7565 \u4e2d\u6cf0\u8bc1\u5238_20181231 - BigQuant\u91cf\u5316\u4ea4\u6613",
            "url": "https://bigquant.com/wiki/doc/oiVYuLosvU",
            "description": "\u6765\u6e90: \u91cf\u5316\u7c7b\u597d\u6587\u7ae0",
            "domain": "bigquant.com",
            "tags": [
              "\u91cf\u5316",
              "\u91cf\u5316\u7c7b\u597d\u6587\u7ae0"
            ]
          },
          {
            "id": "quant-blog-csdn-net-2",
            "name": "\u7edf\u8ba1\u5957\u5229\u7b56\u7565\u7684\u4e94\u5927\u4e3b\u6d41\u7b56\u7565\u5206\u6790\u4e0e\u4f18\u7f3a\u70b9_copula\u51fd\u6570\u7684\u7f3a\u70b9-CSDN\u535a\u5ba2",
            "url": "https://blog.csdn.net/zk168_net/article/details/107536782",
            "description": "\u6765\u6e90: \u91cf\u5316\u7c7b\u597d\u6587\u7ae0",
            "domain": "blog.csdn.net",
            "tags": [
              "\u91cf\u5316",
              "\u91cf\u5316\u7c7b\u597d\u6587\u7ae0"
            ]
          },
          {
            "id": "quant-www-myquant-cn-3",
            "name": "\u8de8\u671f\u5957\u5229(\u671f\u8d27) - \u7ecf\u5178\u7b56\u7565 - \u6398\u91d1\u91cf\u5316",
            "url": "https://www.myquant.cn/docs/python_strategyies/107",
            "description": "\u6765\u6e90: \u91cf\u5316\u7c7b\u597d\u6587\u7ae0",
            "domain": "www.myquant.cn",
            "tags": [
              "\u91cf\u5316",
              "\u91cf\u5316\u7c7b\u597d\u6587\u7ae0"
            ]
          }
        ]
      },
      {
        "id": "quant-item",
        "title": "\u91cf\u5316\u603b\u89c8",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u91cf\u5316\u603b\u89c8\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-www-wolai-com-1",
            "name": "2025\u5e748\u6708 \u91cf\u5316\u91d1\u5de5\u6708\u5ea6\u70ed\u70b9\u7814\u62a5",
            "url": "https://www.wolai.com/ustfinance/uyMty39PGZafSZa2YU93mQ",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.wolai.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-wolai-com-2",
            "name": "\u91cf\u5316\u5b66\u4e60\u8def\u5f84",
            "url": "https://www.wolai.com/ustfinance/uQLt7axQsJBeTdJaMiNvW9",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.wolai.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-blog-csdn-net-3",
            "name": "CSDN\u535a\u5ba2",
            "url": "https://blog.csdn.net/weixin_42219751/article/details/93621991",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "blog.csdn.net",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-bigquant-com-4",
            "name": "bigquant:\u3010\u5386\u53f2\u6587\u6863\u3011\u7b56\u7565\u793a\u4f8b-\u671f\u8d27\u7b56\u7565-\u57fa\u4e8e\u534f\u6574\u7684\u8de8\u671f\u5957\u5229 v1.0",
            "url": "https://bigquant.com/wiki/doc/Tqrre7n7tb",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "bigquant.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-joinquant-com-5",
            "name": "\u793e\u533a - JoinQuant",
            "url": "https://www.joinquant.com/view/community/list?listType=1",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.joinquant.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-joinquant-com-6",
            "name": "JoinQuant\u805a\u5bbd\u91cf\u5316\u6295\u7814\u5e73\u53f0",
            "url": "https://www.joinquant.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.joinquant.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-quantconnect-com-7",
            "name": "\u5f00\u6e90\u7b97\u6cd5\u4ea4\u6613\u5e73\u53f0\u3002 - QuantConnect.com",
            "url": "https://www.quantconnect.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.quantconnect.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-uqer-datayes-com-8",
            "name": "\u4f18\u77ff - \u5927\u6570\u636e\u65f6\u4ee3\u7684\u91cf\u5316\u6295\u8d44 - \u901a\u8054\u91cf\u5316\u5b9e\u9a8c\u5ba4",
            "url": "https://uqer.datayes.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "uqer.datayes.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-uqer-datayes-com-9",
            "name": "labs - \u77e5\u8bc6\u5e93 - \u4f18\u77ff",
            "url": "https://uqer.datayes.com/labs/knowledge/%E4%BC%98%E7%9F%BF%E4%BA%A7%E5%93%81%E7%99%BD%E7%9A%AE%E4%B9%A6%2F%E9%87%8F%E5%8C%96%E6%8A%95%E8%B5%84%E5%8F%8A%E5%85%B6%E7%A0%94%E7%A9%B6%E6%96%B9%E6%B3%95.nb",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "uqer.datayes.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-tushare-pro-10",
            "name": "Tushare\u6570\u636e",
            "url": "https://tushare.pro/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "tushare.pro",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-quantopian-github-io-11",
            "name": "Alphalens \u2014 Alphalens 0.2.1+48.gad0be10 \u6587\u6863",
            "url": "https://quantopian.github.io/alphalens/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "quantopian.github.io",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-github-com-12",
            "name": "\u91cf\u5316\u62a5\u544a\u8d44\u6599\u5e93",
            "url": "https://github.com/QuantNi/Quant-Report",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-gallery-pyecharts-org-13",
            "name": "Document",
            "url": "https://gallery.pyecharts.org/#/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "gallery.pyecharts.org",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-substack-com-14",
            "name": "\u52a0\u5bc6\u91cf\u5316\u535a\u4e3b",
            "url": "https://substack.com/@unexpectedcorrelations",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "substack.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-docs-pandas-ai-com-15",
            "name": "PandasAI\u7b80\u4ecb - PandasAI",
            "url": "https://docs.pandas-ai.com/v2/intro",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "docs.pandas-ai.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-quantpedia-com-16",
            "name": "\u4e3b\u9875 - QuantPedia",
            "url": "https://quantpedia.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "quantpedia.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-mp-weixin-qq-com-17",
            "name": "\u300c\u91cf\u5316\u754c\u300d\u5e74\u5ea6\u6700\u53d7\u6b22\u8fce\u768410\u7bc7\u535a\u5ba2",
            "url": "https://mp.weixin.qq.com/s/CYZ7tPcNYxGr3pSVkd2NSQ",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "mp.weixin.qq.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-quantpedia-com-18",
            "name": "\u5982\u4f55\u5229\u7528\u6bd4\u7279\u5e01\u9694\u591c\u4ea4\u6613\u83b7\u5229\uff1f - QuantPedia",
            "url": "https://quantpedia.com/how-to-profitably-trade-bitcoins-overnight-sessions/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "quantpedia.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-quantpedia-com-19",
            "name": "\u6211\u4eec\u5e94\u8be5\u5728\u6295\u8d44\u7ec4\u5408\u4e2d\u5206\u914d\u591a\u5c11\u6bd4\u7279\u5e01\uff1f - QuantPedia",
            "url": "https://quantpedia.com/how-much-bitcoin-should-we-allocate-to-the-portfolio/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "quantpedia.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-chartjs-org-20",
            "name": "Chart.js Samples | Chart.js",
            "url": "https://www.chartjs.org/docs/latest/samples/information.html",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.chartjs.org",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-pandaai-online-21",
            "name": "Panda AI - \u91cf\u53d8\u5b66\u9662\uff0c\u53ef\u4ee5agent\u4ea4\u6613",
            "url": "https://www.pandaai.online/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.pandaai.online",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-vnpy-com-22",
            "name": "VeighNa\u91cf\u5316\u793e\u533a - \u4f60\u7684\u5f00\u6e90\u793e\u533a\u91cf\u5316\u4ea4\u6613\u5e73\u53f0 | vn.py | vnpy",
            "url": "https://www.vnpy.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.vnpy.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-zhuanlan-zhihu-com-23",
            "name": "vnpy\uff1a\u56fd\u5185\u6700\u53d7\u6b22\u8fce\u7684\u5f00\u6e90\u91cf\u5316\u4ea4\u6613\u5e73\u53f0\u6df1\u5ea6\u89e3\u6790 - \u77e5\u4e4e",
            "url": "https://zhuanlan.zhihu.com/p/1934373021193343584",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "zhuanlan.zhihu.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-jupyter-org-24",
            "name": "JupyterLite",
            "url": "https://jupyter.org/try-jupyter/lab/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "jupyter.org",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-joinquant-com-25",
            "name": "\u805a\u5bbd",
            "url": "https://www.joinquant.com/view/user/floor?type=mainFloor",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.joinquant.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-backtest-10jqka-com-cn-26",
            "name": "\u81ea\u7136\u8bed\u8a00\u5373\u53ef\u56de\u6d4b\uff1aBackTest \u91cf\u5316\u7b56\u7565\u5e73\u53f0",
            "url": "https://backtest.10jqka.com.cn/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "backtest.10jqka.com.cn",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-bigquant-com-27",
            "name": "\u89e3\u9501 AI \u91cf\u5316\u65b0\u5883\u754c\uff1aQbot \u643a\u624b iTick - BigQuant\u91cf\u5316\u4ea4\u6613",
            "url": "https://bigquant.com/wiki/doc/kq9FxV9GUg",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "bigquant.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-quantstart-com-28",
            "name": "\u91cf\u5316\u81ea\u5b66\uff1a\u7b97\u6cd5\u4ea4\u6613\u3001\u91cf\u5316\u4ea4\u6613\u3001\u4ea4\u6613\u7b56\u7565\u3001\u56de\u6d4b\u4e0e\u5b9e\u65bd | QuantStart",
            "url": "https://www.quantstart.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.quantstart.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-blog-headlandstech-com-29",
            "name": "Headlands Technologies LLC \u535a\u5ba2 \u2013 \u5168\u7403\u91cf\u5316\u4ea4\u6613\u516c\u53f8",
            "url": "https://blog.headlandstech.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "blog.headlandstech.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-github-com-30",
            "name": "AI \u4ee3\u7801\u6307\u5357\u662f\u5f00\u59cb\u4f7f\u7528 AI \u8fdb\u884c\u7f16\u7801\u7684\u8def\u7ebf\u56fe\u3002",
            "url": "https://github.com/automata/aicodeguide",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-aurora-gold-insight-pages-dev-31",
            "name": "Aurora Gold Insight",
            "url": "https://aurora-gold-insight.pages.dev/#knowledge",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "aurora-gold-insight.pages.dev",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-cn-tradingview-com-32",
            "name": "BTCUSD 88,957.39 \u25b2 +0.25% \u5927\u7c7b\u8d44\u4ea7",
            "url": "https://cn.tradingview.com/chart/QlE64yj4/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "cn.tradingview.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-ptradeapi-com-33",
            "name": "Ptrade \u91cf\u5316\u4ea4\u6613 API\u63a5\u53e3\u6587\u6863",
            "url": "https://ptradeapi.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "ptradeapi.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-thinktrader-net-34",
            "name": "\u8fc5\u6295-\u4ee5\u601d\u8003\u7684\u901f\u5ea6\u4ea4\u6613qmt-\uff08\u5b98\u65b9\uff09",
            "url": "https://www.thinktrader.net/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.thinktrader.net",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-github-com-35",
            "name": "\u4ea4\u6613\u5e73\u53f0\u642d\u5efa",
            "url": "https://github.com/zhangjunmengyang/quant-research-platform/tree/main",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-ivolatility-com-36",
            "name": "\u4ed8\u8d39API\uff0c\u4f46\u5f88\u4fbf\u5b9c",
            "url": "https://www.ivolatility.com/data-cloud-api/?gad_source=1&gad_campaignid=20419477335&gbraid=0AAAAADyngPXx6BuAUQUg015xdcmQ1rc_M&gclid=CjwKCAiAssfLBhBDEiwAcLpwfulC_7LbiHzzBFUPw60W144ByHitONsLKbUJQo9B58SCDD_1ktS0NhoCyUsQAvD_BwE",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.ivolatility.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-alltick-co-37",
            "name": "API\uff1aReal-time Tick Data for Forex, US & HK Stocks, and Crypto CFD Data API - High Frequency Financial Data API - AllTick",
            "url": "https://alltick.co/#pricing",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "alltick.co",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-calendarific-com-38",
            "name": "\u5168\u7403\u8282\u5047\u65e5\u65e5\u5386 API\uff0c\u6db5\u76d6\u56fd\u5bb6\u548c\u5b97\u6559\u8282\u65e5\u3002",
            "url": "https://calendarific.com/",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "calendarific.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-github-com-39",
            "name": "AI\u91cf\u5316\u5b66\u4e60",
            "url": "https://github.com/waylandzhang/ai-quant-book/tree/main/manuscript/cn",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-www-fmz-com-40",
            "name": "\u8d44\u8d39\u7684\u53c2\u8003\u8d44\u7ba1\u5e73\u53f0",
            "url": "https://www.fmz.com/m/dashboard",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "www.fmz.com",
            "tags": [
              "\u91cf\u5316"
            ]
          },
          {
            "id": "quant-gitee-com-41",
            "name": "gitee",
            "url": "https://gitee.com/JavaLionLi/plus-ui",
            "description": "\u6765\u6e90: \u91cf\u5316",
            "domain": "gitee.com",
            "tags": [
              "\u91cf\u5316"
            ]
          }
        ]
      },
      {
        "id": "quant-item",
        "title": "\u63a5\u53e3",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201c\u63a5\u53e3\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-tushare-pro-1",
            "name": "Tushare\u6570\u636e",
            "url": "https://tushare.pro/document/2?doc_id=284",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "tushare.pro",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-www-alphavantage-co-2",
            "name": "API Documentation | Alpha Vantage",
            "url": "https://www.alphavantage.co/documentation/",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "www.alphavantage.co",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-akshare-akfamily-xyz-3",
            "name": "AKShare \u5916\u6c47\u6570\u636e \u2014 AKShare 1.17.83 \u6587\u6863",
            "url": "https://akshare.akfamily.xyz/data/fx/fx.html",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "akshare.akfamily.xyz",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-tushare-pro-4",
            "name": "Tushare\u6570\u636e",
            "url": "https://tushare.pro/document/2",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "tushare.pro",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-www-juejinshuju-com-5",
            "name": "\u6398\u91d1\uff1a\u56fd\u5185\u671f\u8d27\u5386\u53f2\u6570\u636e-\u4e3b\u8fde\u5206\u949fK\u7ebf-\u671f\u8d27\u4e3b\u8fde\u5386\u53f2\u5206\u949f\u6570\u636e\u4e0b\u8f7d-\u6398\u91d1\u6570\u636e",
            "url": "http://www.juejinshuju.com/future_continue_min/",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "www.juejinshuju.com",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-www-ricequant-com-6",
            "name": "RQData Python API \u624b\u518c | Ricequant Docs",
            "url": "https://www.ricequant.com/doc/rqdata/python/index-rqdatac",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "www.ricequant.com",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-itick-org-7",
            "name": "\u4e13\u4e1a\u91d1\u878d\u6570\u636eAPI\u63a5\u53e3 | \u80a1\u7968\u5916\u6c47\u52a0\u5bc6\u8d27\u5e01\u5b9e\u65f6\u884c\u60c5API | \u8d35\u91d1\u5c5e\u671f\u8d27\u57fa\u91d1\u6570\u636e | \u5b9e\u65f6\u62a5\u4ef7API | \u91cf\u5316\u4ea4\u6613\u63a5\u53e3 - iTick",
            "url": "https://itick.org/",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "itick.org",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-docs-itick-org-8",
            "name": "\u6587\u6863\u8bf4\u660e - iTick \u6587\u6863",
            "url": "https://docs.itick.org/",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "docs.itick.org",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-www-dataroma-com-9",
            "name": "DATAROMA \u8d85\u7ea7\u6295\u8d44\u8005\u6301\u80a1\u6458\u8981",
            "url": "https://www.dataroma.com/m/managers.php",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "www.dataroma.com",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          },
          {
            "id": "quant-doc-shinnytech-com-10",
            "name": "\u5341\u5206\u949f\u5feb\u901f\u5165\u95e8 \u2014 TianQin Python SDK 3.8.7 \u6587\u6863",
            "url": "https://doc.shinnytech.com/tqsdk/latest/quickstart.html#quickstart-0",
            "description": "\u6765\u6e90: \u63a5\u53e3",
            "domain": "doc.shinnytech.com",
            "tags": [
              "\u91cf\u5316",
              "\u63a5\u53e3"
            ]
          }
        ]
      },
      {
        "id": "quant-github-vnpy",
        "title": "GitHub - vnpy",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201cGitHub - vnpy\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-github-com-1",
            "name": "GitHub - vnpy/vnpy: \u57fa\u4e8ePython\u7684\u5f00\u6e90\u91cf\u5316\u4ea4\u6613\u5e73\u53f0\u5f00\u53d1\u6846\u67b6",
            "url": "https://github.com/vnpy/vnpy",
            "description": "\u6765\u6e90: GitHub - vnpy",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316",
              "GitHub - vnpy"
            ]
          }
        ]
      },
      {
        "id": "quant-github-shiyu-coder",
        "title": "GitHub - shiyu-coder",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201cGitHub - shiyu-coder\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-github-com-1",
            "name": "GitHub - shiyu-coder/Kronos\uff1aKronos\uff1a\u91d1\u878d\u5e02\u573a\u8bed\u8a00\u7684\u57fa\u7840\u6a21\u578b",
            "url": "https://github.com/shiyu-coder/Kronos",
            "description": "\u6765\u6e90: GitHub - shiyu-coder",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316",
              "GitHub - shiyu-coder"
            ]
          }
        ]
      },
      {
        "id": "quant-github-ufund-me",
        "title": "GitHub - UFund-Me",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201cGitHub - UFund-Me\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-github-com-1",
            "name": "GitHub - UFund-Me/Qbot: [\ud83d\udd25updating ...] AI \u81ea\u52a8\u91cf\u5316\u4ea4\u6613\u673a\u5668\u4eba(\u5b8c\u5168\u672c\u5730\u90e8\u7f72) AI-powered Quantitative Investment Research Platform. \ud83d\udcc3 online docs: https://ufund-me.github.io/Qbot \u2728 qbot-mini: https://github.com/Charmve/iQuant",
            "url": "https://github.com/UFund-Me/Qbot",
            "description": "\u6765\u6e90: Charmve",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316",
              "GitHub - UFund-Me"
            ]
          }
        ]
      },
      {
        "id": "quant-quantni",
        "title": "QuantNi",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201cQuantNi\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-github-com-1",
            "name": "QuantNi/Quant-Report",
            "url": "https://github.com/quantni/quant-report",
            "description": "\u6765\u6e90: QuantNi",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316",
              "QuantNi"
            ]
          }
        ]
      },
      {
        "id": "quant-pandaai-tech",
        "title": "PandaAI-Tech",
        "description": "\u6765\u81ea\u4e66\u7b7e\u6587\u4ef6\u5939\u201cPandaAI-Tech\u201d\u7684\u6574\u7406\u7ed3\u679c\u3002",
        "tools": [
          {
            "id": "quant-github-com-1",
            "name": "PandaAI-Tech/panda_quantflow",
            "url": "https://github.com/PandaAI-Tech/panda_quantflow",
            "description": "\u6765\u6e90: PandaAI-Tech",
            "domain": "github.com",
            "tags": [
              "\u91cf\u5316",
              "PandaAI-Tech"
            ]
          }
        ]
      }
    ]
  },
    {
      "id": "general",
      "title": "\u7efc\u5408\u5de5\u5177",
      "description": "\u8de8\u5e02\u573a\u8d44\u8baf\u3001\u4ea4\u6613\u65b0\u95fb\u4e0e\u96be\u4ee5\u5f52\u5165\u5355\u4e00\u8d44\u4ea7\u7684\u8f85\u52a9\u5de5\u5177\u3002",
      "groups": [
          {
              "id": "general-\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
              "title": "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8\u201d\u3002",
              "tools": [
                  {
                      "id": "general-app-hedgeye-com-1",
                      "name": "\u5f88\u6742\u7684\u5206\u6790",
                      "url": "https://app.hedgeye.com/?",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "app.hedgeye.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-x-com-1",
                      "name": "(28) Home / X",
                      "url": "https://x.com/home",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "x.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-financialjuice-com-1",
                      "name": "FinancialJuice\u9002\u5408\u62ff\u6765\u770b\u5b9e\u65f6\u7684",
                      "url": "https://www.financialjuice.com/home",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.financialjuice.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-cointelegraph-com-1",
                      "name": "\u7279\u8272 \u2014 Cointelegraph \u6742\u5fd7\u7684\u52a0\u5bc6\u8d27\u5e01\u6df1\u5ea6\u63a2\u7d22",
                      "url": "https://cointelegraph.com/magazine/features/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "cointelegraph.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-foresightnews-pro-1",
                      "name": "FN\u7cbe\u9009 - Foresight News",
                      "url": "https://foresightnews.pro/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "foresightnews.pro",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-jinse-cn-1",
                      "name": "\u91d1\u8272\u8d22\u7ecf_\u5728\u8fd9\u91cc\uff0c\u8bfb\u61c2\u533a\u5757\u94fe",
                      "url": "https://www.jinse.cn/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.jinse.cn",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-panewslab-com-1",
                      "name": "PANews \u4f60\u7684Web3\u4fe1\u606f\u5b98 | PANews",
                      "url": "https://www.panewslab.com/zh",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.panewslab.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-techflowpost-com-1",
                      "name": "\u4e13\u6ce8 Web3 \u4e0e AI \u884c\u4e1a\u6df1\u5ea6\u62a5\u9053\uff0c\u6d1e\u5bdf\u6f6e\u6c34\u6d41\u52a8\u7684\u65b9\u5411 - \u533a\u5757\u94fe\u5a92\u4f53 - \u533a\u5757\u94fe\u65b0\u95fb\u8d44\u8baf - \u533a\u5757\u94fe\u6280\u672f\u5e94\u7528 - \u533a\u5757\u94fe\u9879\u76ee\u673a\u6784 - \u6df1\u6f6eTechFlow",
                      "url": "https://www.techflowpost.com/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.techflowpost.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-coindesk-com-1",
                      "name": "CoinDesk: Bitcoin, Ethereum, Crypto News and Price Data",
                      "url": "https://www.coindesk.com/?_gl=1*v3vlyj*_up*MQ..*_ga*MTA4MTg5NzY1LjE3MjA2MTQ0Nzg.*_ga_VM3STRYVN8*MTcyMjMwNTY2OS4xMC4xLjE3MjIzMDcyMDQuMC4wLjU3MTY4MDIyNg..",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.coindesk.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-odaily-news-1",
                      "name": "Odaily\u661f\u7403\u65e5\u62a5 | \u4e13\u4e1a\u533a\u5757\u94fe\u4e0e\u52a0\u5bc6\u8d27\u5e01\u65b0\u95fb\u3001\u884c\u60c5\u5206\u6790\u4e0e\u6295\u8d44\u8d44\u8baf\u5e73\u53f0",
                      "url": "https://www.odaily.news/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.odaily.news",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-coinpedia-org-1",
                      "name": "Coinpedia - Fintech & Cryptocurrency News Media| Crypto Guide",
                      "url": "https://coinpedia.org/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "coinpedia.org",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-theblock-co-1",
                      "name": "the block",
                      "url": "https://www.theblock.co/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.theblock.co",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-m-weibo-cn-1",
                      "name": "\u67f3\u5927\u6ce2\u6d6a",
                      "url": "https://m.weibo.cn/u/1644724561?wm=3333_2001&from=10F1293010&sourcetype=weixin&s_trans=7101261740_&s_channel=4",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "m.weibo.cn",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-flowus-cn-1",
                      "name": "Web3\u533a\u522b\u5730",
                      "url": "https://flowus.cn/qubiedi/share/8827172d-31de-4486-8571-f1172cbe7fdd?code=UMMDMR",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "flowus.cn",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-investing-com-1",
                      "name": "Investing.com - \u80a1\u7968\u5e02\u573a\u884c\u60c5\u548c\u8d22\u7ecf\u65b0\u95fb",
                      "url": "https://www.investing.com/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.investing.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-reuters-com-1",
                      "name": "\u8def\u900f\u793e | \u7a81\u53d1\u56fd\u9645\u65b0\u95fb\u4e0e\u89c2\u70b9",
                      "url": "https://www.reuters.com/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.reuters.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-marketwatch-com-1",
                      "name": "MarketWatch\uff1a\u80a1\u5e02\u65b0\u95fb - \u8d22\u7ecf\u65b0\u95fb - MarketWatch",
                      "url": "https://www.marketwatch.com/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.marketwatch.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-forbes-com-1",
                      "name": "\u300a\u798f\u5e03\u65af\u300b",
                      "url": "https://www.forbes.com/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.forbes.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-hibor-com-cn-1",
                      "name": "\u6167\u535a\u6295\u7814\u8d44\u8baf-\u4e13\u4e1a\u7684\u6295\u8d44\u7814\u7a76\u62a5\u544a\u5927\u6570\u636e\u5e73\u53f0-\u514d\u8d39\u7684\u7814\u62a5\u5206\u4eab\u5e73\u53f0-\u6167\u535a\u8d44\u8baf",
                      "url": "https://www.hibor.com.cn/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.hibor.com.cn",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-xnews-jin10-com-1",
                      "name": "\u6211\u7684\u8ba2\u9605-\u6587\u7ae0-\u5e02\u573a\u53c2\u8003-\u91d1\u5341\u6570\u636e",
                      "url": "https://xnews.jin10.com/topic/group/my",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "xnews.jin10.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-polymarket-com-1",
                      "name": "Polymarket | The World's Largest Prediction Market",
                      "url": "https://polymarket.com/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "polymarket.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-worldmonitor-app-1",
                      "name": "\u4e16\u754c\u76d1\u6d4b - \u5b9e\u65f6\u5168\u7403\u60c5\u62a5\u4eea\u8868\u76d8",
                      "url": "https://worldmonitor.app/?lat=8.0000&lon=0.0000&zoom=1.00&view=global&timeRange=7d&layers=conflicts%2Cbases%2Chotspots%2Cnuclear%2Csanctions%2Cweather%2Ceconomic%2Cwaterways%2Coutages%2Cmilitary%2Cnatural",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "worldmonitor.app",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-pizzint-watch-1",
                      "name": "Polyglobe - \u5b9e\u65f6\u5730\u7f18\u653f\u6cbb\u5e02\u573a\u60c5\u62a5 | PizzINT",
                      "url": "https://www.pizzint.watch/polyglobe",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.pizzint.watch",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-wallstreetcn-com-1",
                      "name": "\u534e\u5c14\u8857\u89c1\u95fb",
                      "url": "https://wallstreetcn.com/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "wallstreetcn.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-reuters-com-2",
                      "name": "\u5168\u7403\u5e02\u573a\u5934\u6761 |  \u8def\u900f\u793e",
                      "url": "https://www.reuters.com/markets/",
                      "description": "\u6765\u6e90: \u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8",
                      "domain": "www.reuters.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u4ea4\u6613\u65b0\u95fb\u548c\u9ad8\u624b\u8ddf\u8e2a\u7c7b\u603b\u89c8"
                      ]
                  }
              ]
          },
          {
              "id": "general-\u5176\u4ed6\u603b\u89c8",
              "title": "\u5176\u4ed6\u603b\u89c8",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u5176\u4ed6\u603b\u89c8\u201d\u3002",
              "tools": [
                  {
                      "id": "general-fintel-io-1",
                      "name": "IBIT-\u76d1\u7ba1\u4fe1\u606f\u62ab\u9732\u5e73\u53f0",
                      "url": "https://fintel.io/so/us/ibit",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "fintel.io",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-ycharts-com-1",
                      "name": "GBTC \u6298\u4ef7\u6216\u6ea2\u4ef7\u81f3 NAV \u5206\u6790 | YCharts",
                      "url": "https://ycharts.com/stocks",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "ycharts.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-sec-gov-1",
                      "name": "SEC13F\u5b63\u5ea6\u6301\u4ed3",
                      "url": "https://www.sec.gov/edgar/search/",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.sec.gov",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-sec-gov-2",
                      "name": "SEC FORM 13-F Information Table",
                      "url": "https://www.sec.gov/Archives/edgar/data/1166588/000116658824000009/xslForm13F_X02/PBI13f03312024.xml",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.sec.gov",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-cmegroup-com-1",
                      "name": "CME",
                      "url": "https://www.cmegroup.com/tools-information/quikstrike/vol2vol-expected-range.html",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.cmegroup.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-cmegroup-com-2",
                      "name": "\u6295\u8d44\u8005\u6301\u4ed3\u62a5\u544a\u7528\u6237\u6307\u5357 - \u829d\u5546\u6240",
                      "url": "https://www.cmegroup.com/cn-s/tools-information/quikstrike/quikstrike-cftc-commitment-of-traders-report-user-guide.html",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.cmegroup.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-cftc-gov-1",
                      "name": "\u4ea4\u6613\u5458\u6301\u4ed3\u627f\u8bfa | CFTC",
                      "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.cftc.gov",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-spotgamma-com-1",
                      "name": "\u671f\u6743\u6df1\u5ea6\u5206\u6790--SpotGamma",
                      "url": "https://spotgamma.com/",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "spotgamma.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-simnow-com-cn-1",
                      "name": "\u671f\u8d27\u6a21\u62df\u4eff\u771f\u7cfb\u7edf--\u4e0a\u6d77\u671f\u8d27\u4ea4\u6613\u6240SimNow",
                      "url": "https://www.simnow.com.cn/",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.simnow.com.cn",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-p-pandaremit-com-1",
                      "name": "\u718a\u732b\u901f\u6c47",
                      "url": "https://p.pandaremit.com/h5activity/launchInvitationCode?countryCode=HKG&shareCode=MTE1NTQ4OTE%3D&lang=zh-hans",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "p.pandaremit.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-cftc-gov-2",
                      "name": "\u4ea4\u6613\u8005\u627f\u8bfa | CFTC",
                      "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm?utm_source=chatgpt.com",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.cftc.gov",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-chartexchange-com-1",
                      "name": "CFEGF\u80a1\u7968\u4ef7\u683c\u53ca\u56fe\u8868 | ChartExchange",
                      "url": "https://chartexchange.com/symbol/otc-cfegf/",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "chartexchange.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-tradingster-com-1",
                      "name": "COT\u62a5\u544a\uff1a\u7f8e\u5143\u6307\u6570COT\u56fe\u8868\uff08\u4ec5\u9650\u671f\u8d27\uff09- Tradingster",
                      "url": "https://www.tradingster.com/cot/futures/fin/098662",
                      "description": "\u6765\u6e90: \u5176\u4ed6\u603b\u89c8",
                      "domain": "www.tradingster.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u5176\u4ed6\u603b\u89c8"
                      ]
                  }
              ]
          },
          {
              "id": "general-\u884d\u751f\u54c1\u603b\u89c8",
              "title": "\u884d\u751f\u54c1\u603b\u89c8",
              "description": "\u6765\u81ea\u4f60\u6574\u7406\u540e\u7684 Markdown \u5206\u7ec4\u201c\u884d\u751f\u54c1\u603b\u89c8\u201d\u3002",
              "tools": [
                  {
                      "id": "general-www-openvlab-cn-1",
                      "name": "OpenVlab - \u4e13\u4e1a\u671f\u6743\u4ea4\u6613\u4e0e\u6ce2\u52a8\u7387\u5206\u6790\u5e73\u53f0",
                      "url": "https://www.openvlab.cn/",
                      "description": "\u6765\u6e90: \u884d\u751f\u54c1\u603b\u89c8",
                      "domain": "www.openvlab.cn",
                      "tags": [
                          "\u7efc\u5408",
                          "\u884d\u751f\u54c1\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-cboe-com-1",
                      "name": "\u829d\u52a0\u54e5\u671f\u6743\u4ea4\u6613\u6240\u5168\u7403\u5e02\u573a",
                      "url": "https://www.cboe.com/",
                      "description": "\u6765\u6e90: \u884d\u751f\u54c1\u603b\u89c8",
                      "domain": "www.cboe.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u884d\u751f\u54c1\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-bybit-com-1",
                      "name": "\u671f\u6743\u8ba1\u7b97\u5668",
                      "url": "https://www.bybit.com/trade/option/usdt/pb/BTC",
                      "description": "\u6765\u6e90: \u884d\u751f\u54c1\u603b\u89c8",
                      "domain": "www.bybit.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u884d\u751f\u54c1\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-www-theblock-co-2",
                      "name": "\u52a0\u5bc6\u671f\u6743\u672a\u5e73\u4ed3\u5408\u7ea6\u3001\u6210\u4ea4\u91cf\u548c\u9690\u542b\u6ce2\u52a8\u7387\u6570\u636e\u53ca\u56fe\u8868",
                      "url": "https://www.theblock.co/data/crypto-markets/options",
                      "description": "\u6765\u6e90: \u884d\u751f\u54c1\u603b\u89c8",
                      "domain": "www.theblock.co",
                      "tags": [
                          "\u7efc\u5408",
                          "\u884d\u751f\u54c1\u603b\u89c8"
                      ]
                  },
                  {
                      "id": "general-squeezemetrics-com-1",
                      "name": "sqzme | \u80a1\u7968\u6570\u636e\u7684\u65b0\u89c6\u89d2",
                      "url": "https://squeezemetrics.com/monitor",
                      "description": "\u6765\u6e90: \u884d\u751f\u54c1\u603b\u89c8",
                      "domain": "squeezemetrics.com",
                      "tags": [
                          "\u7efc\u5408",
                          "\u884d\u751f\u54c1\u603b\u89c8"
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
