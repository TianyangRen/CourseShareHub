# CourseShare Hub — 满分项目蓝图 (COMP-8347 Summer 2026)

> A Distributed Course Resource Sharing Platform Built with Django
> Team: Honghao Zhang · Tianyang Ren · Lei Jiang · Kun Lan · Zhihan Zhang
> 目标：Final Grading 拿满 **21 / 21**（20 主分 + 1 早答辩加分）

---

## 0. 评分表逐项拆解（这是全篇的“北极星”）

评分表满分 **21**，由 6 大块组成。下表把每一分都落到“谁做、做什么、演示时怎么体现”。

| 评分项 | 分值 | 拿满条件（Excellent 档） | 我们的对策 | 负责人 |
|---|---|---|---|---|
| Presentation & Delivery | /4 | 结构清晰、目的明确、**5 人都开口且均衡**、每人讲自己那部分、有 live demo | 分段脚本，每人讲自己模块 + 亲自 demo 自己的功能（§9） | 全员 |
| GitHub Contribution & Activity | /4 | **多周持续提交**（非一天堆完）、每人有实质代码、commit message 描述性强、无 AI 痕迹 | 5 周提交节奏表 + 每人独立 feature 分支 + 规范 commit（§7） | 全员 |
| Authentication (login/logout/forgot pw) | /1 | 完整实现 | Django auth + 自定义注册 + 密码找回（§5.1） | Honghao |
| Forms, Models & CRUD | /1 | 完整实现 | 11 个模型 + Resource 完整增删改查 CBV（§5.2） | Tianyang |
| User Sessions & Cookies (History) | /1 | 完整实现 | cookie 记“每日访问次数” + session 记最近浏览/搜索（§5.4） | Kun |
| Search + Dropdown Filter | /1 | 完整实现 | 关键词搜索 + 4 个下拉过滤（course/category/type/date）（§5.3） | Lei |
| File Upload | /1 | 完整实现 | Resource 文件上传 + 头像/ID 上传 + 校验（§5.5） | Zhihan |
| Registered vs Guest Interface | /1 | 完整实现 | Mixin + 模板条件渲染，三种角色差异化（§5.6） | 全员 |
| Visual Design & UI/UX | /2 | Bootstrap 专业、布局干净、字体可读、配色统一、导航顺畅、footer 与主题一致 | 统一设计系统 + 4 列 footer（§6） | Zhihan |
| Testing | /2 | demo 中所有功能无错、优雅处理边界（校验、错误登录、空搜索） | 单元测试 + demo 边界清单（§8） | Zhihan+全员 |
| Questions & Answers | /2 | 用自己的话自信作答、真正理解 views/models/sessions/auth/queries | 每人准备本模块 Q&A（§9.3） | 全员 |
| **Early Defense Bonus** | **/1** | **在 Week 11 答辩** | 排 Week 11 早答辩 | 全员 |

**总分带：Excellent ≥18｜Good ≥16｜Satisfactory ≥13。我们目标 21。**

> ⚠️ **Note 3（最高优先级）**：使用 ChatGPT/其他 AI 工具/外部源码 → **直接 0 分**。本文档是“架构蓝图/学习提纲”，**每个人必须自己写、自己懂自己的代码**——viva/Q&A 是权重最高项，会当场检验。把本文当设计说明，代码逐行自己敲、自己理解。

---

## 1. 技术栈与项目结构

- Python 3.x + Django（课上版本）+ PyCharm
- 数据库：SQLite（开发）；**初始数据用 JSON fixtures 加载**，并用 `dumpdata` 导出为 JSON 满足“database in JSON”要求
- 前端：Bootstrap 5（本地静态文件，尽量不引 CDN 外部 API）
- 版本控制：GitHub（务必加协作者 `comp8347proj` —— Note 4）
- 部署：PythonAnywhere 免费版（提供 live website 链接）

**单一主 app 结构**（方便单独提交 `views.py / models.py / forms.py`）：

```
coursesharehub/            # project
  settings.py  urls.py  wsgi.py
hub/                       # 主 app：主 views.py / models.py / forms.py 都在这
  models.py  views.py  forms.py  urls.py  admin.py
  validators.py           # 文件校验
  context_processors.py   # 访问计数(cookie) + 全局数据
  templates/hub/...
  fixtures/  categories.json  courses.json  resources.json  users.json
  tests.py
templates/base.html        # 全站骨架 + navbar + footer
static/  css/  js/  img/
media/                     # 上传文件（.gitignore）
manage.py  requirements.txt  .gitignore  README.md
```

