export const ADVANCED_CHART_SCRIPT =
  'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';

// Warm connections and the small official loader, never a hidden chart or datafeed.
// Browser preload/cache coalesces this with the script inserted by each widget.
export function prepareTradingView(scriptSrc = ADVANCED_CHART_SCRIPT): void {
  if (typeof document === 'undefined') return;
  for (const href of ['https://s3.tradingview.com', 'https://www.tradingview-widget.com']) {
    if (document.head.querySelector(`link[rel="preconnect"][href="${href}"]`)) continue;
    const link = document.createElement('link');
    link.rel = 'preconnect';
    link.href = href;
    document.head.appendChild(link);
  }
  if (!scriptSrc.startsWith('https://s3.tradingview.com/external-embedding/')) return;
  if (document.head.querySelector(`link[rel="preload"][href="${scriptSrc}"]`)) return;
  const link = document.createElement('link');
  link.rel = 'preload';
  link.as = 'script';
  link.href = scriptSrc;
  document.head.appendChild(link);
}
