const API_BASE = "";

const els = {
  appId: document.getElementById("app-id"),
  appSecret: document.getElementById("app-secret"),
  serverIp: document.getElementById("server-ip"),
  copyIp: document.getElementById("copy-ip"),
  verifyBtn: document.getElementById("verify-btn"),
  status: document.getElementById("status"),
  connectForm: document.getElementById("connect-form"),
  connectedPanel: document.getElementById("connected-panel"),
  cAppId: document.getElementById("c-app-id"),
  cTotal: document.getElementById("c-total"),
  exportBtn: document.getElementById("export-btn"),
  resetLink: document.getElementById("reset-link"),
};

// 已知微信错误码 -> 用户可操作的指引
const ERROR_GUIDE = {
  40164: {
    title: "调用 IP 不在白名单",
    detail: () => `当前服务器出口 IP：${els.serverIp.textContent}\n请前往：微信公众平台 → 设置与开发 → 基本配置 → IP 白名单`,
    linkText: "去微信公众平台配置 ↗",
  },
  61024: {
    title: "调用 IP 不在白名单",
    detail: () => `当前服务器出口 IP：${els.serverIp.textContent}\n请前往：微信公众平台 → 设置与开发 → 基本配置 → IP 白名单`,
    linkText: "去微信公众平台配置 ↗",
  },
  48001: {
    title: "当前公众号暂无该 API 权限",
    detail: () => "此接口通常需要认证的服务号/订阅号权限，请查看官方权限说明",
    linkText: "查看公众号开发文档 ↗",
    link: "https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html",
  },
  40013: {
    title: "AppID 无效",
    detail: () => "请检查 AppID 是否复制完整",
  },
  40125: {
    title: "AppSecret 无效",
    detail: () => "请重新在公众平台核对或重置 AppSecret",
  },
};

function showStatus(kind, html) {
  els.status.className = kind;
  els.status.innerHTML = html;
}

function clearStatus() {
  els.status.className = "";
  els.status.innerHTML = "";
}

async function fetchServerIp() {
  try {
    const resp = await fetch(`${API_BASE}/api/server-ip`);
    const data = await resp.json();
    els.serverIp.textContent = data.ip || "获取失败";
  } catch {
    els.serverIp.textContent = "获取失败（离线或无法访问）";
  }
}

els.copyIp.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(els.serverIp.textContent);
    els.copyIp.textContent = "已复制";
    setTimeout(() => (els.copyIp.textContent = "复制"), 1500);
  } catch {
    /* clipboard may be unavailable, ignore */
  }
});

function renderError(errcode, errmsg) {
  const guide = ERROR_GUIDE[errcode];
  if (guide) {
    const link = guide.link || "https://mp.weixin.qq.com/";
    showStatus(
      "error",
      `✕ ${errcode} ${guide.title}<br>` +
        `<pre style="white-space:pre-wrap;font:inherit;margin:6px 0">${guide.detail()}</pre>` +
        `<a class="link-btn" href="${link}" target="_blank" rel="noopener">${guide.linkText || "去微信公众平台配置 ↗"}</a>`
    );
  } else {
    showStatus("error", `✕ ${errcode ?? ""} ${errmsg || "连接失败，请检查凭证"}`);
  }
}

async function apiPost(path, body) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!resp.ok) {
    const detail = data.detail || {};
    const err = new Error(detail.errmsg || "request failed");
    err.errcode = detail.errcode;
    err.errmsg = detail.errmsg;
    throw err;
  }
  return data;
}

function credentials() {
  return { app_id: els.appId.value.trim(), app_secret: els.appSecret.value.trim() };
}

els.verifyBtn.addEventListener("click", async () => {
  clearStatus();
  const creds = credentials();
  if (!creds.app_id || !creds.app_secret) {
    showStatus("error", "请先填写 AppID 和 AppSecret");
    return;
  }
  els.verifyBtn.disabled = true;
  els.verifyBtn.textContent = "连接中…";
  try {
    const data = await apiPost("/api/account/verify", creds);
    showStatus("info", "✓ 公众号连接成功");
    els.cAppId.textContent = creds.app_id;
    els.cTotal.textContent = `${data.total_count} 篇`;
    els.connectForm.style.display = "none";
    els.connectedPanel.style.display = "block";
  } catch (e) {
    renderError(e.errcode, e.errmsg);
  } finally {
    els.verifyBtn.disabled = false;
    els.verifyBtn.textContent = "测试连接";
  }
});

els.exportBtn.addEventListener("click", async () => {
  clearStatus();
  const creds = credentials();
  const formats = Array.from(document.querySelectorAll("#format-checks input[type=checkbox]:not(#with-images)"))
    .filter((cb) => cb.checked)
    .map((cb) => cb.value);
  const withImages = document.getElementById("with-images").checked;

  els.exportBtn.disabled = true;
  els.exportBtn.textContent = "打包中，请稍候…";
  try {
    const resp = await fetch(`${API_BASE}/api/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...creds, formats, with_images: withImages }),
    });
    if (!resp.ok) {
      const data = await resp.json();
      const detail = data.detail || {};
      renderError(detail.errcode, detail.errmsg);
      return;
    }
    const blob = await resp.blob();
    const disposition = resp.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "wechat-backup.zip";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showStatus("info", "✓ 下载完成");
  } catch (e) {
    showStatus("error", "导出失败，请检查网络或稍后重试");
  } finally {
    els.exportBtn.disabled = false;
    els.exportBtn.textContent = "一键下载全部文章";
  }
});

els.resetLink.addEventListener("click", () => {
  els.connectedPanel.style.display = "none";
  els.connectForm.style.display = "block";
  clearStatus();
});

fetchServerIp();