`.gitignore` 至少包含：`venv/  __pycache__/  *.pyc  db.sqlite3  media/  .idea/`

---

## 2. 数据模型设计（11 个模型，人均 ≥2）

> PPT 核心 7 个：Category, Course, Resource, UserProfile, Comment, Favourite, UserHistory。
> 再补 4 个（Tag, SavedSearch, DailyVisitLog, ContactMessage）——既凑满“每人 2 个 model”，也直接变成**加分功能**。

| 模型 | 关键字段 | 关系 | Owner |
|---|---|---|---|
| **Category** | name, slug, description, icon | — | Tianyang |
| **Course** | code(如 COMP-8347), title, description, term | — | Tianyang |
| **Resource** | title, description, file(FileField), file_type(choices), is_public, views_count, download_count, created/updated_at | uploader→User, course→Course, category→Category, tags→Tag(M2M) | Tianyang |
| **Tag** | name, slug | M2M ← Resource | Lei |
| **SavedSearch** | keyword, course, category, file_type, created_at | user→User | Lei |
| **UserProfile** | avatar(ImageField), student_id, program, bio | OneToOne→User | Honghao |
| **ContactMessage** | name, email, subject, body, is_read, created_at | — | **Kun** |
| **UserHistory** | action(VIEW/DOWNLOAD/SEARCH/UPLOAD), keyword, created_at | user→User, resource→Resource(null) | Kun |
| **DailyVisitLog** | date, visit_count；unique(user/session_key, date) | user→User(null) | Kun |
| **Comment** | body, created_at | resource→Resource, author→User | Zhihan |
| **Favourite** | created_at；unique(user, resource) | user→User, resource→Resource | Zhihan |

要点：
- `Resource.is_public` 控制游客可见性；`file_type` 用 choices，在 `save()` 里按扩展名自动判定。
- `UserProfile` 用 `post_save` signal 随 User 自动创建。
- 所有模型写 `__str__`、`Meta.ordering`、必要的 `unique_together`（Q&A 会问）。

---

## 3. Views 设计（含强制的 Class-Based Views）

> 要求明确：**把 index 和 detail 改成 class-based views**。以下 CBV 直接满足。

| View | 类型 | 说明 | Owner |
|---|---|---|---|
| `HomeView` | TemplateView | 首页：分类卡片、最新/热门资源、搜索栏 | Zhihan |
| `ResourceListView` | **ListView** | **index**：分页 + 关键词搜索 + 下拉过滤（`get_queryset`） | Lei |
| `ResourceDetailView` | **DetailView** | **detail**：浏览量+1、写入 session 最近浏览、评论区 | Lei |
| `save_search` / `SavedSearchListView` / `delete_saved_search` | FBV + ListView | 保存/查看/删除搜索条件 | Lei |
| `ResourceCreateView` | CreateView + LoginRequiredMixin | 上传资源（CRUD-C） | Tianyang |
| `ResourceUpdateView` | UpdateView + UserPassesTestMixin | 仅作者可改（CRUD-U） | Tianyang |
| `ResourceDeleteView` | DeleteView + UserPassesTestMixin | 仅作者可删（CRUD-D） | Tianyang |
| `resource_download` | FBV | 下载并 +download_count | Tianyang |
| `CategoryListView` / `CourseListView` | ListView | 分类/课程目录（带资源计数） | **Tianyang** |
| `CategoryCreateView` / `CourseCreateView` | CreateView + LoginRequiredMixin | 新增分类/课程 | **Tianyang** |
| `RegisterView` | CreateView/FormView | 注册 | Honghao |
| `ProfileView` / `ProfileUpdateView` | Detail/UpdateView | 个人资料 + 头像上传 | Honghao |
| `ContactView` | CreateView | Contact Us 表单入库 | **Kun** |
| `HistoryView` | TemplateView/FBV | User History：每日访问次数 + 最近浏览 + 最近搜索 | Kun |
| `clear_history` | FBV | 清空 session 历史 | Kun |
| `toggle_favourite` | FBV(login) | 收藏/取消 | Zhihan |
| `add_comment` | FBV/CreateView(login) | 评论 | Zhihan |
| Login/Logout/Password reset | Django 内置 CBV | 在 urls 挂载并配置模板 | Honghao |
| `AboutView` | TemplateView | About 页 | **Tianyang** |
| `TeamView` | TemplateView | Team 页 | **Honghao** |

