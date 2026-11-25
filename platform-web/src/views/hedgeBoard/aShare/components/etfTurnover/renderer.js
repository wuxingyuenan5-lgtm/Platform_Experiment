// Adapted from the user-supplied tracker; fixed local template, local API only.
export function mountEtfTurnover(root, initial, request, options = {}) {
  let active = true,
    paused = false,
    redraw,
    refreshNow,
    scheduleNow;
  const timers = new Set();
  const document = { getElementById: (id) => root.querySelector('[id="' + id + '"]') };
  const notesLink = (event) => {
    if (!event.target.closest?.('a[href="#notes"]')) return;
    event.preventDefault();
    document.getElementById('notes')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  root.addEventListener('click', notesLink);
  const window = {};
  const setTimeout = (fn, ms) => {
    const id = globalThis.window.setTimeout(() => {
      timers.delete(id);
      if (active && !paused) fn();
    }, ms);
    timers.add(id);
    return id;
  };
  const clearTimeout = (id) => {
    globalThis.window.clearTimeout(id);
    timers.delete(id);
  };
  (function () {
    var S = initial.data;
    var metadata = initial.sources;
    if (!S) {
      document.getElementById('vtitle').textContent = '数据快照未加载';
      return;
    }
    var byCode = {};
    S.items.forEach(function (it) {
      byCode[it.code] = it;
    });
    var tcodes = S.items.map(function (it) {
      return it.tcode;
    });
    var liveOK = metadata.live?.status === 'ready',
      refreshing = false;
    // ---------- 时间 / 交易状态 ----------
    function bjParts() {
      var p = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Shanghai',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        weekday: 'short',
        hourCycle: 'h23',
      }).formatToParts(new Date());
      var o = {};
      p.forEach(function (x) {
        o[x.type] = x.value;
      });
      return o;
    }
    function marketState() {
      var b = bjParts(),
        wd = b.weekday;
      var weekend = wd === 'Sat' || wd === 'Sun';
      var h = parseInt(b.hour, 10),
        m = parseInt(b.minute, 10),
        t = h * 60 + m;
      var lunch = !weekend && t >= 690 && t < 780; // 11:30-13:00 午间休市
      var trading = !weekend && t >= 570 && t < 900;
      var preopen = !weekend && t >= 540 && t < 570; // 9:00-9:30
      var after = !weekend && t >= 900; // 收盘后
      var before = !weekend && t < 540; // 凌晨至 9:00
      var offhours = weekend || before || preopen;
      var prog;
      if (t < 570) prog = 0;
      else if (t <= 690) prog = (t - 570) / 240;
      else if (t < 780) prog = 120 / 240;
      else if (t < 900) prog = (120 + (t - 780)) / 240;
      else prog = 1;
      return {
        weekend: weekend,
        trading: trading,
        lunch: lunch,
        preopen: preopen,
        after: after,
        before: before,
        offhours: offhours,
        progress: Math.max(0.12, Math.min(1, prog)),
        date: b.year + b.month + b.day,
        hhmm: b.hour + ':' + b.minute,
        effHHMM:
          S.items[0]?.date === b.year + b.month + b.day && S.items[0]?.ts?.length === 14
            ? S.items[0].ts.slice(8, 10) + ':' + S.items[0].ts.slice(10, 12)
            : lunch
            ? '11:30'
            : b.hour + ':' + b.minute,
        weekday: wd,
      };
    }
    // ---------- 指标 ----------
    function calc(it) {
      var base = it.avg20_yi || 0,
        amt = it.amount_yi || 0;
      var oi = (it.outer_lots || 0) + (it.inner_lots || 0);
      return {
        ratio: base > 0 ? amt / base : 0,
        net: oi > 0 ? ((it.outer_lots - it.inner_lots) / oi) * amt : 0,
      };
    }
    // ---------- 同时点对齐 ----------
    // 盘中成交额只走完部分交易日，不能直接除「全天 20 日均额」。
    // 用历史日内累计成交额分布，查出「这个时点平均已走完全天的百分之几」，
    // 把分母同比例缩小，分子分母才可比。整个过程不含线性假设。
    function hhmm2min(s) {
      if (!s) return 0;
      var p = String(s).split(':');
      return (parseInt(p[0], 10) || 0) * 60 + (parseInt(p[1], 10) || 0);
    }
    function shapeAt(shape, hhmm) {
      if (!shape || !shape.length) return null;
      var n = shape.length,
        tx = hhmm2min(hhmm);
      if (tx <= hhmm2min(shape[0][0])) return shape[0][1];
      if (tx >= hhmm2min(shape[n - 1][0])) return shape[n - 1][1];
      for (var i = 1; i < n; i++) {
        var t1 = hhmm2min(shape[i][0]);
        if (tx <= t1) {
          var t0 = hhmm2min(shape[i - 1][0]);
          if (t1 <= t0) return shape[i][1];
          return shape[i - 1][1] + ((shape[i][1] - shape[i - 1][1]) * (tx - t0)) / (t1 - t0);
        }
      }
      return shape[n - 1][1];
    }
    // 该标的当前「已走完全天成交额的比例」；收盘/复盘为 1
    function dayProgress(it, st) {
      if (!st || !st.trading) return 1;
      var s = shapeAt(it.shape, st.effHHMM);
      if (s !== null && s > 0.02) return Math.min(1, s);
      return st.progress || 0.5; // 无形状数据时回退线性
    }
    function calcAdj(it, st) {
      var base = it.avg20_yi || 0,
        amt = it.amount_yi || 0;
      var p = dayProgress(it, st);
      var oi = (it.outer_lots || 0) + (it.inner_lots || 0);
      return {
        ratio: base > 0 && p > 0 ? amt / (base * p) : 0, // 同时点对齐后的倍数（可比）
        raw: base > 0 ? amt / base : 0, // 已达成日均的倍数（客观但不可比）
        done: p,
        net: oi > 0 ? ((it.outer_lots - it.inner_lots) / oi) * amt : 0,
      };
    }
    function fmt(n, d) {
      d = d === undefined ? 2 : d;
      return (n || 0).toLocaleString('zh-CN', {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      });
    }
    function signed(n) {
      return (n > 0 ? '+' : '') + fmt(n, 2);
    }
    function cls(n) {
      return n > 0 ? 'up' : n < 0 ? 'down' : 'muted';
    }
    function spark(hist) {
      if (!hist || !hist.length) return '';
      var vals = hist.map(function (x) {
        return x.amount_yi;
      });
      var mx = Math.max.apply(null, vals) || 1,
        w = 96,
        h = 26,
        bw = w / vals.length;
      var bars = vals
        .map(function (v, i) {
          var bh = Math.max(1.2, (v / mx) * h),
            last = i === vals.length - 1;
          return (
            '<rect x="' +
            (i * bw).toFixed(1) +
            '" y="' +
            (h - bh).toFixed(1) +
            '" width="' +
            Math.max(1.2, bw - 1).toFixed(1) +
            '" height="' +
            bh.toFixed(1) +
            '" fill="' +
            (last ? '#ff4713' : '#e0e0e0') +
            '"/>'
          );
        })
        .join('');
      return (
        '<svg class="spark" width="' +
        w +
        '" height="' +
        h +
        '" viewBox="0 0 ' +
        w +
        ' ' +
        h +
        '" aria-label="近30日成交额">' +
        bars +
        '</svg>'
      );
    }
    // ---------- 份额图表：每日份额变化 + 加仓指数 ----------
    // 数据源：S.shares_history（每日收盘后 update_data.py 记录，单位亿份，仅 core 20 只）
    // 加仓指数不用「25年报持仓÷当前份额」的比例口径：信披已停，期初持仓不可验证，
    // 且 2026 上半年大幅减持后比例锚定会严重失真。改用指数口径：区间首日=100。
    // 历史序列（2025-11 起）由韭圈 NeoData 场内基金份额接口回填，日期已与基金净值逐日核对。
    var RANGE = { delta: 242, index: 242 }; // 交易日根数：60/120/242（约 3 月 / 6 月 / 1 年）
    function seriesData(n) {
      var H = S.shares_history || {};
      var dates = Object.keys(H).sort();
      if (dates.length < 2) return null;
      var core = S.items
        .filter(function (i) {
          return i.group === 'core';
        })
        .map(function (i) {
          return i.code;
        });
      if (!core.length) core = Object.keys(H[dates[dates.length - 1]] || {});
      n = Math.max(8, Math.min(n || 242, dates.length - 1));
      // 窗口多带一天，用来算第一根柱子的差值；指数也从这个点起算 100
      var wd = dates.slice(Math.max(0, dates.length - 1 - n));
      var last = {},
        tot = [];
      // forward-fill：某日缺某只就用最近一次已知份额；从未出现过的标的不计入
      wd.forEach(function (d) {
        var row = H[d] || {};
        core.forEach(function (c) {
          if (row[c] !== undefined && row[c] !== null) last[c] = row[c];
        });
        var s = 0;
        core.forEach(function (c) {
          if (last[c] !== undefined) s += last[c];
        });
        tot.push(s);
      });
      var deltas = [];
      for (var i = 1; i < wd.length; i++) deltas.push({ date: wd[i], d: tot[i] - tot[i - 1] });
      var base = tot[0] || 1;
      var idx = wd.map(function (d, i) {
        return { date: d, v: (100 * tot[i]) / base };
      });
      return { dates: wd, deltas: deltas, idx: idx, bars: deltas.length };
    }
    function dShort(d) {
      return d && d.length === 8 ? d.slice(4, 6) + '-' + d.slice(6, 8) : d;
    }
    // 跨年时只写 月-日 会分不清年份，超过一年跨度改成 YY/MM
    function dAxis(d, big) {
      if (!d || d.length !== 8) return d;
      return big ? d.slice(2, 4) + '/' + d.slice(4, 6) : dShort(d);
    }
    function tray(box, tip, html, ev) {
      var rect = box.getBoundingClientRect();
      var px = (ev.touches && ev.touches[0] ? ev.touches[0].clientX : ev.clientX) - rect.left;
      var py = (ev.touches && ev.touches[0] ? ev.touches[0].clientY : ev.clientY) - rect.top;
      tipShow(box, tip, html, px, py);
    }
    function tipShow(box, tip, html, x, y) {
      tip.innerHTML = html;
      tip.style.display = 'block';
      var bw = box.clientWidth,
        tw = tip.offsetWidth;
      var left = Math.max(4, Math.min(bw - tw - 4, x - tw / 2));
      tip.style.left = left + 'px';
      tip.style.top = Math.max(0, y - tip.offsetHeight - 10) + 'px';
    }
    function niceMax(v) {
      if (v <= 0) return 1;
      var p = Math.pow(10, Math.floor(Math.log(v) / Math.LN10));
      for (var m of [1, 2, 2.5, 5, 10]) {
        if (m * p >= v) return m * p;
      }
      return 10 * p;
    }
    function axisY(v) {
      if (v === 0) return '0';
      return v >= 1000
        ? fmt(v / 1000, 1) + 'k'
        : fmt(v, Math.abs(v) < 1 ? 2 : Math.abs(v) < 10 ? 1 : 0);
    }
    function renderBarChart(data) {
      var box = document.getElementById('chartDelta'),
        tip = box.querySelector('.chart-tip');
      if (!data) {
        box.innerHTML =
          '<div class="chart-empty">份额快照还在积累<br>需要至少两个交易日的份额数据</div>';
        return;
      }
      var mob = box.clientWidth > 0 && box.clientWidth < 430;
      var W = mob ? 390 : 560,
        Hh = mob ? 200 : 232,
        pl = mob ? 40 : 48,
        pr = 10,
        pt = 16,
        pb = 26;
      var fs = mob ? 11 : 10,
        pw = W - pl - pr,
        ph = Hh - pt - pb;
      var big =
        data.deltas[0].date.slice(0, 4) !== data.deltas[data.deltas.length - 1].date.slice(0, 4);
      var vals = data.deltas.map(function (x) {
        return x.d;
      });
      var m = niceMax(Math.max.apply(null, vals.map(Math.abs)) || 1);
      var y0 = pt + ph / 2,
        sx = pw / data.deltas.length;
      var bw = Math.max(1, Math.min(34, sx * 0.62));
      var g = '';
      // 网格 + 刻度（对称五档）
      [m, m / 2, 0, -m / 2, -m].forEach(function (v) {
        var y = y0 - (v / m) * (ph / 2);
        g +=
          '<line x1="' +
          pl +
          '" y1="' +
          y.toFixed(1) +
          '" x2="' +
          (W - pr) +
          '" y2="' +
          y.toFixed(1) +
          '" stroke="' +
          (v === 0 ? '#d0d0d0' : '#efefef') +
          '" stroke-width="1"/>' +
          '<text x="' +
          (pl - 6) +
          '" y="' +
          (y + 3.5).toFixed(1) +
          '" text-anchor="end" font-size="' +
          fs +
          '" fill="#8a8a8a">' +
          axisY(v) +
          '</text>';
      });
      // x 轴日期（最多 8 个）
      var n = data.deltas.length,
        step = Math.ceil(n / (mob ? 4 : 7));
      data.deltas.forEach(function (x, i) {
        if (i % step !== 0 && i !== n - 1) return;
        g +=
          '<text x="' +
          (pl + sx * (i + 0.5)).toFixed(1) +
          '" y="' +
          (Hh - 8) +
          '" text-anchor="middle" font-size="' +
          fs +
          '" fill="#8a8a8a">' +
          dAxis(x.date, big) +
          '</text>';
      });
      // 柱（一年 240+ 根时退化成细柱直方图，仍能看出大额申购/赎回的尖峰）
      data.deltas.forEach(function (x, i) {
        var v = x.d,
          h = Math.max(bw >= 3 ? 1.5 : 0.8, (Math.abs(v) / m) * (ph / 2));
        var cx = pl + sx * (i + 0.5);
        g +=
          '<rect x="' +
          (cx - bw / 2).toFixed(1) +
          '" y="' +
          (v >= 0 ? y0 - h : y0).toFixed(1) +
          '" width="' +
          bw.toFixed(1) +
          '" height="' +
          h.toFixed(1) +
          '"' +
          (bw >= 3 ? ' rx="1.5"' : '') +
          ' fill="' +
          (v >= 0 ? '#ff4713' : '#00875a') +
          '"/>';
      });
      // 命中区（透明列）
      data.deltas.forEach(function (x, i) {
        g +=
          '<rect class="hit" data-i="' +
          i +
          '" x="' +
          (pl + sx * i).toFixed(1) +
          '" y="' +
          pt +
          '" width="' +
          sx.toFixed(1) +
          '" height="' +
          ph +
          '" fill="transparent" style="cursor:crosshair"/>';
      });
      var svg =
        '<svg viewBox="0 0 ' +
        W +
        ' ' +
        Hh +
        '" aria-label="每日份额变化">' +
        '<text x="6" y="10" font-size="' +
        fs +
        '" fill="#8a8a8a">亿份</text>' +
        g +
        '</svg>';
      box.innerHTML = svg;
      box.appendChild(tip);
      tip = box.querySelector('.chart-tip');
      box.querySelectorAll('.hit').forEach(function (r) {
        var i = +r.getAttribute('data-i'),
          x = data.deltas[i];
        function show(ev) {
          tray(
            box,
            tip,
            '<b>' +
              x.date.slice(0, 4) +
              '-' +
              dShort(x.date) +
              '</b><br>份额变化 <span class="' +
              (x.d >= 0 ? 'tu' : 'td') +
              '">' +
              signed(x.d) +
              ' 亿份</span>',
            ev,
          );
        }
        r.addEventListener('mousemove', show);
        r.addEventListener('touchstart', show, { passive: true });
        r.addEventListener('mouseleave', function () {
          tip.style.display = 'none';
        });
      });
    }
    function renderLineChart(data) {
      var box = document.getElementById('chartIndex'),
        tip = box.querySelector('.chart-tip');
      if (!data) {
        box.innerHTML = '<div class="chart-empty">至少需要两个交易日的份额快照</div>';
        return;
      }
      var mob = box.clientWidth > 0 && box.clientWidth < 430;
      var W = mob ? 390 : 560,
        Hh = mob ? 200 : 232,
        pl = mob ? 40 : 48,
        pr = mob ? 10 : 12,
        pt = 16,
        pb = 26;
      var fs = mob ? 11 : 10,
        pw = W - pl - pr,
        ph = Hh - pt - pb;
      var big = data.idx[0].date.slice(0, 4) !== data.idx[data.idx.length - 1].date.slice(0, 4);
      var vs = data.idx.map(function (x) {
        return x.v;
      });
      var lo = Math.min(100, Math.min.apply(null, vs)),
        hi = Math.max(100, Math.max.apply(null, vs));
      var pad = Math.max(0.6, (hi - lo) * 0.18);
      lo -= pad;
      hi += pad;
      function Y(v) {
        return pt + ((hi - v) / (hi - lo)) * ph;
      }
      function X(i) {
        return pl + (data.idx.length === 1 ? pw / 2 : (pw * i) / (data.idx.length - 1));
      }
      var g = '';
      // 网格 4 档
      for (var k = 0; k <= 4; k++) {
        var v = lo + ((hi - lo) * k) / 4,
          y = Y(v);
        g +=
          '<line x1="' +
          pl +
          '" y1="' +
          y.toFixed(1) +
          '" x2="' +
          (W - pr) +
          '" y2="' +
          y.toFixed(1) +
          '" stroke="#efefef"/>' +
          '<text x="' +
          (pl - 6) +
          '" y="' +
          (y + 3.5).toFixed(1) +
          '" text-anchor="end" font-size="' +
          fs +
          '" fill="#8a8a8a">' +
          fmt(v, 1) +
          '</text>';
      }
      // 100 基准虚线
      var yb = Y(100);
      g +=
        '<line x1="' +
        pl +
        '" y1="' +
        yb.toFixed(1) +
        '" x2="' +
        (W - pr) +
        '" y2="' +
        yb.toFixed(1) +
        '" stroke="#b0b0b0" stroke-dasharray="4 4"/>' +
        '<text x="' +
        (W - pr) +
        '" y="' +
        (yb - 5).toFixed(1) +
        '" text-anchor="end" font-size="' +
        fs +
        '" fill="#8a8a8a">基期 100</text>';
      // x 轴日期
      var n = data.idx.length,
        step = Math.ceil(n / (mob ? 4 : 7));
      data.idx.forEach(function (x, i) {
        if (i % step !== 0 && i !== n - 1) return;
        g +=
          '<text x="' +
          X(i).toFixed(1) +
          '" y="' +
          (Hh - 8) +
          '" text-anchor="middle" font-size="' +
          fs +
          '" fill="#8a8a8a">' +
          dAxis(x.date, big) +
          '</text>';
      });
      // 面积 + 折线
      var pts = data.idx
        .map(function (x, i) {
          return X(i).toFixed(1) + ',' + Y(x.v).toFixed(1);
        })
        .join(' ');
      var area =
        'M' +
        pl +
        ',' +
        Y(lo).toFixed(1) +
        ' L' +
        pts.replace(/ /g, ' L') +
        (' L' + X(n - 1).toFixed(1)) +
        ',' +
        Y(lo).toFixed(1) +
        ' Z';
      g += '<path d="' + area + '" fill="rgba(0,94,184,.08)"/>';
      g +=
        '<polyline points="' +
        pts +
        '" fill="none" stroke="#005eb8" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
      // 点：短周期逐个标点，一年期只保留末点避免糊成一条
      var dots =
        n <= 70
          ? data.idx.map(function (x, i) {
              return i;
            })
          : [n - 1];
      dots.forEach(function (i) {
        g +=
          '<circle cx="' +
          X(i).toFixed(1) +
          '" cy="' +
          Y(data.idx[i].v).toFixed(1) +
          '" r="3" fill="#005eb8" stroke="#fff" stroke-width="1.5"/>';
      });
      // 命中区
      data.idx.forEach(function (x, i) {
        g +=
          '<rect class="hit" data-i="' +
          i +
          '" x="' +
          (pl + (pw * i) / n).toFixed(1) +
          '" y="' +
          pt +
          '" width="' +
          (pw / n).toFixed(1) +
          '" height="' +
          ph +
          '" fill="transparent" style="cursor:crosshair"/>';
      });
      var svg =
        '<svg viewBox="0 0 ' +
        W +
        ' ' +
        Hh +
        '" aria-label="加仓指数">' +
        '<text x="6" y="10" font-size="' +
        fs +
        '" fill="#8a8a8a">指数</text>' +
        g +
        '</svg>';
      box.innerHTML = svg;
      box.appendChild(tip);
      tip = box.querySelector('.chart-tip');
      box.querySelectorAll('.hit').forEach(function (r) {
        var i = +r.getAttribute('data-i'),
          x = data.idx[i];
        var prev = i > 0 ? data.idx[i - 1].v : null;
        var diff = prev === null ? '' : (x.v - prev >= 0 ? ' +' : ' ') + fmt(x.v - prev, 2);
        function show(ev) {
          tray(
            box,
            tip,
            '<b>' +
              x.date.slice(0, 4) +
              '-' +
              dShort(x.date) +
              '</b><br>加仓指数 <b style="color:#005eb8">' +
              fmt(x.v, 2) +
              '</b>' +
              (diff
                ? '<br>较前日 <span class="' +
                  (x.v - prev >= 0 ? 'tu' : 'td') +
                  '">' +
                  diff +
                  '</span>'
                : ''),
            ev,
          );
        }
        r.addEventListener('mousemove', show);
        r.addEventListener('touchstart', show, { passive: true });
        r.addEventListener('mouseleave', function () {
          tip.style.display = 'none';
        });
      });
    }
    function renderCharts() {
      var bd = seriesData(RANGE.delta),
        ld = seriesData(RANGE.index);
      var dn = document.getElementById('chartDeltaNote'),
        en = document.getElementById('chartIndexNote');
      renderBarChart(bd);
      renderLineChart(ld);
      root
        .querySelectorAll('.chartbox svg')
        .forEach((el) => el.setAttribute('data-chart-kind', 'line'));
      options.onCharts?.();
      if (!bd) {
        dn.innerHTML = '';
        en.innerHTML = '';
        return;
      }
      var b0 = bd.dates[0],
        b1 = bd.dates[bd.dates.length - 1];
      var l0 = ld.dates[0],
        l1 = ld.dates[ld.dates.length - 1];
      dn.innerHTML =
        '<b>估算方法：</b>池内 20 只 ETF「当日场内份额 − 上一交易日份额」加总，正数计申购、负数计赎回；' +
        '区间 ' +
        b0 +
        ' ~ ' +
        b1 +
        '（' +
        bd.bars +
        ' 个交易日）。' +
        '日度份额变化<b>可能来自任何机构或个人投资者</b>，不能确认为特定机构操作；' +
        '沪市行情商份额存在未按日更新的情况（见表格脚注②），缺数期间本图偏低。此为近似推算，非官方披露数据。';
      en.innerHTML =
        '<b>估算方法：</b>加仓指数 = 100 × 当日池内总份额 ÷ 区间首日（' +
        l0 +
        '）总份额，区间 ' +
        l0 +
        ' ~ ' +
        l1 +
        '。' +
        '高于 100 = 这段区间估算净加仓，低于 100 = 净减仓。<b>不等于真实持仓比例</b>：历史名单不能验证当前持仓，' +
        '期初持仓不可验证，比例锚定会失真，故用指数刻画变化方向与幅度。' +
        '份额源未日更的交易日按前值顺延（不产生假跳变）。此为近似推算，非官方披露数据。';
    }
    // 时间范围切换
    function bindRange() {
      ['rngDelta', 'rngIndex'].forEach(function (id) {
        var box = document.getElementById(id);
        if (!box) return;
        var key = box.getAttribute('data-target');
        box.querySelectorAll('button').forEach(function (b) {
          b.addEventListener('click', function () {
            box.querySelectorAll('button').forEach(function (x) {
              x.classList.remove('on');
            });
            b.classList.add('on');
            RANGE[key] = +b.getAttribute('data-n');
            renderCharts();
          });
        });
      });
    }
    // ---------- 判断 ----------
    function verdict() {
      var st = marketState();
      // 盘中但数据日期不是今天 = 实时通道没拿到今日数据（快照是上一交易日全天值），
      // 此时不能按半天基准对齐（会把倍数凭空翻倍），退回全天对全天
      var stale = st.trading && S.items[0] && S.items[0].date && S.items[0].date !== st.date;
      var effSt = stale ? { trading: false, lunch: false, offhours: st.offhours } : st;
      var core = S.items.filter(function (i) {
        return i.group === 'core';
      });
      var sumAmt = 0,
        sumBase = 0,
        sumBaseAdj = 0,
        sumNet = 0,
        capW = 0,
        pctW = 0;
      var tailCur = 0,
        tailBase = 0,
        tailAmt = 0;
      core.forEach(function (it) {
        var c = calcAdj(it, effSt);
        sumAmt += it.amount_yi || 0;
        sumBase += it.avg20_yi || 0;
        sumBaseAdj += (it.avg20_yi || 0) * c.done; // 分母按历史同时点成交进度对齐
        sumNet += c.net;
        var w = it.mktcap_yi || 0;
        capW += w;
        pctW += (it.pct || 0) * w;
        if (
          it.tail_ratio !== null &&
          it.tail_ratio !== undefined &&
          it.tail_ratio_base !== null &&
          it.tail_ratio_base !== undefined
        ) {
          tailCur += (it.amount_yi || 0) * it.tail_ratio;
          tailBase += (it.amount_yi || 0) * it.tail_ratio_base;
          tailAmt += it.amount_yi || 0;
        }
      });
      var ratio = sumBaseAdj > 0 ? sumAmt / sumBaseAdj : 0; // 与「历史同时点均值」比，可比
      var rawRatio = sumBase > 0 ? sumAmt / sumBase : 0; // 已达成全天日均的倍数
      var done = sumBase > 0 ? sumBaseAdj / sumBase : 1; // 当前已走完全天的比例
      var wpct = capW > 0 ? pctW / capW : 0;
      var tail = tailAmt > 0 ? tailCur / tailAmt : 0;
      var tailB = tailAmt > 0 ? tailBase / tailAmt : 0;
      var level = 'cool',
        title = '',
        reason = '';
      if (ratio >= 1.8 && sumNet > 0) {
        level = 'hot';
        title = '大概率上班了';
        reason =
          '汪汪队池成交额达到历史同时点均值的 ' +
          fmt(ratio, 2) +
          ' 倍，且主动净买入 ' +
          fmt(sumNet, 1) +
          ' 亿元。放量 + 净买入同向，是典型的护盘量价特征。';
      } else if (ratio >= 1.3 && sumNet > 0) {
        level = 'mid';
        title = '有护盘迹象';
        reason =
          '成交额放大到历史同时点均值的 ' +
          fmt(ratio, 2) +
          ' 倍，主动净买入 ' +
          fmt(sumNet, 1) +
          ' 亿元，方向偏买，但力度还不构成强信号。';
      } else if (ratio >= 1.8 && sumNet <= 0) {
        level = 'mid';
        title = '放量了，方向不对';
        reason =
          '成交额放大到历史同时点均值的 ' +
          fmt(ratio, 2) +
          ' 倍，但主动净买入 ' +
          fmt(sumNet, 1) +
          ' 亿元。大额成交未必是买盘，更像换手或出货，不能直接算上班。';
      } else if (ratio >= 1.3) {
        level = 'mid';
        title = '成交活跃，证据不够';
        reason =
          '成交额达到历史同时点均值的 ' +
          fmt(ratio, 2) +
          ' 倍，但主动净买入 ' +
          fmt(sumNet, 1) +
          ' 亿元，方向不清晰。';
      } else {
        level = 'cool';
        title = '没看出上班迹象';
        reason =
          '成交额只有历史同时点均值的 ' +
          fmt(ratio, 2) +
          ' 倍，主动净买入 ' +
          fmt(sumNet, 1) +
          ' 亿元，量价都平静。';
      }
      if (tail > 0 && tailB > 0 && tail > tailB * 1.25 && (level === 'hot' || level === 'mid')) {
        reason +=
          ' 尾盘半小时成交占全天 ' +
          fmt(tail * 100, 1) +
          '%，明显高于 20 日均值 ' +
          fmt(tailB * 100, 1) +
          '%。';
      }
      if (wpct < -0.5 && (level === 'hot' || level === 'mid')) {
        reason += ' 池内规模加权涨跌 ' + fmt(wpct, 2) + '%，下跌日放量更符合护盘场景。';
      }
      if (stale)
        reason +=
          '（实时通道未连上，当前显示 ' +
          fmtDate(S.items[0].date) +
          ' 全天收盘数据，与全天基准直接对比；连上后自动切换同时点对齐）';
      else if (st.lunch)
        reason +=
          '（午间休市，成交额锁定 11:30；对比基准 = 20 日均额 × 历史同时点进度 ' +
          fmt(done * 100, 1) +
          '%）';
      else if (st.trading)
        reason +=
          '（' +
          st.effHHMM +
          ' 历史平均已走完全天 ' +
          fmt(done * 100, 1) +
          '%，分母已同比例缩小，与历史同时点均值对比）';
      else if (st.offhours)
        reason +=
          '（非交易时段，以上为 ' + fmtDate(S.trade_date) + ' 收盘复盘，开盘后自动切换实时）';
      return {
        st: st,
        core: core,
        sumAmt: sumAmt,
        sumBase: sumBase,
        sumBaseAdj: sumBaseAdj,
        sumNet: sumNet,
        ratio: ratio,
        rawRatio: rawRatio,
        done: done,
        wpct: wpct,
        tail: tail,
        tailB: tailB,
        level: level,
        title: title,
        reason: reason,
      };
    }
    function fmtDate(d) {
      if (!d || d.length !== 8) return d || '—';
      var wk = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
      var dt = new Date(
        parseInt(d.slice(0, 4), 10),
        parseInt(d.slice(4, 6), 10) - 1,
        parseInt(d.slice(6, 8), 10),
      );
      return d.slice(0, 4) + '-' + d.slice(4, 6) + '-' + d.slice(6, 8) + ' ' + wk[dt.getDay()];
    }
    function renderVerdict(v) {
      var el = document.getElementById('verdict');
      el.className = 'verdict ' + (v.level === 'hot' ? 'hot' : v.level === 'mid' ? 'mid' : '');
      document.getElementById('vlabel').textContent = v.st.lunch
        ? '今日结论 · 午间半场'
        : v.st.trading
        ? '今日结论 · 实时跟踪'
        : v.st.after
        ? '今日收盘复盘'
        : '最近交易日复盘 · ' + fmtDate(S.trade_date);
      var t = document.getElementById('vtitle');
      t.textContent = v.title;
      t.className = 'vtitle ' + (v.level === 'cool' ? 'cool' : '');
      document.getElementById('vreason').textContent = v.reason;
      var sn = document.getElementById('vstampNum');
      sn.textContent = fmt(v.ratio, 2) + '×';
      sn.className = 'num' + (v.ratio >= 1.8 ? ' hl' : '');
      document.getElementById('vstampLabel').textContent = v.st.trading
        ? '较同时点历史均值'
        : '较20日均额';
      var thr = document.getElementById('thRatio');
      if (thr) thr.textContent = v.st.trading ? '同时点倍数' : '较20日均';
      var pctCls = cls(v.wpct);
      var bars = Math.min(100, (v.ratio / 2.5) * 100);
      document.getElementById('mgrid').innerHTML =
        card(
          '汪汪队合计成交额',
          fmt(v.sumAmt, 1) + ' 亿',
          v.st.trading
            ? '截至 ' + v.st.effHHMM + ' · 已达成全天日均 ' + fmt(v.rawRatio, 2) + '×'
            : '20日均额 ' + fmt(v.sumBase, 1) + ' 亿',
          '',
        ) +
        card(
          '成交额放大倍数',
          fmt(v.ratio, 2) + '×',
          v.st.trading
            ? '基准 ' +
                fmt(v.sumBaseAdj, 1) +
                ' 亿 = 20日均额 × 同时点进度 ' +
                fmt(v.done * 100, 1) +
                '%'
            : '阈值 1.8× 为强信号',
          '<div class="bar"><span style="width:' + bars.toFixed(1) + '%"></span></div>',
        ) +
        card('合计主动净买入', signed(v.sumNet) + ' 亿', '主动买卖口径推算', '') +
        card(
          '池内加权涨跌',
          fmt(v.wpct, 2) + '%',
          '规模加权 · ' + fmtDate(S.items[0]?.date || S.trade_date),
          '',
        );
      var g = document.getElementById('mgrid');
      g.children[1].querySelector('.v').className = 'v num ' + (v.ratio >= 1.8 ? 'hl' : '');
      g.children[2].querySelector('.v').className = 'v num ' + cls(v.sumNet);
      g.children[3].querySelector('.v').className = 'v num ' + cls(v.wpct);
    }
    function card(k, v, n, extra) {
      return (
        '<div><div class="k">' +
        k +
        '</div><div class="v num">' +
        v +
        '</div><div class="n">' +
        n +
        '</div>' +
        extra +
        '</div>'
      );
    }
    // 份额变化：明确标出对比的是哪一天，0 不写成 +0.00（会被误读成有数据且为零）
    // 若同一市场绝大多数标的份额与昨日完全相同，判定为数据源未按日更新，不能当「无申赎」
    var __suspect = null;
    function sharesSuspect() {
      if (__suspect) return __suspect;
      var by = {};
      S.items.forEach(function (it) {
        var m = (it.tcode || '').slice(0, 2);
        (by[m] = by[m] || []).push(it);
      });
      var out = {};
      Object.keys(by).forEach(function (m) {
        var known = by[m].filter(function (x) {
          return x.subscr_net_yi !== null && x.subscr_net_yi !== undefined;
        });
        if (known.length < 3) return;
        var same = known.filter(function (x) {
          return Math.abs(x.subscr_net_yi) < 0.005;
        }).length;
        out[m] = same / known.length >= 0.7;
      });
      __suspect = out;
      return out;
    }
    function subscrCell(it) {
      var v = it.subscr_net_yi;
      if (v === null || v === undefined) return '<div class="sub muted">申赎 待积累</div>';
      var m = (it.tcode || '').slice(0, 2);
      if (sharesSuspect()[m])
        return '<div class="sub muted" title="同市场绝大多数标的份额与昨日完全相同，判断为行情商份额字段未按日更新，不代表当日没有申赎">份额源未日更</div>';
      var pd = S.prev_share_date;
      var tag = pd && pd.length === 8 ? pd.slice(4, 6) + '-' + pd.slice(6, 8) : '上日';
      if (Math.abs(v) < 0.005) return '<div class="sub muted">较' + tag + ' 持平</div>';
      return '<div class="sub num ' + cls(v) + '">较' + tag + ' ' + signed(v) + '亿</div>';
    }
    // ---------- 表格 ----------
    function renderTable() {
      var st = marketState();
      var stale = st.trading && S.items[0] && S.items[0].date && S.items[0].date !== st.date;
      var effSt = stale ? { trading: false } : st; // 实时未更新时不做同时点对齐
      var sort = document.getElementById('sort').value,
        scope = document.getElementById('scope').value;
      var q = document.getElementById('q').value.trim().toLowerCase();
      var list = S.items.filter(function (it) {
        if (scope !== 'all' && it.group !== scope) return false;
        if (q && (it.code + it.name + it.index).toLowerCase().indexOf(q) < 0) return false;
        return true;
      });
      var cmp = {
        huijin: function (a, b) {
          return b.huijin_yi - a.huijin_yi || b.mktcap_yi - a.mktcap_yi;
        },
        amount: function (a, b) {
          return b.amount_yi - a.amount_yi;
        },
        ratio: function (a, b) {
          return calcAdj(b, effSt).ratio - calcAdj(a, effSt).ratio;
        },
        net: function (a, b) {
          return calcAdj(b, effSt).net - calcAdj(a, effSt).net;
        },
        mktcap: function (a, b) {
          return b.mktcap_yi - a.mktcap_yi;
        },
      }[sort];
      // 分组固定：汪汪队在前；组内按所选排序
      list.sort(function (a, b) {
        if (a.group !== b.group) return a.group === 'core' ? -1 : 1;
        return cmp(a, b);
      });
      var html = '',
        lastGroup = '';
      list.forEach(function (it) {
        if (it.group !== lastGroup) {
          lastGroup = it.group;
          var label =
            it.group === 'core'
              ? '汪汪队重点关注 · 2025年报最后一次实名披露（此后停止披露）'
              : '扩展观察 · 2025年报未见汇金持仓（名单已停止更新）';
          var cnt = list.filter(function (x) {
            return x.group === it.group;
          }).length;
          html +=
            '<tr class="grouphead"><td colspan="10">' +
            label +
            '<span class="cnt">' +
            cnt +
            ' 只</span></td></tr>';
        }
        var c = calcAdj(it, effSt),
          pctCls = cls(it.pct),
          netCls = cls(c.net);
        var rCls = c.ratio >= 1.8 ? 'hl' : c.ratio >= 1.3 ? '' : 'muted';
        var hb = Math.min(100, (c.ratio / 3) * 100);
        var amtSub = st.trading ? '<div class="sub muted">截至 ' + st.effHHMM + '</div>' : '';
        var ratioSub = st.trading
          ? '<div class="sub muted">已达成日均 ' + fmt(c.raw, 2) + '×</div>'
          : '';
        html +=
          '<tr>' +
          '<td><div class="name">' +
          it.name +
          '<span class="chip ' +
          it.group +
          '">' +
          (it.group === 'core' ? '汪汪队' : '观察') +
          '</span></div>' +
          '<div class="code num">' +
          it.code +
          '</div></td>' +
          '<td class="muted">' +
          it.index +
          '</td>' +
          '<td class="num">' +
          fmt(it.mktcap_yi, 1) +
          '</td>' +
          '<td class="num" style="font-weight:700">' +
          fmt(it.amount_yi, 2) +
          amtSub +
          '</td>' +
          '<td><div class="ratio num ' +
          rCls +
          '">' +
          fmt(c.ratio, 2) +
          '<b>×</b></div>' +
          ratioSub +
          '<div class="mini"><span style="width:' +
          hb.toFixed(1) +
          '%"></span></div></td>' +
          '<td class="num ' +
          netCls +
          '" style="font-weight:700">' +
          signed(c.net) +
          '</td>' +
          '<td class="num ' +
          pctCls +
          '" style="font-weight:700">' +
          signed(it.pct) +
          '%</td>' +
          '<td><div class="num">' +
          fmt(it.shares_yi, 1) +
          '</div>' +
          subscrCell(it) +
          '</td>' +
          '<td>' +
          spark(it.hist) +
          '</td>' +
          '<td class="num ' +
          (it.huijin_yi ? '' : 'muted') +
          '">' +
          (it.huijin_yi ? fmt(it.huijin_yi, 1) : '—') +
          '</td>' +
          '</tr>';
      });
      // 合计行
      var core = S.items.filter(function (i) {
        return i.group === 'core';
      });
      if (st.trading && S.items[0]?.date !== st.date) st = { ...st, trading: false };
      var sa = 0,
        sb = 0,
        sn = 0;
      core.forEach(function (it) {
        var c = calcAdj(it, st);
        sa += it.amount_yi;
        sb += (it.avg20_yi || 0) * c.done;
        sn += c.net;
      });
      html +=
        '<tr class="total"><td>汪汪队合计</td><td class="muted">' +
        core.length +
        ' 只</td><td class="muted">—</td>' +
        '<td class="num">' +
        fmt(sa, 2) +
        (st.trading ? '<div class="sub muted">截至 ' + st.effHHMM + '</div>' : '') +
        '</td>' +
        '<td class="num hl">' +
        fmt(sb > 0 ? sa / sb : 0, 2) +
        '×</td>' +
        '<td class="num ' +
        cls(sn) +
        '">' +
        signed(sn) +
        '</td><td colspan="4" class="muted" style="text-align:right">合计口径与上方判断一致</td></tr>';
      document.getElementById('tbody').innerHTML = html;
    }
    async function refresh() {
      if (refreshing || !active || paused || globalThis.document.hidden) return;
      refreshing = true;
      var btn = document.getElementById('refresh');
      btn.textContent = '读取中…';
      try {
        var next = await request();
        if (!active || paused) return;
        if (!next.data) throw new Error('成交额跟踪快照暂不可用');
        S = next.data;
        metadata = next.sources;
        __suspect = null;
        liveOK = metadata.live?.status === 'ready';
        options.onError?.('');
      } catch (error) {
        liveOK = false;
        if (active && !paused) options.onError?.('成交额跟踪读取失败，保留已有数据');
      } finally {
        refreshing = false;
        if (active && !paused) {
          btn.textContent = '立即刷新';
          renderAll();
        }
      }
    }
    // ---------- 状态栏 ----------
    function renderStatus() {
      var v = verdict(),
        st = v.st;
      var badge = document.getElementById('badge'),
        txt = document.getElementById('badgeText');
      if (st.lunch) {
        badge.className = 'badge' + (liveOK ? ' live' : ' warn');
        txt.textContent = '午间休市 · 数据锁定 11:30';
      } else if (st.trading) {
        badge.className = 'badge' + (liveOK ? ' live' : ' warn');
        txt.textContent = liveOK ? '行情正常 · 每60秒读取' : '行情待更新 · 保留快照';
      } else if (st.preopen) {
        badge.className = 'badge';
        txt.textContent = '等待开盘 · 9:30';
      } else if (st.after) {
        badge.className = 'badge';
        txt.textContent = '收盘快照 · ' + fmtDate(S.items[0]?.date || S.trade_date);
      } else {
        badge.className = 'badge';
        txt.textContent = '休市 · 最近交易日收盘数据';
      }
      document.getElementById('stamp').textContent =
        '快照 ' + fmtDate(S.trade_date) + ' · 生成 ' + S.generated_at;
      var newest = S.items[0] && S.items[0].date ? S.items[0].date : S.trade_date;
      var stale = newest && newest !== st.date && (st.trading || st.after);
      document.getElementById('meta').innerHTML =
        '数据时间 ' +
        (S.items[0] && S.items[0].ts
          ? S.items[0].ts.replace(/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/, '$1-$2-$3 $4:$5:$6')
          : '—') +
        (liveOK ? (st.lunch ? ' · 通道正常，13:00 继续刷新' : ' · 实时已连接') : '') +
        (stale ? ' <span style="color:var(--orange)">· 行情尚未更新到当前交易日</span>' : '') +
        (metadata.baseline?.status !== 'ready' ? ' · 历史基准更新异常，保留原值' : '');
      document.getElementById('footerSign').textContent =
        '数据来源：腾讯行情；历史基准与份额序列沿用参考站；名单为2025年报历史标签 · 快照生成 ' +
        S.generated_at +
        ' · 仅供内部研究，不构成投资建议';
    }
    var historyVersion = '';
    function renderAll() {
      renderVerdict(verdict());
      renderTable();
      renderStatus();
      var revision = JSON.stringify(S.shares_history);
      if (revision !== historyVersion) {
        historyVersion = revision;
        renderCharts();
      }
    }
    redraw = renderCharts;
    refreshNow = refresh;
    scheduleNow = schedule;
    // ---------- 事件 ----------
    ['sort', 'scope', 'q'].forEach(function (id) {
      document.getElementById(id).addEventListener(id === 'q' ? 'input' : 'change', renderTable);
    });
    document.getElementById('refresh').addEventListener('click', refresh);
    document.getElementById('auto').addEventListener('change', function () {
      if (this.checked) schedule();
      else clearTimeout(window.__t);
    });
    function schedule() {
      clearTimeout(window.__t);
      var st = marketState();
      var ms = 60000;
      window.__t = setTimeout(function () {
        if (document.getElementById('auto').checked) refresh();
        schedule();
      }, ms);
    }
    bindRange();
    renderAll();

    schedule();
  })();
  const observer = new ResizeObserver(() => {
    if (active && !paused) redraw?.();
  });
  observer.observe(root);
  const visibility = () => {
    if (!globalThis.document.hidden && active && !paused) void refreshNow?.();
  };
  globalThis.document.addEventListener('visibilitychange', visibility);
  const dispose = () => {
    active = false;
    timers.forEach((id) => globalThis.window.clearTimeout(id));
    timers.clear();
    observer.disconnect();
    root.removeEventListener('click', notesLink);
    globalThis.document.removeEventListener('visibilitychange', visibility);
  };
  dispose.pause = () => {
    paused = true;
    timers.forEach((id) => globalThis.window.clearTimeout(id));
    timers.clear();
  };
  dispose.resume = () => {
    paused = false;
    void refreshNow?.();
    scheduleNow?.();
  };
  return dispose;
}
