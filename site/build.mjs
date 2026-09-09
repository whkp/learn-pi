#!/usr/bin/env node
/**
 * Learn Pi 站点生成器
 *
 * docs/ 仍是唯一事实源：读取 docs 目录下的 Markdown，改写仓库内链接为 GitHub 地址，
 * 渲染成静态 HTML，输出到 dist/。
 *
 * 设计目标：Apple 风格的教程站 —— 浅灰底、渐变强调色、卡片化导航、
 * 中文友好的站内搜索（直接做子串匹配，而不是英文分词）。
 *
 * 用法：
 *   node site/build.mjs           # 构建
 *   node site/build.mjs --serve   # 构建并启动本地预览（默认 http://localhost:4173）
 */
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, rm, readdir, stat, copyFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DOCS = path.join(ROOT, 'docs');
const DIST = path.join(ROOT, 'dist');
const GITHUB_BLOB = 'https://github.com/whkp/learn-pi/blob/main';

/* ------------------------------------------------------------------ *
 * 站点结构（与 scripts/build_site.py 保持同一份事实）
 * ------------------------------------------------------------------ */
const GROUPS = [
  {
    key: 'intro', label: '入门', num: '00',
    desc: '先看懂课程怎么读，再决定从哪条路线进入。',
    items: [['00-course-map.md', '课程地图', '课程结构、四条阅读路线、三阶段学习路径与验收标准。']],
  },
  {
    key: 'stage1', label: '阶段一 · 架构与核心机制', num: '01',
    desc: '先建立整体心智模型：谁在循环里，谁在循环外。',
    items: [
      ['01-architecture/README.md', '架构总览', 'Pi 的分层、最小 Agent 闭环与 Planning/Memory 的承担者。'],
      ['02-agent-loop/README.md', 'Agent Loop', '循环如何驱动模型工作：Trace 与 Turn、终止条件。'],
      ['03-tools/README.md', '工具系统', 'schema + executor、注册表分发、软约束与硬闸门。'],
      ['04-messages-and-memory/README.md', '消息与记忆', '对话历史如何组织与传递，工具结果成对回填。'],
      ['04b-system-prompt/README.md', '系统提示词', '五段拼装、customPrompt 与默认路径、三级回退链。'],
    ],
  },
  {
    key: 'stage2', label: '阶段二 · 状态与边界', num: '02',
    desc: '状态存在哪一层？出错时边界画在哪里？',
    items: [
      ['05-sessions/README.md', '会话管理', 'JSONL v3、append-only 的会话树、认父不认子。'],
      ['06-events-and-extensions/README.md', '事件驱动与扩展', '事件即契约：subscribe 与 pi.on 的分水岭。'],
      ['07-context-and-compaction/README.md', '上下文压缩', '窗口即预算：压缩是让模型总结它自己。'],
    ],
  },
  {
    key: 'stage3', label: '阶段三 · 集成与实践', num: '03',
    desc: '把前面所有边界接起来，做成能跑、能测的东西。',
    items: [
      ['08-providers-and-models/README.md', 'Provider 与模型', '元数据、协议、认证三者分离与 models.json。'],
      ['09-reliability/README.md', '可靠性', '先分类再重试、指数退避必封顶、错误隔离。'],
      ['10-protocol-and-integration/README.md', '协议与集成', 'stdout 是协议：JSONL 分帧、粘包与半包。'],
      ['11-projects-and-evaluation/README.md', '实战与评测', '四个离线 mini-project 与同一条质量链。'],
    ],
  },
  {
    key: 'appendix', label: '附录', num: '04',
    desc: '回查用的参考资料。',
    items: [
      ['glossary.md', '术语表', 'Pi 基线、当前 Pi 行为、Python 教学模型等关键术语。'],
      ['code-tour.md', '核心代码导览', '九个核心机制的精选片段与逐段解读，对应 Pi 源码符号。'],
      ['pi-source-map.md', 'Pi 源码映射', '固定基线 0.85.1 的源码入口与常见误解对照。'],
    ],
  },
];

const STATS = [
  ['12', '主题章节'],
  ['12', '离线实验'],
  ['4', '实战项目'],
  ['131', '单元测试'],
];