---

## 4. Forms 设计（人均 ≥2）

| Form | 用途 | Owner |
|---|---|---|
| `RegisterForm`(UserCreationForm 扩展) | 注册（含 email 校验） | Honghao |
| `UserProfileForm` | 资料 + 头像/ID 上传 | Honghao |
| `ContactForm` | 联系我们 | **Kun** |
| `ResourceForm` | 上传/编辑资源（文件校验） | Tianyang |
| `CourseForm` / `CategoryForm` | 后台/管理端增改 | Tianyang |
| `SearchFilterForm` | 搜索关键词 + 下拉过滤 | Lei |
| `SavedSearchForm` | 保存搜索条件 | Lei |
| `CommentForm` | 评论 | Zhihan |
| `BootstrapAuthenticationForm`/`PasswordResetForm`/`SetPasswordForm` | 给内置 auth 表单套 Bootstrap 样式 | Honghao |

所有表单写 `clean_*` 校验（Testing 项要靠它体现边界处理）。

---

## 5. 六大强制功能实现要点

### 5.1 Authentication（/1，Honghao）
- 登录/登出：`django.contrib.auth` 内置 `LoginView`/`LogoutView`。
- 注册：`RegisterForm` 继承 `UserCreationForm`，注册后自动登录。
- **忘记密码**：用 Django 内置 `PasswordResetView` 四件套（reset / done / confirm / complete）。
  - **不引外部 API**：`EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`，重置链接打印到控制台；demo 时展示控制台里的链接→点击→重设。既满足功能又零外部依赖。
- 登录失败要有友好错误提示（Testing 边界项）。

### 5.2 Forms / Models / CRUD（/1，Tianyang）
- Resource 的 **C/R/U/D** 全部用 CBV（见 §3），Update/Delete 用 `UserPassesTestMixin` 限作者本人。
- 关系齐全：Resource↔Course/Category/Tag/User，Q&A 时能讲清 FK/M2M/on_delete。
- `admin.py` 注册所有模型，`list_display/search_fields/list_filter` 配好（也是加分）。

### 5.3 Search + Dropdown Filter（/1，Lei）
- 顶部搜索栏 `?q=`：`Q(title__icontains=q) | Q(description__icontains=q) | Q(tags__name__icontains=q)`。
- 4 个下拉（预定义选项）：`course`、`category`、`file_type`、`sort/date`；在 `ResourceListView.get_queryset()` 链式过滤。
- 空搜索 → 显示“未找到结果”的友好空态（Testing 边界项）。
- 每次搜索把关键词写入 session `recent_searches` 和 `UserHistory`。

### 5.4 Sessions & Cookies — User History（/1，Kun）
参考 care2 的“每日访问计数”：
- **Cookie**：`context_processors.py` 里读 `last_visit` / `daily_visit_count`，跨天则归零、同天则 +1，回写 cookie；同时给注册用户写 `DailyVisitLog`。
- **Session**：
  - `recently_viewed`：DetailView 里维护最近浏览的 resource id 列表（去重、最多 10）。
  - `recent_searches`：搜索时维护最近关键词（最多 10）。
- **History 页面**展示：今日访问次数、累计访问、最近浏览、最近搜索；注册用户额外看每日访问柱状图 + `UserHistory` 列表。
- 提供“清空历史”。

### 5.5 File Upload（/1，Zhihan）
- `Resource.file = FileField(upload_to='resources/%Y/%m/')`；`UserProfile.avatar = ImageField`（可作为“照片/ID”上传）。
- `validators.py`：限制大小（如 ≤10MB）+ 扩展名白名单（pdf/doc/docx/ppt/pptx/png/jpg）；违规抛 `ValidationError`。
- 配 `MEDIA_URL`/`MEDIA_ROOT`，开发期在 urls 挂 media 静态服务。
- 边界演示：上传超大文件/非法类型 → 表单报错不崩溃。

