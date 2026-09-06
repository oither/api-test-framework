# 面试问答要点（结合本项目实现）

> 每个问题都对应本仓库的真实代码，回答时可以落到具体文件和具体事件上。

## 1. 为什么用三层架构？如果接口变了，你要改哪里？

- 三层 = **API 封装层**（`api/`，怎么发请求）+ **用例层**（`testcases/`，验证什么）+ **数据层**（`testdata/`，用什么数据验证）。核心目的是让"变"发生在最小的范围内。
- 接口变了只改 **API 层一处**：比如文章详情路径从 `/articles/{id}` 改成 `/posts/{id}`，只动 `article_api.py` 的 `detail()`，62 条引用它的用例和 YAML 数据零改动。
- 反面教材是"用例里直接写 requests 调用"：接口一改，几十个用例逐个改 URL、改参数解析。

## 2. 数据驱动的原理是什么？`@pytest.mark.parametrize` 底层怎么工作？

- pytest 在**收集（collection）阶段**扫描测试函数，`parametrize` 装饰器会把每组参数生成一个独立的测试项（test item），参数通过闭包/属性绑定到函数上，所以报告里每组数据是单独的用例、单独的失败判定。
- 本项目的做法是两级解析（`utils/data_loader.py`）：`parametrize_from_yaml` 在收集阶段读 YAML 生成用例项和用例 ID；`resolve_placeholders` 在**运行阶段**才把 `${uuid}`/`${random_username}` 替换成随机值。分开的原因：用例 ID 需要稳定（收集期生成），而数据需要每次运行随机（保证可重复执行、避免唯一键冲突）。

## 3. fixture 的作用域有哪些？conftest.py 的加载顺序是什么？

- 作用域：function / class / module / package / session。本项目的分配：`auth_api`/`article_api`/`comment_api`/`db` 是 **session 级**（无状态或只读，复用省开销）；`registered_user`/`logged_in_user`/`user_article` 是 **function 级**（每个用例独立数据集 + 自动清理）。
- conftest 按目录从根向下加载，pytest 运行时把沿途所有 conftest 合并；子目录同名 fixture 会覆盖上层。根 `conftest.py` 放 hook（`--env` 参数注册、失败日志），`testcases/conftest.py` 放业务 fixture。
- **踩过的真实坑**：session 级 API 实例是可变共享状态——`logged_in_user` 只给 `AuthAPI` 注入了 Token，`ArticleAPI` 还是 None，导致 34 条用例 setup 阶段 401。修复后也理解了代价：这套设计依赖串行执行，要并行就得改成函数级实例。
- **fixture 还有个隐藏成本：急切加载**。数据驱动的参数化用例把 fixture 全写进函数签名，pytest 就会为**每一组数据**都执行全部前置——哪怕"注册失败 422"这种用例根本不需要预置文章和第二用户。优化方式是签名里只留 `request`，用例内按场景 `request.getfixturevalue("user_article")` 惰性拉取，全量套件耗时从 56s 降到 25s。代价是前置依赖从函数签名（显式）转移到代码分支（隐式），所以要配合清晰的注释和固定的 action 语义。

## 4. 如果接口有依赖关系（比如必须先登录才能发文），你怎么处理？

- 用 **fixture 链式依赖**表达依赖：`user_article` → `logged_in_user` → `registered_user`，pytest 自动按依赖顺序实例化。用例函数签名里出现 `user_article` 就自动获得"已登录用户的一篇文章"，不需要用例内部手工串联注册/登录/发文三个请求。
- 依赖链同时承担了清理职责：每个 fixture yield 后做反向清理（先删评论、再删文章、最后删用户，符合外键指向），保证可重复执行。

## 5. 数据库断言和接口断言各验证什么？为什么要双重断言？

