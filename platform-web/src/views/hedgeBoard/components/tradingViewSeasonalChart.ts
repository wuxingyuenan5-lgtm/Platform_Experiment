const SCRIPT_SRC = 'https://widgets.tradingview-widget.com/w/en/tv-seasonal-chart.js';

let scriptPromise: Promise<void> | null = null;

export function ensureTradingViewSeasonalScript(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('TradingView 组件仅支持浏览器环境'));
  }
  if (customElements.get('tv-seasonal-chart')) return Promise.resolve();
  if (scriptPromise) return scriptPromise;

  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[data-tv-seasonal-chart="true"]',
    );
    const script = existing ?? document.createElement('script');
    if (!existing) {
      script.type = 'module';
      script.src = SCRIPT_SRC;
      script.async = true;
      script.dataset.tvSeasonalChart = 'true';
      document.head.appendChild(script);
    }
    const timeout = window.setTimeout(() => reject(new Error('TradingView 组件加载超时')), 15000);
    script.addEventListener(
      'load',
      () => {
        window.clearTimeout(timeout);
        customElements
          .whenDefined('tv-seasonal-chart')
          .then(() => resolve())
          .catch(reject);
      },
      { once: true },
    );
    script.addEventListener(
      'error',
      () => {
        window.clearTimeout(timeout);
        reject(new Error('TradingView 组件脚本加载失败'));
      },
      { once: true },
    );
    if (customElements.get('tv-seasonal-chart')) {
      window.clearTimeout(timeout);
      resolve();
    }
  });

  return scriptPromise;
}
