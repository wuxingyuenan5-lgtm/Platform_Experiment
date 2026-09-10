export function nativeAmount(value: string | null | undefined, currency?: string | null) {
  return value == null ? '--' : `${value} ${currency || '币种待核对'}`;
}

export function fillOriginLabel(origin: string | undefined, source?: string | null) {
  const label =
    origin === 'venue_execution'
      ? '原生成交'
      : origin === 'runtime_confirmation'
      ? '执行回执（原生明细待齐）'
      : '历史来源待核对';
  return source ? `${label} · ${source}` : label;
}

export function settlementLabel(kind: string) {
  const labels: Record<string, string> = {
    funding: '资金费',
    swap: '库存费',
    fee: '手续费',
    realized_pnl: '已实现损益',
  };
  return labels[kind] || kind;
}