### 5.6 Registered vs Guest Interface（/1，全员）
| 能力 | Guest | Registered | Admin |
|---|---|---|---|
| 浏览/搜索公开资源 | ✅ | ✅ | ✅ |
| 查看详情 | ✅（下载/评论/收藏需登录） | ✅ | ✅ |
| 上传/改删自己的资源 | ❌ | ✅ | ✅ |
| 评论/收藏/历史/个人页 | ❌ | ✅ | ✅ |
| 管理用户/分类/全部内容 | ❌ | ❌ | ✅(Django admin) |

实现：`LoginRequiredMixin` / `@login_required` / `UserPassesTestMixin` + 模板 `{% if user.is_authenticated %}`。导航栏未登录显示“登录/注册”，登录后显示头像下拉。

---

## 6. UI/UX + Footer（/2，Zhihan）

**配色（统一、醒目又专业）**
- Primary 靛蓝 `#4F46E5`，Accent 琥珀 `#F59E0B`，文字 `#1E293B`，次要 `#64748B`，背景 `#F8FAFC`，卡片白。
- 字体：Inter / system-ui；标题 600–700。
- 组件统一：卡片阴影、圆角、按钮悬停、分页、面包屑、toast/alert。

**Navbar**：Logo + 站名｜搜索栏｜分类下拉｜（未登录）登录/注册 /（登录）头像下拉。
**Footer（4 列 + 底栏）**：
1. About CourseShare Hub（一句简介）
2. Quick Links（Home / Browse / Upload / About / Team）
3. Categories（Notes / Labs / Slides / Past Exams…）
4. Contact（邮箱 + 社交图标）
底栏：`© 2026 CourseShare Hub · COMP-8347 · Team of 5`

`base.html` 用 `{% block %}` 继承；全站导航顺畅、响应式。

---

## 7. GitHub 策略（/4）——多周、均衡、可信

**分支**：`main` + 每人 `feat/<name>-<模块>`；小步提交，PR 合并。
**Commit 规范**（描述性，评分表点名要这种）：
- ✅ `Add UserHistory session tracking for recently viewed`
- ✅ `Implement forgot-password flow with console email backend`
- ❌ `update` / `fix` / `final`（会扣分）

**5 周提交节奏（关键：不要最后一天堆）**

| 周 | 里程碑 | 每人应有的提交 |
|---|---|---|
| W6 | 立项：`startproject`、settings、base.html、models 骨架 | 各自建自己的 model + `__str__` |
| W7 | Auth + CRUD 打通 | Honghao 登录注册；Tianyang Resource CRUD |
| W8 | 搜索/过滤 + Session/Cookie 历史 | Lei 搜索过滤；Kun 历史追踪 |
| W9 | 上传 + UI/Bootstrap + fixtures | Zhihan 上传+样式；全员填 fixtures |
| W10 | 收尾：测试、附加页、部署、写文档 | 各自补单元测试 + bug 修复 |
| W11 | **早答辩（+1 bonus）** | tag `v1.0`、最终 README |

**别忘**：Settings → Collaborators 加 `comp8347proj`。

---

## 8. Testing（/2，Zhihan 主导，全员补自己模块）

**单元测试（`tests.py`）**
- Models：`__str__`、关系、`unique_together`。
- Forms：非法输入被拒（空标题、超大文件、错误扩展名）。
- Views：状态码、未登录访问上传→重定向登录、作者外的人改删→403。
- Auth：注册→登录→登出→找回密码 token 流程。

**Demo 边界清单（评分表明确奖励“优雅处理边界”，现场务必演示）**
- [ ] 错误密码登录 → 友好报错，不崩
- [ ] 空搜索 / 无结果 → 空态提示
- [ ] 上传非法类型/超大文件 → 表单校验拦截
- [ ] 游客点“上传/收藏” → 跳登录页
- [ ] 非作者访问他人编辑/删除 URL → 403
- [ ] 重复收藏同一资源 → 不报错（幂等）
- [ ] 忘记密码 → 展示重置链接并成功改密

---

## 9. 演讲（/4）+ Q&A（/2）

