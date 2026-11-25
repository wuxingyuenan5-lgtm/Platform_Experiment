const test = require('node:test');
const assert = require('node:assert/strict');
const createLoader = require('./load-strategy-module.cjs');

function fixture() {
  const previous = { document: global.document, MutationObserver: global.MutationObserver };
  const elements = [];
  class Element {
    constructor(tag) {
      this.tag = tag;
      this.children = [];
      this.listeners = new Map();
      elements.push(this);
    }
    replaceChildren() {
      this.children = [];
    }
    append(...nodes) {
      this.children.push(...nodes);
    }
    appendChild(node) {
      this.append(node);
    }
    querySelector(tag) {
      return this.children.find((node) => node.tag === tag) || null;
    }
    addEventListener(event, listener) {
      this.listeners.set(event, listener);
    }
    removeEventListener(event) {
      this.listeners.delete(event);
    }
  }
  let observer;
  global.document = { createElement: (tag) => new Element(tag) };
  global.MutationObserver = class {
    constructor(callback) {
      this.callback = callback;
      observer = this;
    }
    observe() {
      this.active = true;
    }
    disconnect() {
      this.active = false;
    }
  };
  const { mountTickerChart } = createLoader()('src/views/hedgeBoard/components/tickerChart.ts');
  const host = new Element('host');
  const results = [];
  const dispose = mountTickerChart(host, 'SSE:000300', (error) => results.push(error || 'ready'));
  return {
    elements,
    host,
    results,
    frame() {
      const frame = new Element('iframe');
      host.children[0].append(frame);
      observer.callback();
      return frame;
    },
    close() {
      dispose();
      Object.assign(global, previous);
    },
  };
}

test('one configured embed loads in the modal and settles only when its iframe loads', () => {
  const f = fixture();
  try {
    const scripts = f.elements.filter((node) => node.tag === 'script');
    assert.equal(scripts.length, 1);
    assert.equal(JSON.parse(scripts[0].text).symbol, 'SSE:000300');
    assert.deepEqual(f.results, []);
    const frame = f.frame();
    frame.listeners.get('load')();
    assert.deepEqual(f.results, ['ready']);
    scripts[0].onerror();
    assert.deepEqual(f.results, ['ready']);
  } finally {
    f.close();
  }
});

test('closing while loading detaches the iframe and suppresses late completion', () => {
  const f = fixture();
  const frame = f.frame();
  const lateLoad = frame.listeners.get('load');
  f.close();
  lateLoad();
  assert.deepEqual(f.host.children, []);
  assert.deepEqual(f.results, []);
  assert.equal(frame.listeners.has('load'), false);
});

test('transport failure is visible instead of an endless loading indicator', () => {
  const f = fixture();
  try {
    f.elements.find((node) => node.tag === 'script').onerror();
    assert.match(f.results[0], /TradingView.*无法连接/);
  } finally {
    f.close();
  }
});
