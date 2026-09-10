import { createStrategyApi, strategyData } from './strategyApi';
import type { components } from './generated/strategy';

export type FundingTransferDirection = 'bybit_to_mt5' | 'mt5_to_bybit';
export type FundingTransferStatus = 'pending' | 'completed' | 'failed' | 'result_unknown';

export type FundingBalanceQuote = components['schemas']['FundingBalanceQuote'];

export type FundingTransferQuoteResult = components['schemas']['FundingTransferQuoteResponse'];

export type InternalCapitalTransferResult =
  components['schemas']['InternalCapitalTransferResponse'];

const api = createStrategyApi(30_000);

export async function getFundingTransferQuote(): Promise<FundingTransferQuoteResult> {
  const response = await api.GET('/api/v1/trading/cross-spread/funding-transfer/quote');
  return strategyData(response);
}

export async function createFundingTransfer(input: {
  idempotencyKey: string;
  direction: FundingTransferDirection;
  amount: string;
}): Promise<InternalCapitalTransferResult> {
  const response = await api.POST('/api/v1/trading/cross-spread/funding-transfer', { body: input });
  return strategyData(response);
}

export async function getFundingTransfer(
  transferId: string,
): Promise<InternalCapitalTransferResult> {
  const response = await api.GET('/api/v1/trading/cross-spread/funding-transfers/{transfer_id}', {
    params: { path: { transfer_id: transferId } },
  });
  return strategyData(response);
}
