import { ADVANCED_CHART_SCRIPT } from './tradingViewResources';

// The official embedding script creates its own iframe. Load it once per opened
// chart, directly in its host, rather than waiting for an unused head script.
export function mountTickerChart(
  host: HTMLElement,
  symbol: string,
  settled: (error?: string) => void,
): () => void {
  host.replaceChildren();
  const container = document.createElement('div');
  container.className = 'tradingview-widget-container';
  const widget = document.createElement('div');
  widget.className = 'tradingview-widget-container__widget';
  const script = document.createElement('script');
  script.async = true;
  script.src = ADVANCED_CHART_SCRIPT;
  script.text = JSON.stringify({
    autosize: true,
    symbol,
    interval: 'D',
    timezone: 'Asia/Shanghai',
    theme: 'light',
    style: '1',
    locale: 'zh_CN',
    allow_symbol_change: true,
    calendar: false,
    support_host: 'https://www.tradingview.com',
    hide_top_toolbar: false,
    hide_legend: false,
    save_image: false,
    details: false,
    studies: ['Volume@tv-basicstudies'],
    withdateranges: true,
    range: '30D',
    backgroundColor: '#f7fafc',
    gridColor: 'rgba(101, 119, 139, 0.12)',
  });
  let disposed = false;
  let finished = false;
  let frame: HTMLIFrameElement | null = null;
  const finish = (error?: string) => {
    if (disposed || finished) return;
    finished = true;
    clearTimeout(timer);
    observer.disconnect();
    settled(error);
  };
  const loaded = () => finish();
  const observer = new MutationObserver(() => {
    const nextFrame = container.querySelector('iframe');
    if (!nextFrame || nextFrame === frame) return;
    frame?.removeEventListener('load', loaded);
    frame = nextFrame;
    frame.addEventListener('load', loaded, { once: true });
  });
  const timer = setTimeout(() => finish('TradingView 加载超时，请关闭后重试'), 25_000);
  script.onerror = () => finish('TradingView 暂时无法连接，请关闭后重试');
  observer.observe(container, { childList: true, subtree: true });
  container.append(widget, script);
  host.appendChild(container);
  return () => {
    disposed = true;
    clearTimeout(timer);
    observer.disconnect();
    frame?.removeEventListener('load', loaded);
    script.onerror = null;
    host.replaceChildren();
  };
}