const ROUTES = [
  ['概念', '按章节顺序读', '从架构总览到实战评测，一条线理解 Pi 的核心设计。', '01-architecture/README.md'],
  ['实验', '直接跑离线 Lab', 'python3 -m learn_pi_lab lab agent-loop，先跑起来再补机制。', '00-course-map.md'],
  ['源码', '按 Pi 源码追踪', '以源码映射为索引，逐个断言回溯到固定基线位置。', 'pi-source-map.md'],
  ['构建', '从裸 API 写 Harness', 'examples/harness 十二步连续编码主线，B01–B06 已完成。', '00-course-map.md'],
];

// 只保留「有功能」的图标：搜索 / 外链 / 主题 / 菜单 / 跳转。
// 章节语义图标（罗盘·图层·盾牌·插头·书）一律不用——它们不传递信息，
// 只是填满版面的装饰，是最典型的生成式页面指纹。
const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  github: '<path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.6 9.6 0 0 1 5 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 0 12 2Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/>',
  moon: '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>',
  arrow: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
};

/* ------------------------------------------------------------------ *
 * 工具函数
 * ------------------------------------------------------------------ */
const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const md = new MarkdownIt({
  html: true,
  // 不能开 linkify：.md 是真实存在的国家顶级域，`usage.md` 这类文件名会被
  // 自动加上 http:// 前缀，反而制造死链。
  linkify: false,
  highlight(code, lang) {
    const name = String(lang || '').trim().split(/\s+/)[0];
    if (name && hljs.getLanguage(name)) {
      try {
        return hljs.highlight(code, { language: name, ignoreIllegals: true }).value;
      } catch { /* 落到默认转义 */ }
    }
    return '';
  },
});

/** md 文件路径 -> 站点内相对根的 URL */
function siteUrl(mdPath) {
  const dir = path.posix.dirname(mdPath.split(path.sep).join('/'));
  const base = path.posix.basename(mdPath);
  return base === 'README.md' ? `${dir}/` : `${dir === '.' ? '' : `${dir}/`}${base.replace(/\.md$/, '.html')}`;
}

/** 由页面 URL 推导回到站点根的相对前缀 */
function rootPrefix(url) {
  return url.endsWith('/') ? '../'.repeat(url.split('/').filter(Boolean).length) : '';
}

function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[\s]+/g, '-')
    .replace(/[^\p{L}\p{N}\-_]/gu, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '') || 'section';
}

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...(await walk(full)));
    else out.push(full);
  }
  return out;
}

/* ------------------------------------------------------------------ *
 * Markdown 处理
 * ------------------------------------------------------------------ */
const REPO_LINK = /\.\.\/(?:\.\.\/)?(learn_pi_lab|projects|scripts|tests|examples)\/[A-Za-z0-9_./-]+/g;
const DOC_LINK = /href="([^"#]+\.md)(#[^"]*)?"/g;

/** 把相对 .md 链接改写成站点内 URL；仓库源码链接指向 GitHub */
function rewriteLinks(html, sourceMd) {
  const sourceDir = path.posix.dirname(sourceMd.split(path.sep).join('/'));
  return html.replace(DOC_LINK, (whole, href, hash = '') => {
    if (/^(https?:)?\/\//.test(href) || href.startsWith('/')) return whole;
    const resolved = path.posix.normalize(path.posix.join(sourceDir === '.' ? '' : `${sourceDir}/`, href));
    // 跳出 docs/ 的仓库文件（如 ../examples/harness/...）不在站点内，交给 REPO_LINK 处理
    if (resolved.startsWith('..')) return whole;
    if (!existsSync(path.join(DOCS, resolved))) return whole;
    // 基准必须是「源 md 所在目录」。不能用 siteUrl 的页面 URL 再 dirname：
    // 目录 URL 带尾斜杠（'02-agent-loop/'），posix.dirname 会返回 '.'，
    // 导致 relative 从站点根起算，正文互链全部变成 './03-tools' 这类 404。
    const fromDir = sourceMd.includes('/') ? sourceMd.split('/').slice(0, -1).join('/') : '.';
    const to = siteUrl(resolved);
    let rel = path.posix.relative(fromDir, to.replace(/\/$/, ''));
    // 指向目录页（README 渲染成 index.html）时补回尾斜杠，省一次服务端跳转
    const isDirPage = resolved.endsWith('/README.md') || existsSync(path.join(DOCS, resolved, 'index.html'));
    if (!rel.endsWith('.html') && isDirPage) {
      rel += '/';
    }
    return `href="${rel.startsWith('.') ? rel : `./${rel}`}${hash}"`;
  }).replace(REPO_LINK, (match) => `${GITHUB_BLOB}/${match.replace(/^(\.\.\/)+/, '')}`);
}

/** 给标题加 id，并给特定小节打语义色 */
const SECTION_TINT = {
  边界与安全: 'danger',
  验证方式: 'warn',
  'Python 实验': 'lab',
  '当前 Pi 行为': 'lab',
};

function decorateHeadings(html) {
  const used = new Map();
  // 只处理 markdown 生成的标题（行首），避免碰到首页卡片里的 <h3>
  return html.replace(/(^|\n)(<h([2-4])>)([\s\S]*?)<\/h\3>/g, (whole, lead, _open, level, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim();
    let id = slugify(text);
    const seen = used.get(id) ?? 0;
    used.set(id, seen + 1);
    if (seen) id = `${id}-${seen}`;
    const tint = level === '2' && SECTION_TINT[text] ? ` data-tint="${SECTION_TINT[text]}"` : '';
    return `${lead}<h${level} id="${id}"${tint}>${inner}</h${level}>`;
  });
}

function collectOutline(html) {
  const out = [];
  const re = /<h([23]) id="([^"]+)"[^>]*>([\s\S]*?)<\/h\1>/g;
  for (const match of html.matchAll(re)) {
    out.push({ level: Number(match[1]), id: match[2], text: match[3].replace(/<[^>]+>/g, '').trim() });
  }
  return out;
}

