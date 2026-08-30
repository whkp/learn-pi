/* Learn Pi — 代码块增强
 *
 * - 超过 30 行的代码块默认折叠，提供可键盘访问的展开按钮
 * - 折叠状态不依赖颜色（有明确的文字标签）
 * - prefers-reduced-motion 下无过渡动画
 */
(function () {
  "use strict";

  var COLLAPSE_THRESHOLD = 30;

  function attach() {
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

  document.addEventListener("DOMContentLoaded", attach);
  // mdBook 页面切换后重新绑定
  var observer = new MutationObserver(attach);
  observer.observe(document.body, { childList: true, subtree: true });
})();
