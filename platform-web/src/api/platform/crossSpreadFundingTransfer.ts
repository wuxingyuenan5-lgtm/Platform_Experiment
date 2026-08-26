import axios, { type AxiosInstance } from 'axios';

export type FundingTransferDirection = 'bybit_to_mt5' | 'mt5_to_bybit';
export type FundingTransferStatus = 'pending' | 'completed' | 'failed' | 'result_unknown';

export interface FundingBalanceQuote {
  amount: string | null;
  currency: string;
  dataQualityState: 'complete' | 'unavailable';
  asOf: string | null;
  reason?: string | null;
}

export interface FundingTransferQuoteResult {
  strategyInstanceId: string;
  bybitTransferable: FundingBalanceQuote;
  mt5Withdrawable: FundingBalanceQuote;
  suggestedDirection: FundingTransferDirection | null;
  suggestedAmount: string | null;
  mode: 'automated' | 'assisted';
  officialFundingUrl: string;
  asOf: string;
}

export interface InternalCapitalTransferResult {
  transferId: string;
  idempotencyKey: string;
  strategyInstanceId: string;
  direction: FundingTransferDirection;
  currency: string;
  amount: string;
  status: FundingTransferStatus;
  externalTransferId: string | null;
  failureReason: string | null;
  requestedBy: string;
  mode: 'automated' | 'assisted';
  officialFundingUrl: string;
  currentLocation: 'bybit_uta' | 'funding' | 'mt5' | 'unknown';
  createdAt: string;
  updatedAt: string;
}

const apiBaseUrl = import.meta.env.VITE_PLATFORM_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const platformApiToken = import.meta.env.VITE_PLATFORM_API_TOKEN || '';

const client: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    ...(platformApiToken ? { Authorization: `Bearer ${platformApiToken}` } : {}),
  },
});

export async function getFundingTransferQuote(): Promise<FundingTransferQuoteResult> {
  const response = await client.get<FundingTransferQuoteResult>(
    '/trading/cross-spread/funding-transfer/quote',
  );
  return response.data;
}

export async function createFundingTransfer(input: {
  idempotencyKey: string;
  direction: FundingTransferDirection;
  amount: string;
}): Promise<InternalCapitalTransferResult> {
  const response = await client.post<InternalCapitalTransferResult>(
    '/trading/cross-spread/funding-transfer',
    input,
  );
  return response.data;
}

export async function getFundingTransfer(
  transferId: string,
): Promise<InternalCapitalTransferResult> {
  const response = await client.get<InternalCapitalTransferResult>(
    `/trading/cross-spread/funding-transfers/${encodeURIComponent(transferId)}`,
  );
  return response.data;
}

export async function cancelFundingTransfer(
  transferId: string,
): Promise<InternalCapitalTransferResult> {
  const response = await client.post<InternalCapitalTransferResult>(
    `/trading/cross-spread/funding-transfers/${encodeURIComponent(transferId)}/cancel`,
  );
  return response.data;
}
