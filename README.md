# api-test-framework — 博客系统 API 自动化测试框架

![API Tests](https://github.com/oither/api-test-framework/actions/workflows/api-tests.yml/badge.svg)

基于 **Python + pytest + requests** 的数据驱动 API 自动化测试框架，针对个人博客系统（FastAPI + SQLite）的全部 11 个接口编写了 **64 条测试用例**，采用 **API 层 / 用例层 / 数据层** 三层架构，支持多环境切换、接口 + 数据库双重断言、Allure 报告与失败自动重试，并通过 GitHub Actions 在每次 push 时自动完成「拉起被测服务 → 跑全量用例 → 发布 Allure 报告」。

> 被测系统：[blog-system-under-test](https://github.com/oither/blog-system-under-test.git)（FastAPI + SQLite + JWT，含用户认证、文章 CRUD、评论与资源归属权限校验）

## 技术栈

| 层面 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 实际运行于 3.13 |
| 测试框架 | pytest 8.x | fixture 管理生命周期、parametrize 数据驱动 |
| HTTP 请求 | requests | `Session` 会话复用，统一封装 |
| 数据驱动 | PyYAML | 测试数据与用例代码分离 |
| 数据库校验 | sqlite3（标准库） | 直查被测系统 SQLite，做落库双重断言 |
| 报告 | Allure（allure-pytest） | epic/feature/story/title 分层标记 |
| 环境管理 | python-dotenv | `.env.dev` / `.env.test` / `.env.prod` 一键切换 |
| 日志 | loguru | 控制台 + 按天滚动文件双输出 |
| 失败重试 | pytest-rerunfailures | `--reruns=2` 自动重试 flaky 用例 |

## 框架架构

```
                    ┌─────────────────────────────────────────┐
                    │              pytest 驱动层               │
                    │   conftest.py（hook / marker / 环境初始化）│
                    └────────────────┬────────────────────────┘
                                     │
        ┌────────────┐    ┌──────────▼───────────┐    ┌──────────────┐
        │  数据层     │    │       用例层          │    │   工具层      │
        │ testdata/  │───▶│     testcases/       │───▶│   utils/     │
        │ *.yaml     │    │ test_auth / article  │    │ db_helper    │
        │ 参数化数据  │    │ test_comment         │    │ data_loader  │
        └────────────┘    └──────────┬───────────┘    │ logger       │                                     │                └──────┬───────┘
                                     │                         │
                          ┌──────────▼───────────┐    ┌────────▼───────┐
                          │       API 层          │    │   config/      │
                          │  base_api（会话/Token/ │    │ settings.py    │
                          │  日志）+ 模块封装       │    │ .env.dev/test/ │
                          └──────────┬───────────┘    │ .env.prod      │
                                     │                └────────────────┘
              ┌──────────────────────┴───────────────────┐
              ▼                                          ▼
   ┌─────────────────────┐                   ┌─────────────────────┐
   │  被测系统 (HTTP 8000) │                   │  被测数据库 SQLite    │
   │  FastAPI 博客服务     │                   │  blog.db 直查        │
   └─────────────────────┘                   └─────────────────────┘
```

**三层职责**

- **API 层**（`api/`）：每个业务模块一个封装类，继承 `BaseAPI`。`BaseAPI` 统一管理 `Session`、Bearer Token 注入、请求/响应日志与超时，上层只关心业务参数，不碰 requests 细节。
- **用例层**（`testcases/`）：只写业务断言逻辑，不写请求数据。前置条件（注册、登录、发文、清理）全部由 fixture 承担。
- **数据层**（`testdata/`）：YAML 维护正常/异常/边界测试数据，通过 `parametrize_from_yaml` + `resolve_placeholders`（`${uuid}` 等占位符）注入参数化用例，**一份代码跑多组数据**。

## 目录结构

```
api-test-framework/
├── config/                  # 配置层
│   ├── settings.py          # 读取 .env.{env}，Settings 单例
│   ├── .env.dev             # 开发环境（BASE_URL / DB_PATH）
│   ├── .env.test            # 测试环境
│   └── .env.prod            # 生产环境
├── api/                     # API 封装层
│   ├── base_api.py          # 会话 / Token / 日志 / get post put delete
│   ├── auth_api.py          # 注册、JSON 登录、Form 登录
│   ├── article_api.py       # 文章 CRUD
│   └── comment_api.py       # 评论增删查
├── testcases/               # 用例层
│   ├── conftest.py          # 全局 fixture：随机用户注册/登录/Token 注入/数据清理
│   ├── test_smoke.py        # 冒烟：健康检查 + 注册→登录→发文→落库→清理
│   ├── test_auth.py         # 认证模块 23 条（含 Form 登录、鉴权与校验顺序）
│   ├── test_article.py      # 文章模块 27 条
│   └── test_comment.py      # 评论模块 12 条
├── testdata/                # 数据层
│   ├── auth_data.yaml       # 注册/登录正常、异常、边界数据
│   ├── article_data.yaml    # 文章 CRUD + 分页/搜索边界
│   └── comment_data.yaml    # 评论正常、异常、权限、跨文章删除
├── utils/                   # 工具层
│   ├── db_helper.py         # SQLite 查询封装（用户/文章/评论表）
│   ├── data_loader.py       # YAML 加载 + 参数化 + 占位符解析 + 随机用户生成
│   └── logger.py            # loguru 日志
├── reports/                 # allure-results / allure-report / logs（不入库）
├── conftest.py              # 根 conftest：--env 参数、marker 注册、失败日志
├── pytest.ini               # alluredir、reruns、marker 声明
├── docs/
│   └── interview-notes.md   # 面试问答要点（结合本项目实现）
├── .github/workflows/       # CI：起被测服务 → 全量用例 → Allure 报告 artifact
└── requirements.txt
```

## 快速开始

### 1. 启动被测系统

```bash
git clone <blog-system-under-test 仓库地址>
cd blog-system-under-test
pip install -r requirements.txt
copy .env.example .env        # Windows，Linux 用 cp
uvicorn app.main:app --reload # 服务运行在 http://127.0.0.1:8000
```

### 2. 安装测试框架依赖

```bash
cd api-test-framework
pip install -r requirements.txt
```

### 3. 运行测试

```bash
# 默认 dev 环境
pytest

# 指定环境（读取 config/.env.{env}）
pytest --env=test

# 只跑冒烟
pytest -m smoke

# 失败用例自动重试已在 pytest.ini 中开启（--reruns=2）
```

> 注意：需在项目根目录运行 pytest——`DB_PATH` 与日志输出均为相对路径，从其他目录运行会导致数据库校验与日志落错位置。

### 4. 查看 Allure 报告

```bash
# 方式一：生成静态报告后打开
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report

# 方式二：直接起本地服务实时预览
allure serve reports/allure-results
```

> Allure 命令行需要单独安装：`scoop install allure` / `npm install -g allure-commandline`，或从 [GitHub Releases](https://github.com/allure-framework/allure2/releases) 下载，要求 Java 8+。

## 持续集成

GitHub Actions 工作流（[.github/workflows/api-tests.yml](.github/workflows/api-tests.yml)）在每次 push 到 main 或手动触发时自动执行：

1. 克隆被测博客系统，安装两侧依赖，生成随机 `SECRET_KEY` 配置
2. 后台启动 uvicorn，轮询健康检查接口等待服务就绪
3. `pytest --env=dev` 跑全量 64 条用例
4. 无论成败，生成 Allure HTML 报告并上传为构建产物（Artifact）；用例失败时额外上传被测服务日志便于排查

报告在 Actions 运行详情页底部 Artifacts 区下载后本地打开即可。

## 用例覆盖

共 **64 条用例**，覆盖被测系统 11 个接口的正常、异常、边界、鉴权与权限场景：

| 模块 | 接口 | 用例数 | 覆盖场景 |
|------|------|-------|---------|
| 冒烟 | `/` 注册→登录→发文链路 | 2 | 服务可用性、核心链路、落库校验 |
| 认证 | `POST /auth/register` | 9 | 注册成功（DB 校验密码已哈希）、用户名/邮箱重复 400、非法邮箱/缺字段/全 null 422 |
| 认证 | `POST /auth/login` | 5 | 登录成功（Token 可用）、密码错误 401、用户不存在 401、禁用账号 403、字段 null 422 |
| 认证 | `POST /auth/login/form` | 2 | Form 表单登录成功（Token 可用）、密码错误 401 |
| 认证 | 受保护接口鉴权 | 7 | 5 类受保护接口无 Token 401、无效 Token 401、校验顺序 401 先于 404 |
| 文章 | `POST /articles` | 6 | 创建成功（DB 校验 author_id 归属）、缺 title/content 422、未登录 401、空标题/超长标题边界 |
| 文章 | `GET /articles` | 6 | 默认分页、自定义分页、limit=0/101 422、limit=1 下界、skip 负数 422 |
| 文章 | `GET /articles?search=` | 2 | 命中返回非空、未命中返回空 |
| 文章 | `GET /articles/{id}` | 2 | 存在 200、不存在 404 |
| 文章 | `PUT /articles/{id}` | 5 | 全量更新、部分更新（exclude_unset 未传字段不被改）、非作者 403、不存在 404、未登录 401 |
| 文章 | `DELETE /articles/{id}` | 4 | 作者删除 204（DB 校验已删）、非作者 403、不存在 404、未登录 401 |
| 文章 | 权限校验顺序 | 2 | 有 Token + 资源不存在 → 404、非作者修改 → 403 |
| 评论 | `POST /articles/{id}/comments` | 4 | 创建成功（DB 校验 user_id/article_id）、文章不存在 404、未登录 401、缺 content 422 |
| 评论 | `GET /articles/{id}/comments` | 3 | 有评论非空、无评论为空、文章不存在返回空列表（锚定实际行为） |
| 评论 | `DELETE /articles/{id}/comments/{id}` | 5 | 评论者删除 204（DB 校验）、非评论者 403、跨文章删除 404、评论不存在 404、未登录 401 |

**双重断言说明**：接口断言验证 HTTP 状态码与响应结构（路由、鉴权、序列化是否正确）；数据库断言直接查 SQLite 验证数据真实落库（写入是否成功、`author_id`/`user_id` 归属是否正确、删除后记录是否真的消失）。只断言接口无法发现"返回 201 但没写库"这类问题，反之亦然。

**用例可重复执行**：每个用例由 fixture 自动注册随机用户（`testuser_<uuid>`）并登录注入 Token，用例结束后清理该用户全部文章/评论/用户记录，用例之间互不污染，可反复回归。

## 遇到的问题与解决

**1. 登录态 fixture 只给 AuthAPI 注入了 Token，文章/评论接口全部 401**

- **现象**：冒烟测试通过，但全量跑 34 条用例在 setup 阶段集体 ERROR，日志显示用有效 Token 创建文章却返回 401。
- **定位**：`AuthAPI` / `ArticleAPI` / `CommentAPI` 是三个独立的 Session 实例，`logged_in_user` fixture 只调用了 `auth_api.set_token()`，`ArticleAPI` 的 Token 仍是 None，发请求时没带 `Authorization` 头。冒烟能过纯属巧合——它自己在用例里手动 set 了 Token。
- **解决**：登录后统一遍历注入全部 API 实例的 Token。
- **收获**：fixture 之间共享的可变状态（session 级 API 实例）是自动化框架的高坑区；冒烟通过 ≠ 框架正确，要用依赖 `user_article` 的用例做验证。

**2. 调了继承自基类的通用方法而不是模块封装方法，URL 被拼坏**

- **现象**：删评论相关用例报 `TypeError` / 非法 URL。
- **定位**：`BaseAPI.delete(path)` 是通用方法（接收路径字符串），与 `CommentAPI.delete_comment(article_id, comment_id)` 同名易混，用例里误写成 `comment_api.delete(article_id, cid)`，参数错位。
- **解决**：修正调用；并意识到 API 封装层的命名要和基类通用方法拉开区分度。

**3. 测试预期与系统实际行为不符：文章不存在时评论列表返回 200 而非 404**

- **现象**："评论列表-文章不存在" 用例期望 404，实际返回 200 + 空数组，重试两次仍失败。
- **定位**：查被测系统源码确认 `GET /articles/{id}/comments` 实现就是按 `article_id` 过滤查询，不校验文章存在性（README 接口文档也只对 POST 承诺 404）。
- **解决**：修正用例预期为 200 + 空列表。
- **收获**：写异常用例前必须先用真实请求探一遍系统行为（或对照接口文档），不能想当然按 REST 语义脑补预期；测试锚定的应该是"约定行为"而不是"想象行为"。

## 设计取舍

- **为什么 sqlite3 而不是 SQLAlchemy？** 只做只读校验和清理 DELETE，单文件库、无连接池诉求，标准库零依赖反而更简单。
- **为什么每个用例新建随机用户？** 被 CRUD 用例共享账号会造成数据耦合（A 用例删了 B 用例的文章），随机用户 + fixture 清理让每个用例自带独立数据集，天然支持重复执行。
- **为什么 Token 放 fixture 注入而不是用例里手动 set？** 用例只描述业务场景，登录态是绝大多数用例的公共前置；权限类用例（401/403）再单独显式置空/替换 Token。

## 已知局限与后续方向

- 被测系统使用 SQLite 单文件库，并发与性能场景不在本项目范围内，由独立的 Locust 全链路压测项目覆盖。
- 用例串行执行，session 级 API 实例的 Token 状态依赖该前提；如需并行（pytest-xdist）应改为函数级实例或按请求显式传 Token。
- 异常场景依赖被测系统真实行为，未引入 Mock/Stub（如"禁用账号"靠直改数据库构造）。

结合本项目实现的面试问答要点见 [docs/interview-notes.md](docs/interview-notes.md)。
