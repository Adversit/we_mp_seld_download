# 微信公众号文章备份工具

只面向**公众号管理员本人**的小工具：一键把自己公众号已发布的文章备份成本地 Markdown / HTML / JSON + 图片。

只调用微信官方文档中的接口（`stable_token`、`freepublish/batchget`、`freepublish/getarticle` 能力范围），不使用 `/web/mp/articles`、Cookie 或后台逆向接口，避免账号风控问题。

## 架构

```
浏览器（只填 AppID/AppSecret，测试连接、点击下载）
        │
        ▼
FastAPI 后端（本机运行）
        │
        ├── stable_token          获取 access_token
        ├── freepublish/batchget  分页拉取已发布文章
        └── html → markdown / 图片本地化 / 打包 ZIP
        │
        ▼
微信官方 API
```

**AppSecret 只会发送到你自己本机运行的后端**，不会写入浏览器 LocalStorage，也不会上传到任何第三方服务器。

## 目录结构

```
backend/
  app/
    main.py            FastAPI 路由
    wechat_client.py    微信官方 API 客户端
    export_service.py   HTML→Markdown、图片本地化、打 ZIP
  tests/               pytest 测试
frontend/
  index.html / app.js / style.css   纯静态页面，无需构建
```

## 快速开始

**Windows 一键启动**：双击根目录下的 `start.bat`（首次运行会自动创建虚拟环境并安装依赖，然后自动打开浏览器）。

或手动启动：

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows PowerShell 用 .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000 ，按页面提示：

1. 去微信公众平台（设置与开发 → 基本配置）获取 `AppID` / `AppSecret`
2. 如提示 IP 未加入白名单，把页面显示的服务器出口 IP 加入公众平台白名单
3. 点击「测试连接」，成功后会显示已发布文章数量
4. 选择导出格式，点击「一键下载全部文章」，浏览器会直接下载 ZIP

## 导出的 ZIP 结构

```
raw/*.json          每篇文章的原始接口返回（最终数据底稿，务必保留）
articles/<年份>/*.md 转换后的 Markdown（YAML front matter 带标题/日期/原文链接）
html/*.html          原始正文 HTML（图片已替换为本地相对路径，如勾选下载图片）
images/<id>/*        正文图片
manifest.json        全部文章的索引（标题、发布时间、原文链接）
```

## 已知限制

- 微信从 2025 年 7 月起对部分个人主体/未认证主体账号收紧了 `freepublish` 相关接口权限；如果测试连接返回 `48001`（无权限）或 `40164` / `61024`（IP 未授权），页面会给出对应的处理指引。
- 第一版不做数据库、不做增量同步、不做素材库（图片/语音/视频永久素材）备份，只覆盖「已发布图文文章」这一核心需求。
- 单次导出是同步请求：后端会一次性抓完全部文章并打包再返回，文章很多时请求会持续较长时间，属预期行为。

## 运行测试

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

测试使用 mock 微信客户端，不需要真实的 AppID/AppSecret，也不会产生真实网络请求。
