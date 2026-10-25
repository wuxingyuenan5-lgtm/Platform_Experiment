const macroRanges: Record<string, number> = {
  netLiquidity: 3,
  nyfedRepo: 1,
  discountWindow: 3,
  fedBalance: 10,
  fedAssets: 10,
  treasuryYields: 1,
  rateCorridor: 0.25,
  corporateYields: 3,
  riskHighYieldOas: 1,
  riskInvestmentGradeOas: 1,
  jpTreasury: 1,
  realYield: 1,
  cnPolicyRates: 3,
  cnRates: 3,
  cnTreasury: 3,
  actualInflation: 3,
  upstreamInflation: 3,
  inflationNowcast: 3,
  inflationExpectations: 3,
  marketInflation: 1,
  vix: 1,
  riskCreditRatio: 1,
  cnRiskLeverage: 1,
  cnRiskVolatility: 1,
};

const commodityRanges: Record<string, number> = {
  wgcEtfWeekly: 1,
  wgcEtfMonthly: 1,
  spdrFlow: 1,
  spdrHoldings: 1,
  goldOpenInterest: 1,
  wgcCentralPurchases: 0,
};
const cryptoRanges: Record<string, number> = {
  fearGreed: 1,
  etfPremium: 1,
};

export function initialChartYears(group: string, domain: string, presentation: string): number {
  if (domain === 'macro') return macroRanges[group] ?? 5;
  const specified = domain === 'commodity' ? commodityRanges[group] : cryptoRanges[group];
  if (specified !== undefined) return specified;
  if (presentation === 'gold-drivers') return 1;
  if (group === 'coinbasePremium' || group === 'cnyUsdt' || group.startsWith('binanceCombined'))
    return 0.25;
  return 3;
}

const treasuryLabels: Record<string, string> = {
  us_treasury_3m: 'US03MY',
  us_treasury_2y: 'US2Y',
  us_treasury_5y: 'US5Y',
  us_treasury_10y: 'US10Y',
  us_treasury_30y: 'US30Y',
};
export function macroDisplayLabel(group: string, seriesId: string, original: string): string {
  if (group === 'usUnemployment' && seriesId === 'us_unrate') return '美国失业率';
  return group === 'treasuryYields' ? treasuryLabels[seriesId] ?? original : original;
}
