(function () {
  function ensureToast() {
    var toast = document.querySelector(".toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "toast";
      toast.textContent = "模拟交互已响应";
      document.body.appendChild(toast);
    }
    return toast;
  }

  function showToast(message) {
    var toast = ensureToast();
    toast.textContent = message || "模拟交互已响应";
    toast.classList.add("is-visible");
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(function () {
      toast.classList.remove("is-visible");
    }, 1400);
  }

  document.querySelectorAll("[data-toggle-group]").forEach(function (group) {
    group.querySelectorAll("button, .chip, .pill").forEach(function (item) {
      item.addEventListener("click", function () {
        group.querySelectorAll("button, .chip, .pill").forEach(function (sibling) {
          sibling.classList.remove("is-active");
        });
        item.classList.add("is-active");
        if (item.dataset.toast) {
          showToast(item.dataset.toast);
        }
      });
    });
  });

  document.querySelectorAll("[data-choice-group]").forEach(function (group) {
    group.querySelectorAll(".choice").forEach(function (choice) {
      choice.addEventListener("click", function () {
        group.querySelectorAll(".choice").forEach(function (sibling) {
          sibling.classList.remove("is-selected", "is-correct", "is-wrong");
        });
        choice.classList.add("is-selected");
        if (choice.dataset.result === "correct") {
          choice.classList.add("is-correct");
        }
        if (choice.dataset.result === "wrong") {
          choice.classList.add("is-wrong");
        }
        showToast(choice.dataset.toast || "已选择");
      });
    });
  });

  document.querySelectorAll("[data-favorite]").forEach(function (button) {
    button.addEventListener("click", function () {
      button.classList.toggle("is-active");
      var icon = button.querySelector("i");
      if (icon) {
        icon.className = button.classList.contains("is-active")
          ? "ri-heart-3-fill"
          : "ri-heart-3-line";
      }
      showToast(button.classList.contains("is-active") ? "已加入收藏" : "已取消收藏");
    });
  });

  document.querySelectorAll("[data-switch]").forEach(function (button) {
    button.addEventListener("click", function () {
      button.classList.toggle("is-active");
      showToast(button.classList.contains("is-active") ? "设置已开启" : "设置已关闭");
    });
  });

  document.querySelectorAll("[data-panel-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      var target = document.getElementById(button.dataset.panelToggle);
      if (target) {
        target.classList.toggle("is-open");
        showToast(button.dataset.toast || "已切换内容");
      }
    });
  });

  document.querySelectorAll("[data-toast]").forEach(function (button) {
    button.addEventListener("click", function () {
      showToast(button.dataset.toast);
    });
  });

  document.querySelectorAll("a[href='#']").forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      showToast(link.dataset.toast || "这里是原型交互入口");
    });
  });
})();