- 接口断言验证**契约**：状态码、响应结构、鉴权/权限语义——覆盖路由、序列化、依赖注入这些 Web 层。
- DB 断言验证**持久化事实**：数据真的写进去了、`author_id`/`user_id` 归属正确、删除后记录真的消失。
- 只查接口发现不了"返回 201 但没写库"（比如事务没提交），只查 DB 发现不了状态码/权限错误。项目里的例子：创建文章用例同时断言 201 和 `articles.author_id == 当前用户 id`；删除文章断言 204 后再直查 `articles` 表确认记录消失。

## 6. 补充问题

**你的 Token 是怎么管理的？**
`BaseAPI.request()` 统一在请求头注入 `Authorization: Bearer <token>`，业务代码不碰请求头。验证 Token 有效性不能用 `GET /articles`——它是公开接口，无 Token 也是 200；项目里用 `PUT /articles/999999`（有效 Token 过了鉴权层返回 404 资源不存在，无效 Token 被拦返回 401），既验证了鉴权又无副作用。日志层面两层防泄露：不打印 headers（避免 Token 落日志），请求体中的 `password`/`token` 字段统一打码为 `***`（避免注册/登录请求的密码明文落日志）。

**失败自动重试是怎么实现的？重试会掩盖问题吗？**
`pytest-rerunfailures` 插件，pytest.ini 里 `--reruns=2 --reruns-delay=1`。它能救环境抖动（连接瞬断），但救不了确定性失败——本项目早期 34 条 401 用例重试 68 次全失败就是证据：重试只对 flaky 有效，对 bug 无效。Allure 报告里 RERUN 状态可辨识，重试过的用例不会被"洗白"成安静通过。

**测试数据怎么做到互不干扰、可重复执行？**
每个用例 fixture 生成 `testuser_<uuid6>` 随机用户，注册/登录/发文都在该用户名下，teardown 直查 SQLite 反向删除该用户的全部评论/文章/用户记录。并行冲突、名字重复、脏数据残留都被这一套规避了。

**你发现过被测系统的问题吗？**
有。写"评论列表-文章不存在"用例时我按 REST 习惯预期 404，实测返回 200 + 空数组；查被测系统源码确认列表接口就是按 `article_id` 过滤、不校验文章存在性，接口文档也只对 POST 承诺 404。最终把用例预期改成 200 + 空列表，并在文档里标注"锚定实际行为"。教训：测试预期锚定的是**约定行为**，写异常用例前先探真实行为或查契约文档，不脑补。

**多环境切换怎么实现的？**
根 `conftest.py` 的 `pytest_addoption` 注册 `--env` 参数，`pytest_configure` 钩子（早于所有 fixture）里按 env 加载 `config/.env.{env}` 到 Settings 单例，API 层和 DB 工具都从单例取 `BASE_URL`/`DB_PATH`。`pytest --env=test` 一键切换。

**测试套件慢，你会从哪里下手？**
先量化再动手。本项目的做法：
1. **减少前置请求**：数据驱动用例的 fixture 急切加载是最大头——64 条用例原来每条都做"注册+登录+（发文+第二用户）"，改成按 action 惰性加载后套件耗时 56s→25s，收益全在"砍无用请求"而不在并发；
2. **fail-fast 排障**：服务没起时秒级报错退出，避免几十条用例各吃 3 次连接重试的无效等待；
3. 更进一步的手段是 pytest-xdist 并行（本项目数据按随机用户隔离，理论可行），但被测系统是 SQLite，并发写入可能触发 database is locked，要评估被测系统的承受力——测试侧提速不能把被测侧拖挂。

**依赖出过什么"莫名其妙"的问题吗？**
有，而且是间接发现被测系统的隐患：被测系统 requirements 钉了 `fastapi==0.104.1` 但没钉 pydantic，pydantic 2.13 发布后 FastAPI 0.104 在 import 阶段直接崩（`FieldInfo.in_`）。测试框架侧的兜底是 CI 安装依赖后显式约束 `pydantic<2.13`。教训：**requirements 里只钉直接依赖不钉传递依赖，等于把传递依赖的升级权交给了 PyPI**——任何一行与自己无关的版本变更都可能弄挂自己的环境，重要环境要么钉全、要么配 lock 文件。
