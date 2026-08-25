import axios, { type AxiosInstance } from 'axios';

const apiBaseUrl = import.meta.env.VITE_PLATFORM_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const platformApiToken = import.meta.env.VITE_PLATFORM_API_TOKEN || '';

const client: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10_000,
  headers: {
    'Content-Type': 'application/json',
    ...(platformApiToken ? { Authorization: `Bearer ${platformApiToken}` } : {}),
  },
});

export interface FundingSymbolOption {
  baseAsset: string;
  quoteCurrency: string;
  perpetualSymbol: string;
  spotSymbol: string;
  perpetualInstrumentId: string;
  spotInstrumentId: string;
}

export interface FundingExecutionContext {
  accountId: string;
  venue: string;
  spotSymbol: string;
  perpetualSymbol: string;
  symbolOptions: FundingSymbolOption[];
  spotQuote: Record<string, unknown>;
  perpetualQuote: Record<string, unknown>;
  fundingRate?: string | null;
  nextFundingTime?: string | null;
  basis?: string | null;
  tickSize: Record<string, string>;
  quantityStep: Record<string, string>;
  minimumQuantity: Record<string, string>;
  contractMultiplier: Record<string, string>;
  suggestedQuantity?: string | null;
  requestedNotional?: string | null;
  availableBalance?: Record<string, unknown> | null;
  activeReservation: {
    currency: string;
    activeReserved: string;
    fundingReserved: string;
    crossReserved: string;
    fundingAvailable?: string | null;
  };
  sharedResourceClaims: Array<Record<string, unknown>>;
  controlledLiveReadiness: Record<string, unknown>;
  runtime: Record<string, unknown>;
  dataQualityState: string;
  asOf: string;
}

export interface FundingWorkspaceResponse {
  instruction: Record<string, unknown>;
  executionBatch?: Record<string, unknown> | null;
  workspaceState: Record<string, unknown>;
}

export interface FundingPositionGroup {
  instructionId: string;
  openInstructionId: string;
  batchId: string;
  status: string;
  perpetualSymbol: string;
  spotSymbol: string;
  perpetualSide: string;
  spotSide: string;
  hedgedQuantity: string;
  residualQuantity: string;
  alreadyClosedQuantity?: string | null;
  authoritativeClosedQuantity?: string | null;
  pendingCloseQuantity?: string | null;
  resultUnknownReservedQuantity?: string | null;
  remainingClosableQuantity?: string | null;
  lifecycleState: 'active' | 'history';
  fundingFees?: string | null;
  fees?: string | null;
  pnl?: string | null;
  asOf: string;
  workspaceState?: Record<string, unknown> | null;
}

export async function getFundingExecutionContext(params?: {
  perpetualSymbol?: string;
  spotSymbol?: string;
  notional?: string;
}): Promise<FundingExecutionContext> {
  const response = await client.get<FundingExecutionContext>('/trading/funding/execution-context', {
    params,
  });
  return response.data;
}

export async function getFundingPositionGroups(
  scope: 'active' | 'history' | 'all' = 'all',
): Promise<FundingPositionGroup[]> {
  const response = await client.get<FundingPositionGroup[]>('/trading/funding/positions', {
    params: { scope },
  });
  return response.data;
}

export async function submitFundingInstruction(input: {
  action: 'open' | 'close';
  idempotencyKey: string;
  perpetualSymbol: string;
  spotSymbol: string;
  quantity: string;
  targetOpenInstructionId?: string;
}): Promise<FundingWorkspaceResponse> {
  const response = await client.post<FundingWorkspaceResponse>(
    '/trading/funding/instructions',
    input,
  );
  return response.data;
}

export async function getFundingInstructionWorkspace(
  instructionId: string,
): Promise<FundingWorkspaceResponse> {
  const response = await client.get<FundingWorkspaceResponse>(
    `/trading/funding/instructions/${encodeURIComponent(instructionId)}`,
  );
  return response.data;
}

export async function getFundingInstructionWorkspaceByIdempotency(
  idempotencyKey: string,
): Promise<FundingWorkspaceResponse> {
  const response = await client.get<FundingWorkspaceResponse>('/trading/funding/instructions', {
    params: { idempotencyKey },
  });
  return response.data;
}
