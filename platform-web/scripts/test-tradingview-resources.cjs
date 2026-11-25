const test = require('node:test');
const assert = require('node:assert/strict');
const createLoader = require('./load-strategy-module.cjs');

test('resource preparation deduplicates connections and preloads without executing hidden widgets', () => {
  const previous = global.document;
  const links = [];
  global.document = {
    createElement(tag) {
      return { tag };
    },
    head: {
      appendChild(link) {
        links.push(link);
      },
      querySelector(selector) {
        return links.find((link) => selector === `link[rel="${link.rel}"][href="${link.href}"]`);
      },
    },
  };
  try {
    const { prepareTradingView, ADVANCED_CHART_SCRIPT } = createLoader()(
      'src/views/hedgeBoard/components/tradingViewResources.ts',
    );
    prepareTradingView();
    prepareTradingView();
    assert.equal(links.filter((link) => link.rel === 'preconnect').length, 2);
    assert.equal(links.filter((link) => link.rel === 'preload').length, 1);
    assert.equal(links.find((link) => link.rel === 'preload').href, ADVANCED_CHART_SCRIPT);
    prepareTradingView('https://s3.tradingview.com/external-embedding/embed-widget-events.js');
    assert.equal(links.filter((link) => link.rel === 'preload').length, 2);
    assert.ok(links.every((link) => link.tag === 'link'));
  } finally {
    global.document = previous;
  }
});
