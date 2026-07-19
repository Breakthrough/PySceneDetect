// Adds a copy-to-clipboard button to code blocks (the readthedocs theme has no
// built-in equivalent of mkdocs-material's `content.code.copy` feature).
document.addEventListener("DOMContentLoaded", function () {
  var blocks = document.querySelectorAll(".rst-content pre");
  blocks.forEach(function (pre) {
    var code = pre.querySelector("code");
    if (!code) {
      return;
    }
    var button = document.createElement("button");
    button.className = "copy-btn";
    button.type = "button";
    button.title = "Copy to clipboard";
    button.setAttribute("aria-label", "Copy to clipboard");
    button.innerHTML = '<span class="fa fa-clipboard"></span>';
    button.addEventListener("click", function () {
      navigator.clipboard.writeText(code.innerText.trim()).then(function () {
        button.innerHTML = '<span class="fa fa-check"></span>';
        button.classList.add("copied");
        setTimeout(function () {
          button.innerHTML = '<span class="fa fa-clipboard"></span>';
          button.classList.remove("copied");
        }, 600);
      });
    });
    pre.appendChild(button);
  });
});
