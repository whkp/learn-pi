/* Learn Pi — 页面增强
 *
 * 1. 右侧大纲 TOC：收集正文 h2/h3，生成固定右侧目录，滚动高亮当前小节
 * 2. 章节完成状态：每章末尾的"标记完成"按钮，localStorage 持久化，
 *    侧边栏显示已完成的勾选
 * 3. 30 行以上代码自动折叠（保留自上一版）
 */
(function () {
  "use strict";

  var COLLAPSE_THRESHOLD = 30;
  var STORAGE_KEY = "learnpi-completed-chapters";

  /* ---------- 代码折叠 ---------- */
  function attachCollapse() {
    var blocks = document.querySelectorAll("main pre");
    Array.prototype.forEach.call(blocks, function (pre) {
      if (pre.dataset.learnpiProcessed) return;
      pre.dataset.learnpiProcessed = "1";
      var code = pre.querySelector("code");
      if (!code) return;
      var lineCount = code.textContent.split("\n").length;
      if (lineCount <= COLLAPSE_THRESHOLD) return;

      pre.classList.add("learnpi-collapsible");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "learnpi-collapse-btn";
      button.setAttribute("aria-expanded", "false");
      button.textContent = "展开全部（" + lineCount + " 行）";
      button.addEventListener("click", function () {
        var expanded = pre.classList.toggle("learnpi-expanded");
        button.setAttribute("aria-expanded", String(expanded));
        button.textContent = expanded
          ? "折叠代码"
          : "展开全部（" + lineCount + " 行）";
      });
      pre.appendChild(button);
    });
  }

  /* ---------- 右侧大纲 TOC ---------- */
  function buildOutline() {
    var content = document.querySelector("main .content");
    if (!content) return;
    // 仅在有 ≥3 个二级/三级标题时显示
    var headings = content.querySelectorAll("h2, h3");
    if (headings.length < 3) return;

    var nav = document.createElement("nav");
    nav.className = "learnpi-outline";
    nav.setAttribute("aria-label", "本页目录");

    var title = document.createElement("div");
    title.className = "learnpi-outline-title";
    title.textContent = "本页目录";
    nav.appendChild(title);

    var list = document.createElement("ul");
    Array.prototype.forEach.call(headings, function (heading) {
      if (!heading.id) {
        heading.id =
          "h-" + heading.textContent.trim().replace(/\s+/g, "-").slice(0, 40);
      }
      var item = document.createElement("li");
      item.className = heading.tagName === "H2" ? "lvl-2" : "lvl-3";
      var link = document.createElement("a");
      link.href = "#" + heading.id;
      link.textContent = heading.textContent;
      link.addEventListener("click", function (event) {
        event.preventDefault();
        heading.scrollIntoView({ behavior: "smooth", block: "start" });
        history.replaceState(null, "", "#" + heading.id);
      });
      item.appendChild(link);
      list.appendChild(item);
    });
    nav.appendChild(list);
    document.body.appendChild(nav);

    // 滚动高亮当前小节
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var current = nav.querySelector("a.active");
          if (current) current.classList.remove("active");
          var link = nav.querySelector('a[href="#' + entry.target.id + '"]');
          if (link) link.classList.add("active");
        });
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );
    headings.forEach(function (h) {
      observer.observe(h);
    });
  }

  /* ---------- 章节完成状态 ---------- */
  function readCompleted() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch (e) {
      return [];
    }
  }

  function saveCompleted(list) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {
      /* 隐私模式下静默失败 */
    }
  }

  function attachCompletion() {
    var content = document.querySelector("main .content");
    if (!content) return;
    // 不在首页（课程地图）显示完成按钮
    if (document.querySelector(".home-hero")) return;

    var path = window.location.pathname;

    var box = document.createElement("div");
    box.className = "learnpi-complete";

    var button = document.createElement("button");
    button.type = "button";
    button.className = "learnpi-complete-btn";

    var completed = readCompleted();
    var isDone = completed.indexOf(path) !== -1;
    function refresh() {
      button.textContent = isDone
        ? "✓ 已完成本章"
        : "标记本章为已完成";
      button.classList.toggle("done", isDone);
    }

    button.addEventListener("click", function () {
      completed = readCompleted();
      if (isDone) {
        completed = completed.filter(function (p) {
          return p !== path;
        });
      } else {
        completed.push(path);
      }
      isDone = !isDone;
      saveCompleted(completed);
      refresh();
      updateSidebar();
    });
    refresh();

    box.appendChild(button);
    content.appendChild(box);
  }

  function updateSidebar() {
    var completed = readCompleted();
    var links = document.querySelectorAll(".sidebar li.chapter-item a");
    Array.prototype.forEach.call(links, function (link) {
      var path = link.getAttribute("href") || "";
      if (completed.indexOf(path) !== -1) {
        link.classList.add("learnpi-done");
      } else {
        link.classList.remove("learnpi-done");
      }
    });
  }

  function init() {
    attachCollapse();
    buildOutline();
    attachCompletion();
    updateSidebar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  var observer = new MutationObserver(init);
  observer.observe(document.body, { childList: true, subtree: true });
})();