/** 供搜索用的纯文本（去标签、压空白） */
function plainText(html) {
  return html
    .replace(/<(pre|code)[^>]*>[\s\S]*?<\/\1>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;|&#\d+;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/* ------------------------------------------------------------------ *
 * 页面模板
 * ------------------------------------------------------------------ */
function icon(name, size = 20, extraClass = '') {
  const cls = extraClass ? `i ${extraClass}` : 'i';
  return `<svg class="${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] ?? ''}</svg>`;
}

function navLinks(currentUrl) {
  const entries = [
    ['首页', 'index.html', /^index\.html?$|^$/],
    ['课程地图', siteUrl('00-course-map.md'), /^00-course-map\.html?$/],
    ['阶段一', siteUrl('01-architecture/README.md'), /^01-architecture\/|^02-agent-loop\/|^03-tools\/|^04-messages-and-memory\//],
    ['阶段二', siteUrl('05-sessions/README.md'), /^05-sessions\/|^06-events-and-extensions\/|^07-context-and-compaction\//],
    ['阶段三', siteUrl('08-providers-and-models/README.md'), /^08-providers-and-models\/|^09-reliability\/|^10-protocol-and-integration\/|^11-projects-and-evaluation\//],
    ['源码映射', siteUrl('pi-source-map.md'), /^pi-source-map\.html?$/],
  ];
  const active = currentUrl.replace(/^\.\//, '');
  return entries
    .map(([label, target, pattern]) => {
      const isActive = new RegExp(pattern).test(active);
      const href = `${rootPrefix(currentUrl)}${target}`;
      return `<a class="nav-link${isActive ? ' is-active' : ''}" href="${href}">${label}</a>`;
    })
    .join('');
}

function sidebar(currentUrl) {
  const active = currentUrl.replace(/^\.\//, '');
  return GROUPS.map((group) => {
    const items = group.items
      .map(([file, title]) => {
        const url = siteUrl(file);
        const isActive = active === url || active === `${url}index.html`;
        return `<a class="side-item${isActive ? ' is-active' : ''}" href="${rootPrefix(currentUrl)}${url}">${title}</a>`;
      })
      .join('');
    return `<div class="side-group"><div class="side-label">${group.label}</div>${items}</div>`;
  }).join('');
}

function outlineHtml(entries) {
  if (entries.length < 3) return '';
  const items = entries
    .map((entry) => `<li class="lvl-${entry.level}"><a href="#${entry.id}">${escapeHtml(entry.text)}</a></li>`)
    .join('');
  return `<nav class="outline" aria-label="本页目录"><div class="outline-label">本页目录</div><ul>${items}</ul></nav>`;
}

function footNav(index) {
  const flat = GROUPS.flatMap((group) => group.items.map(([file, title]) => [file, title]));
  const prev = index > 0 ? flat[index - 1] : null;
  const next = index < flat.length - 1 ? flat[index + 1] : null;
  const cell = (item, dir) =>
    item
      ? `<a class="foot-card" href="${rootPrefix(siteUrl(item[0]))}${siteUrl(item[0])}"><span class="foot-label">${dir}</span><span class="foot-title">${item[1]} ${icon('arrow', 15)}</span></a>`
      : '<span class="foot-card is-empty"></span>';
  return `<div class="foot-nav">${cell(prev, '上一章')}${cell(next, '下一章')}</div>`;
}

function shell({ url, title, description, kicker, body, extraHead = '' }) {
  const root = rootPrefix(url);
  const isHome = url === 'index.html' || url === '';
  return `<!DOCTYPE html>
<html lang="zh-CN"${isHome ? ' data-home' : ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title>
<meta name="description" content="${escapeHtml(description)}">
<meta property="og:type" content="website">
<meta property="og:title" content="${escapeHtml(title)}">
<meta property="og:description" content="${escapeHtml(description)}">
<meta name="theme-color" content="#fafafa" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0a0a0a" media="(prefers-color-scheme: dark)">
<link rel="icon" href="${root}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="${root}assets/style.css">
${extraHead}
<script>
(function(){try{var t=localStorage.getItem('learnpi-theme');if(t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme: dark)').matches)||!t&&matchMedia('(prefers-color-scheme: dark)').matches){document.documentElement.classList.add('dark')}}catch(e){}})();
</script>
</head>
<body data-root="${root}">
<a class="skip" href="#main">跳到正文</a>
<header class="nav">
  <div class="nav-inner">
    <a class="brand" href="${root}index.html">Learn<span class="brand-accent">Pi</span></a>
    <nav class="nav-links" aria-label="主导航">${navLinks(url)}</nav>
    <div class="nav-tools">
      <button class="tool-btn" type="button" data-search aria-label="搜索 (Ctrl+K)">${icon('search', 17)}</button>
      <a class="tool-btn" href="https://github.com/whkp/learn-pi" target="_blank" rel="noopener" aria-label="GitHub 仓库">${icon('github', 17)}</a>
      <button class="tool-btn" type="button" data-theme aria-label="切换深浅色">${icon('sun', 17, 'icon-sun')}${icon('moon', 17, 'icon-moon')}</button>
      <button class="tool-btn only-mobile" type="button" data-menu aria-label="打开目录">${icon('menu', 18)}</button>
    </div>
  </div>
</header>
<div class="layout">
  <aside class="side" id="side" aria-label="课程目录">${sidebar(url)}</aside>
  <main class="main" id="main">${body}</main>
  <div class="outline-slot"></div>
</div>
${isHome ? '' : `<script type="application/json" class="search-page"></script>`}
<div class="search" hidden>
  <div class="search-mask" data-close></div>
  <div class="search-panel" role="dialog" aria-modal="true" aria-label="站内搜索">
    <div class="search-bar">${icon('search', 18)}<input class="search-input" type="search" placeholder="搜索章节、机制、术语…" autocomplete="off" spellcheck="false"><kbd>Esc</kbd></div>
    <div class="search-results" role="listbox"></div>
    <div class="search-foot"><span><kbd>↵</kbd> 打开</span><span><kbd>↑</kbd><kbd>↓</kbd> 切换</span><span><kbd>Esc</kbd> 关闭</span></div>
  </div>
</div>
<script src="${root}assets/app.js" defer></script>
</body>
</html>`;
}

/* ------------------------------------------------------------------ *
 * 首页
 * ------------------------------------------------------------------ */
function chapterCard([file, title, desc], index) {
  const num = String(index).padStart(2, '0');
  return `<a class="card" href="${siteUrl(file)}">
    <div class="card-top"><span class="card-num">${num}</span><span class="card-rule"></span></div>
    <h3 class="card-title">${title}</h3>
    <p class="card-desc">${desc}</p>
  </a>`;
}

function buildHome() {
  const stageBlocks = GROUPS.filter((group) => group.key !== 'intro')
    .map((group) => {
      const startNum = group.key === 'stage1' ? 1 : group.key === 'stage2' ? 6 : 9;
      const cards = group.items.map((item, i) => chapterCard(item, startNum + i)).join('');
      return `<section class="block"><header class="block-head">
          <p class="block-eyebrow"><span>Part ${group.num}</span>${group.items.length} 章</p>
          <h2 class="block-title">${group.label}</h2>
          <p class="block-desc">${group.desc}</p>
        </header><div class="grid grid-4">${cards}</div></section>`;
    })
    .join('');

  const routes = ROUTES.map(([tag, title, desc]) => `<a class="route" href="${siteUrl('00-course-map.md')}">
      <span class="route-tag">${tag}</span>
      <h3 class="route-title">${title}</h3>
      <p class="route-desc">${desc}</p>
    </a>`).join('');

  const stats = STATS.map(([n, label]) => `<div class="stat"><dt class="stat-num">${n}</dt><dd class="stat-label">${label}</dd></div>`).join('');

  const body = `
  <section class="hero">
    <p class="hero-eyebrow">开源课程 · 离线可复现 · 固定 Pi 基线 0.85.1</p>
    <h1 class="hero-title">读懂编码智能体的<br><em>Harness</em> 工程</h1>
    <p class="hero-lead">智能来自模型，<strong>能力边界全部来自 harness</strong>。以 Pi 为蓝本，用可运行的 Python 实验和固定基线源码，讲清编码 Agent 的每一层机制——从最小闭环 agent = LLM + tool use，到记忆、上下文、会话、权限与协议。</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="${siteUrl('01-architecture/README.md')}">开始学习 ${icon('arrow', 16)}</a>
      <a class="btn btn-ghost" href="https://github.com/whkp/learn-pi" target="_blank" rel="noopener">${icon('github', 16)} GitHub</a>
    </div>
    <dl class="stats">${stats}</dl>
  </section>

  <section class="block"><header class="block-head">
      <p class="block-eyebrow"><span>Routes</span>四条</p>
      <h2 class="block-title">按目的进入</h2>
      <p class="block-desc">按目的选入口，不必从第一页顺着读。</p>
    </header><div class="grid grid-4">${routes}</div></section>

  ${stageBlocks}

  <section class="cta">
    <h2 class="cta-title">先跑起来，再补机制</h2>
    <p class="cta-desc">全部实验只依赖 Python 标准库：不访问网络、不调用模型、不执行你提供的 shell 命令。</p>
    <pre class="cta-code"><code>python3 -m learn_pi_lab lab agent-loop</code></pre>
  </section>`;

  return shell({
    url: 'index.html',
    title: 'Learn Pi — 编码智能体的 Harness 工程课',
    description: '面向开发者的 Pi 编码智能体学习仓库：准确资料、可运行的 Python 实验、自动化测试与离线实战项目。',
    kicker: '首页',
    body,
  });
}

/* ------------------------------------------------------------------ *
 * 文档页
 * ------------------------------------------------------------------ */
async function buildDoc(file, index) {
  const mdPath = path.join(DOCS, file);
  const raw = await readFile(mdPath, 'utf8');

  const titleMatch = raw.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : path.basename(file, '.md');
  // 移除首个 H1 行。注意不能用 `.+`：文件是 CRLF 行尾时，`.+` 无法匹配 `\r`，
  // `/^#\s+.+\n/` 会失配，导致 H1 残留、正文出现两个 `<h1>`。
  // `[^\n]*` 能吃掉 `\r`，`(?:\r?\n)?` 对 LF / CRLF / 无尾换行都成立。
  // `#\s` 保证不误伤 `##` 小节；只替换首个匹配，H1 位于文件开头。
  const bodyMd = raw.replace(/^#\s[^\n]*(?:\r?\n)?/m, '');

  let html = md.render(bodyMd);
  html = rewriteLinks(html, file);
  html = decorateHeadings(html);
  html = html.replace(/<table>/g, '<div class="table-wrap"><table>').replace(/<\/table>/g, '</table></div>');
  html = html.replace(/<pre><code class="language-([\w+#-]+)">/g, '<pre data-lang="$1"><code class="language-$1">');

  const group = GROUPS.find((g) => g.items.some(([f]) => f === file));
  const outline = collectOutline(html);
  const url = siteUrl(file);
  const docTitle = `${title} · Learn Pi`;

  const page = shell({
    url,
    title: docTitle,
    description: plainText(html).slice(0, 150),
    kicker: group?.label ?? '',
    body: `<article class="doc">
      <header class="doc-head">
        <p class="kicker">${group?.label ?? ''}</p>
        <h1 class="doc-title">${escapeHtml(title)}</h1>
      </header>
      ${html}
      ${footNav(index)}
    </article>`,
  });

  return { url, html: page, outline };
}

/* ------------------------------------------------------------------ *
 * 搜索索引（中文用子串匹配，英文按词）
 * ------------------------------------------------------------------ */
async function buildSearchIndex() {
  const entries = [];
  for (const group of GROUPS) {
    for (const [file, title] of group.items) {
      const raw = await readFile(path.join(DOCS, file), 'utf8');
      const rendered = md.render(raw.replace(REPO_LINK, (m) => `${GITHUB_BLOB}/${m.replace(/^(\.\.\/)+/, '')}`));
      const html = decorateHeadings(rendered);
      const pageUrl = siteUrl(file);
      const root = rootPrefix(pageUrl);

      const sections = html.split(/<h2[^>]*>/).slice(1);
      const chunks = [{ h: '', text: plainText(rendered.split(/<h2[^>]*>/)[0]) }];
      for (const section of sections) {
        // split 已经吃掉了 <h2 ...> 开标签，段首直接就是标题文本
        const heading = plainText(section.match(/^([\s\S]*?)<\/h2>/)?.[1] ?? '');
        chunks.push({ h: heading, text: plainText(section) });
      }
      for (const chunk of chunks) {
        if (chunk.text.length < 12) continue;
        entries.push({ u: `${root}${pageUrl}`, t: title, h: chunk.h, g: group.label, x: chunk.text.slice(0, 900) });
      }
    }
  }
  return entries;
}

/* ------------------------------------------------------------------ *
 * 静态资源
 * ------------------------------------------------------------------ */
const FAVICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#007aff"/><stop offset="1" stop-color="#5856d6"/></linearGradient></defs>
<rect width="64" height="64" rx="15" fill="url(#g)"/>
<text x="32" y="44" font-family="Georgia,serif" font-size="38" font-style="italic" font-weight="700" fill="#fff" text-anchor="middle">π</text>
</svg>`;

async function copyAssets() {
  const assets = path.join(DIST, 'assets');
  await mkdir(assets, { recursive: true });
  for (const name of ['style.css', 'app.js', 'favicon.svg']) {
    await writeFile(path.join(assets, name), await readFile(path.join(ROOT, 'site', 'assets', name), 'utf8'));
  }
  const docAssets = path.join(DOCS, 'assets');
  if (existsSync(docAssets)) {
    for (const file of await readdir(docAssets)) {
      await copyFile(path.join(docAssets, file), path.join(assets, file));
    }
  }
}

/* ------------------------------------------------------------------ *
 * 主流程
 * ------------------------------------------------------------------ */
/** 清空 dist：逐个删顶层条目，避免一次性递归删除整个目录 */
async function cleanDist() {
  if (!existsSync(DIST)) return;
  for (const entry of await readdir(DIST, { withFileTypes: true })) {
    await rm(path.join(DIST, entry.name), { recursive: true, force: true });
  }
}

async function build() {
  const started = Date.now();
  // 默认直接覆盖写入（CI 是全新目录，不会有陈旧文件）；需要彻底重建时加 --clean
  if (process.argv.includes('--clean')) await cleanDist();
  await mkdir(DIST, { recursive: true });

  const flat = GROUPS.flatMap((group) => group.items.map(([file]) => file));
  const pages = [{ url: 'index.html', html: buildHome(), outline: [] }];
  for (let i = 0; i < flat.length; i++) pages.push(buildDoc(flat[i], i));
  const built = await Promise.all(pages);

  for (const page of built) {
    const file = page.url.endsWith('/') ? `${page.url}index.html` : page.url;
    const target = path.join(DIST, file);
    await mkdir(path.dirname(target), { recursive: true });
    let out = page.html;
    if (page.outline) {
      out = out.replace('<div class="outline-slot"></div>', `<div class="outline-slot">${outlineHtml(page.outline)}</div>`);
    }
    await writeFile(target, out);
  }

  await copyAssets();
  await writeFile(path.join(DIST, 'search-index.json'), JSON.stringify(await buildSearchIndex()));

  const count = built.length;
  console.log(`OK  ${count} 页 · ${(Date.now() - started)}ms  ->  ${path.relative(ROOT, DIST)}`);
}

function serve() {
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' };
  createServer(async (req, res) => {
    let pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    let file = path.join(DIST, pathname);
    try {
      const info = await stat(file);
      if (info.isDirectory()) file = path.join(file, 'index.html');
    } catch {
      if (existsSync(`${file}.html`)) file = `${file}.html`;
      else if (existsSync(path.join(file, 'index.html'))) file = path.join(file, 'index.html');
    }
    try {
      const body = await readFile(file);
      res.writeHead(200, { 'content-type': types[path.extname(file)] ?? 'application/octet-stream' });
      res.end(body);
    } catch {
      res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found');
    }
  }).listen(4173, () => console.log('预览地址  http://localhost:4173/'));
}

const serveMode = process.argv.includes('--serve');
await build();
if (serveMode) serve();
