/* Learn Pi — 页面交互
 * 主题切换 / 站内搜索（中文子串匹配）/ 右侧目录高亮 / 代码复制 / 移动端目录
 */
(function () {
  'use strict';

  var root = document.body.dataset.root || '';
  var THEME_KEY = 'learnpi-theme';

  /* ---------- 主题：system -> light -> dark ---------- */
  function applyTheme(mode) {
    var dark = mode === 'dark' || (mode === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', dark);
    try { localStorage.setItem(THEME_KEY, mode); } catch (e) {}
  }

  document.querySelectorAll('[data-theme]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var current;
      try { current = localStorage.getItem(THEME_KEY) || 'system'; } catch (e) { current = 'system'; }
      var next = current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system';
      applyTheme(next);
    });
  });

  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    var mode;
    try { mode = localStorage.getItem(THEME_KEY) || 'system'; } catch (e) { mode = 'system'; }
    if (mode === 'system') applyTheme('system');
  });

  /* ---------- 移动端目录 ---------- */
  var side = document.getElementById('side');
  document.querySelectorAll('[data-menu]').forEach(function (btn) {
    btn.addEventListener('click', function () { side && side.classList.toggle('is-open'); });
  });
  if (side) {
    side.addEventListener('click', function (event) {
      if (event.target.closest('a')) side.classList.remove('is-open');
    });
  }

  /* ---------- 右侧目录滚动高亮 ---------- */
  var outlineLinks = Array.prototype.slice.call(document.querySelectorAll('.outline a'));
  if (outlineLinks.length) {
    var targets = outlineLinks
      .map(function (link) { return document.getElementById(link.getAttribute('href').slice(1)); })
      .filter(Boolean);
    var ticking = false;
    var sync = function () {
      ticking = false;
      var current = 0;
      for (var i = 0; i < targets.length; i++) {
        if (targets[i].getBoundingClientRect().top <= 120) current = i;
      }
      outlineLinks.forEach(function (link, i) { link.classList.toggle('is-active', i === current); });
    };
    addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(sync);
    }, { passive: true });
    sync();
  }

  /* ---------- 代码复制 ---------- */
  document.querySelectorAll('.doc pre').forEach(function (pre) {
    var code = pre.querySelector('code');
    if (!code) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy-btn';
    btn.textContent = '复制';
    btn.addEventListener('click', function () {
      var done = function () {
        btn.textContent = '已复制';
        btn.classList.add('is-done');
        setTimeout(function () { btn.textContent = '复制'; btn.classList.remove('is-done'); }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(code.innerText).then(done, function () {});
      } else {
        var range = document.createRange();
        range.selectNodeContents(code);
        var selection = getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        try { document.execCommand('copy'); done(); } catch (e) {}
        selection.removeAllRanges();
      }
    });
    pre.appendChild(btn);
  });

  /* ---------- 站内搜索 ---------- */
  var overlay = document.querySelector('.search');
  var input = overlay && overlay.querySelector('.search-input');
  var listBox = overlay && overlay.querySelector('.search-results');
  var index = null;
  var results = [];
  var cursor = 0;

  function openSearch() {
    if (!overlay) return;
    overlay.hidden = false;
    document.body.style.overflow = 'hidden';
    input.value = '';
    render('');
    input.focus();
    ensureIndex();
  }

  function closeSearch() {
    if (!overlay) return;
    overlay.hidden = true;
    document.body.style.overflow = '';
  }

  function ensureIndex() {
    if (index) return;
    fetch(root + 'search-index.json')
      .then(function (response) { return response.json(); })
      .then(function (data) { index = data; render(input.value); })
      .catch(function () { index = []; });
  }

  function normalize(text) {
    return String(text).toLowerCase().replace(/\s+/g, ' ');
  }

  function search(query) {
    if (!index || !query) return [];
    var needle = normalize(query);
    var scored = [];
    for (var i = 0; i < index.length; i++) {
      var entry = index[i];
      var title = normalize(entry.t);
      var heading = normalize(entry.h);
      var body = normalize(entry.x);
      var score = 0;
      if (title.indexOf(needle) !== -1) score += 60;
      if (heading.indexOf(needle) !== -1) score += 40;
      if (body.indexOf(needle) !== -1) score += 12;
      if (!score) continue;
      scored.push({ entry: entry, score: score, at: body.indexOf(needle) });
    }
    scored.sort(function (a, b) { return b.score - a.score; });
    return scored.slice(0, 12);
  }

  function highlight(text, query) {
    if (!query) return text;
    var at = normalize(text).indexOf(normalize(query));
    if (at === -1) return text;
    return text.slice(0, at) + '<mark>' + text.slice(at, at + query.length) + '</mark>' + text.slice(at + query.length);
  }

  function render(query) {
    if (!listBox) return;
    if (!index) {
      listBox.innerHTML = '<div class="search-hint">正在载入索引…</div>';
      return;
    }
    results = search(query);
    cursor = 0;
    if (!query) {
      listBox.innerHTML = '<div class="search-hint">输入关键词，支持中文直接匹配</div>';
      return;
    }
    if (!results.length) {
      listBox.innerHTML = '<div class="search-hint">没有找到「' + query + '」相关内容</div>';
      return;
    }
    listBox.innerHTML = results.map(function (item, i) {
      var entry = item.entry;
      return '<a class="search-item' + (i === 0 ? ' is-cursor' : '') + '" role="option" href="' + entry.u + '">' +
        '<div class="search-item-group">' + entry.g + (entry.h ? ' · ' + entry.h : '') + '</div>' +
        '<div class="search-item-title">' + highlight(entry.t, query) + '</div>' +
        '<div class="search-item-text">' + highlight(entry.x.slice(Math.max(0, item.at - 40), item.at + 120), query) + '</div>' +
        '</a>';
    }).join('');
  }

  function moveCursor(step) {
    if (!results.length) return;
    cursor = (cursor + step + results.length) % results.length;
    var items = listBox.querySelectorAll('.search-item');
    items.forEach(function (item, i) { item.classList.toggle('is-cursor', i === cursor); });
    items[cursor].scrollIntoView({ block: 'nearest' });
  }

  document.querySelectorAll('[data-search]').forEach(function (btn) {
    btn.addEventListener('click', openSearch);
  });
  overlay && overlay.addEventListener('click', function (event) {
    if (event.target.closest('[data-close]')) closeSearch();
  });
  addEventListener('keydown', function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      overlay && overlay.hidden ? openSearch() : closeSearch();
      return;
    }
    if (event.key === 'Escape' && overlay && !overlay.hidden) closeSearch();
  });
  input && input.addEventListener('input', function () { render(input.value.trim()); });
  input && input.addEventListener('keydown', function (event) {
    if (event.key === 'ArrowDown') { event.preventDefault(); moveCursor(1); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); moveCursor(-1); }
    else if (event.key === 'Enter' && results[cursor]) {
      event.preventDefault();
      window.location.href = results[cursor].entry.u;
    }
  });
})();