### 9.1 10 分钟分段脚本（人人开口、均衡、讲自己那块）
1. Honghao（1.5min）：问题背景 + 目标 + 架构总览，然后 demo 注册/登录/忘记密码。
2. Tianyang（2min）：模型关系图 + demo 资源增删改查。
3. Lei（1.5min）：demo 关键词搜索 + 下拉过滤 + 空搜索边界。
4. Kun（1.5min）：demo User History（每日访问次数、最近浏览/搜索）+ 讲 session/cookie。
5. Zhihan（2min）：demo 文件上传+校验、UI/footer、游客 vs 注册差异，收尾。
- **务必 live demo**（强制项，缺则 0）。

### 9.2 加分
- **排 Week 11 答辩** → +1。

### 9.3 每人 Q&A 备考（用自己的话，理解逻辑）
- Honghao：`UserCreationForm` 怎么扩展？密码找回 token 原理？`login_required` vs Mixin？
- Tianyang：`on_delete` 各选项区别？`UserPassesTestMixin.test_func` 怎么限作者？ListView 与手写 view 区别？
- Lei：`Q` 对象与 `filter` 链？`icontains` 命中什么？分页怎么做？
- Kun：session 存哪里？cookie 与 session 区别？跨天计数逻辑？context processor 作用？
- Zhihan：`FileField` vs `ImageField`？`clean_file` 怎么校验大小/类型？`MEDIA_ROOT`/`MEDIA_URL`？

---

## 10. 提交物清单（Brightspace）

- [ ] 一份 Word：建站步骤、选题动机、**成员分工表**、截图、**live 网站链接 + GitHub 链接**
- [ ] 单独上传 `views.py`、`models.py`、`forms.py`（**不要放进文件夹**）
- [ ] fixtures JSON + `loaddata` 说明
- [ ] 已加 `comp8347proj` 协作者

---

## 11. 成员贡献总表（再平衡后 · 已按当前代码实况）

> 排序按工作量从多到少。单元测试各写自己模块的那部分。

| 成员 | Models | Views | Forms | 模板 | 专属模块 |
|---|---|---|---|---|---|
| **Tianyang**（Models/CRUD/数据） | Category, Course, Resource | Resource Create/Update/Delete + download、CategoryListView、CourseListView、CategoryCreateView、CourseCreateView | ResourceForm, CategoryForm, CourseForm | resource_form, resource_confirm_delete, category_list, course_list, taxonomy_form, about | **admin.py（全部模型）· sample_data fixtures** |
| **Honghao**（Auth/协调） | UserProfile（+ profile signal） | RegisterView, ProfileView, ProfileUpdateView, TeamView | RegisterForm, UserProfileForm ＋ 3 个 Bootstrap auth 表单 | login / register / logged_out / password_reset×4(+email/subject) / profile / profile_form / team | auth URL 覆盖 |
| **Zhihan**（UI/上传/测试） | Comment, Favourite | HomeView, toggle_favourite, add_comment, FavouritesListView | CommentForm（+ BootstrapMixin） | home, favourites, base, partials/_resource_card, partials/_form | **theme.css + Lucide 设计系统 · validators.py · tests.py 框架** |
| **Lei**（Search/CBV） | Tag, SavedSearch | ResourceListView, ResourceDetailView, save_search, SavedSearchListView, delete_saved_search | SearchFilterForm, SavedSearchForm | resource_list, resource_detail, saved_searches | — |
| **Kun**（Sessions/History） | UserHistory, DailyVisitLog, ContactMessage | HistoryView, clear_history, ContactView | ContactForm | history, contact | **middleware.py · context_processors.py** |

**再平衡的三处调整**：Contact 整块（模型+表单+视图+模板）Honghao→**Kun**；About→**Tianyang**；Team→**Honghao**。新增真功能：Tianyang 的课程/分类目录 + 管理页，Lei 的 SavedSearch 保存/列表。

> 每人在 models/views/forms/templates 都有实质产出（满足 Note 2）；

---

## 12. 立即行动（本周 W6）
1. `django-admin startproject coursesharehub` + `python manage.py startapp hub`
2. 建仓库、加 `.gitignore`、加协作者 `comp8347proj`、提交本 `PROJECT_PLAN.md`
3. 五人各建自己的第一个 model 并各自提交一次（形成多人多分支的早期历史）
4. 搭 `base.html`（navbar+footer 骨架）

**红线**：全部代码自己写、自己懂（Note 3 + viva 最高权重）。本文档只是设计蓝图。
