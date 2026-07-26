# CourseShare Hub — 代码详解 (CODE GUIDE)

> 面向：全组 5 人 + viva 备考。逐文件讲功能、逐功能讲实现、逐人讲分工、并说明怎么用。
> 配套文档：`docs/PROJECT_PLAN.md`（分工表 §11 / 评分对策 §0）。
> ⚠️ Note 3：这是参考实现，**每人必须自己读懂、用自己的话重写并能当面解释**。

---

## 目录
1. 项目总览与请求生命周期
2. 目录结构 · 每个文件的职责
3. `settings.py` 配置逐项
4. URL 路由（project + app）
5. 数据模型 `models.py`
6. 表单 `forms.py`
7. 视图 `views.py`
8. 会话/Cookie：`middleware.py` + `context_processors.py`
9. 文件校验 `validators.py`
10. 模板系统（`base.html` / partials / 各页面）
11. 前端设计系统 `theme.css` + Lucide 图标
12. 后台 `admin.py`
13. 初始数据 `fixtures/sample_data.json`
14. 测试 `tests.py`
15. **需求 → 实现 映射表**
16. **人员分工 → 文件对照**
17. 如何运行与逐功能使用说明
18. viva Q&A 备考（每人）

---

## 1. 项目总览与请求生命周期

**是什么**：一个 Django 课程资源共享平台。游客可浏览/搜索公开资源；注册用户可上传、评论、收藏、看历史、保存搜索；管理员用 Django admin 管一切。

**技术栈**：Python 3.14 · Django 6.0 · SQLite（开发）· JSON fixtures（初始数据）· Bootstrap 5 + Lucide 图标（**本地托管**，无 CDN）。

**一次请求怎么走（以打开某资源详情为例）**：
```
浏览器 GET /resources/5/
  → coursesharehub/urls.py 匹配到 hub.urls
  → hub/urls.py 匹配 'resources/<int:pk>/' → ResourceDetailView
  → 中间件链：Session → Auth → ... → VisitCountMiddleware（记访问）
  → View.get_queryset()（游客只给 is_public=True）→ get_object()（浏览量+1、写 session）
  → render 'hub/resource_detail.html'（extends base.html）
  → context_processors.visit_counter 注入 visit_stats
  → 返回 HTML；VisitCountMiddleware 在 response 上写 cookie
```

**核心设计约束**（都对着评分表）：
- `index` 用 `ListView`、`detail` 用 `DetailView`（要求强制的 class-based views）。
- 初始数据用 JSON fixtures（要求 "database in JSON"）。
- 忘记密码用 console 邮件后端（零外部 API，离线可 demo）。
- 前端资源全部 `static/` 本地托管（离线 demo 不挂 + "minimize external"）。

---

## 2. 目录结构 · 每个文件的职责

```
CourseShareHub/
├─ manage.py                      Django 命令入口（runserver/migrate/test…）
├─ requirements.txt               依赖：Django 6.0.6, Pillow（ImageField 用）
├─ .gitignore                     忽略 venv/db.sqlite3/media/docs 等
├─ README.md                      安装与运行说明
├─ db.sqlite3                     开发数据库（gitignore，不进仓库）
│
├─ coursesharehub/                ★ 项目配置包
│  ├─ settings.py                 全局配置（apps/中间件/模板/静态/邮件…）
│  ├─ urls.py                     根路由：admin + auth 覆盖 + include hub
│  ├─ wsgi.py / asgi.py           部署入口（PythonAnywhere 用 wsgi）
│
├─ hub/                           ★ 主 app（几乎所有业务代码）
│  ├─ models.py                   11 个数据模型 + 自动建 profile 的 signal
│  ├─ views.py                    所有视图（CBV + FBV）
│  ├─ forms.py                    所有表单 + BootstrapMixin
│  ├─ urls.py                     app 内路由表
│  ├─ admin.py                    11 个模型的后台注册
│  ├─ validators.py              文件上传校验（大小/扩展名）
│  ├─ middleware.py              每日访问计数（cookie + DailyVisitLog）
│  ├─ context_processors.py      把 visit_stats 注入所有模板
│  ├─ tests.py                    17+ 单元测试
│  ├─ migrations/                 0001_initial, 0002_alter_resource_file
│  ├─ fixtures/sample_data.json   初始数据（分类/课程/标签/用户/资源）
│  └─ templates/hub/*.html        本 app 页面模板
│
├─ templates/                     ★ 项目级模板
│  ├─ base.html                   全站骨架（navbar + footer + 图标脚本）
│  ├─ partials/_form.html         Bootstrap 表单字段渲染片段
│  ├─ partials/_resource_card.html 资源卡片片段（首页/列表复用）
│  └─ registration/*.html         登录/注册/登出/找回密码（9 个）
│
├─ static/                        ★ 本地静态资源
│  ├─ css/theme.css               自定义设计系统（配色/组件）
│  ├─ css/bootstrap.min.css       Bootstrap 5（本地）
│  └─ js/bootstrap.bundle.min.js, js/lucide.min.js
│
└─ media/                         用户上传（resources/、avatars/；gitignore）
```

---

## 3. `settings.py` 配置逐项（`coursesharehub/settings.py`）

| 配置 | 值 | 作用 |
|---|---|---|
| `INSTALLED_APPS` | +`'hub'` | 注册主 app（模型/模板/静态才会被发现） |
| `MIDDLEWARE` | 末尾 +`hub.middleware.VisitCountMiddleware` | 放在 Session/Auth 之后，才能用 `request.user`/`session` |
| `TEMPLATES.DIRS` | `[BASE_DIR/'templates']` | 让 Django 找到项目级 `base.html`、`registration/` |
| `TEMPLATES.context_processors` | +`hub.context_processors.visit_counter` | 每个模板都能拿到 `visit_stats` |
| `DATABASES` | SQLite `db.sqlite3` | 开发库；初始数据靠 fixtures |
| `TIME_ZONE` | `America/Toronto` | 温莎本地时区（时间戳按本地显示） |
| `STATIC_URL`/`STATICFILES_DIRS`/`STATIC_ROOT` | `static/` · `[BASE_DIR/'static']` · `staticfiles/` | 开发从 `static/` 提供；部署 `collectstatic` 收到 `staticfiles/` |
| `MEDIA_URL`/`MEDIA_ROOT` | `media/` · `BASE_DIR/'media'` | 上传文件的 URL 与磁盘位置 |
| `LOGIN_URL`/`LOGIN_REDIRECT_URL`/`LOGOUT_REDIRECT_URL` | `login`/`home`/`home` | 未登录跳 login；登录/登出后回 home |
| `EMAIL_BACKEND` | `console.EmailBackend` | 找回密码把重置链接**打到终端**，无需外部邮箱 |
| `MESSAGE_TAGS` | `{ERROR: 'danger'}` | 让 `alert-{{ tag }}` 渲染成 Bootstrap 的 `alert-danger` |

> 生产注意（部署前）：`DEBUG=False`、`ALLOWED_HOSTS=['<你的域名>']`、换掉 `SECRET_KEY`、跑 `collectstatic`。

---

## 4. URL 路由

**根路由 `coursesharehub/urls.py`**：先覆盖三个内置 auth 视图（换成 Bootstrap 表单），再 include 其余：
```python
path('accounts/login/', LoginView.as_view(authentication_form=BootstrapAuthenticationForm), name='login'),
path('accounts/password_reset/', PasswordResetView.as_view(form_class=BootstrapPasswordResetForm), name='password_reset'),
path('accounts/reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(form_class=BootstrapSetPasswordForm), name='password_reset_confirm'),
path('accounts/', include('django.contrib.auth.urls')),   # logout / *_done / *_complete
path('', include('hub.urls')),
if DEBUG: urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)  # 开发期服务上传文件
```
> 覆盖放在 `include(auth.urls)` **之前**——URL 从上往下匹配，先命中我们的，但 name 沿用内置的（`{% url 'login' %}` 照常）。

**app 路由 `hub/urls.py`（完整表）**：

| 路径 | name | 视图 | 谁 |
|---|---|---|---|
| `/` | home | HomeView | Zhihan |
| `/register/` | register | RegisterView | Honghao |
| `/profile/` `/profile/edit/` | profile / profile_edit | Profile(Update)View | Honghao |
| `/contact/` | contact | ContactView | Kun |
| `/resources/` | resource_list | ResourceListView | Lei |
| `/resources/new/` | resource_create | ResourceCreateView | Tianyang |
| `/resources/<pk>/` | resource_detail | ResourceDetailView | Lei |
| `/resources/<pk>/edit/` `delete/` | resource_update / resource_delete | Resource(Update/Delete)View | Tianyang |
| `/resources/<pk>/download/` | resource_download | resource_download | Tianyang |
| `/categories/` `/categories/new/` | category_list / category_create | Category(List/Create)View | Tianyang |
| `/courses/` `/courses/new/` | course_list / course_create | Course(List/Create)View | Tianyang |
| `/saved-searches/` `save/` `<pk>/delete/` | saved_searches / save_search / delete_saved_search | SavedSearch* | Lei |
| `/history/` `/history/clear/` | history / clear_history | HistoryView / clear_history | Kun |
| `/resources/<pk>/favourite/` `comment/` | toggle_favourite / add_comment | FBV | Zhihan |
| `/favourites/` | favourites | FavouritesListView | Zhihan |
| `/about/` `/team/` | about / team | About/TeamView | Tianyang / Honghao |
| `/accounts/login,logout,password_reset*` | (内置 name) | Django auth 视图 | Honghao |
| `/admin/` | — | Django admin | Tianyang（配置） |

---

## 5. 数据模型 `hub/models.py`（11 个模型）

顶部：`USER = settings.AUTH_USER_MODEL`（最佳实践，FK 都指向它）。

### Tianyang：Category / Course / Resource
- **Category**：`name(unique)` `slug(auto)` `description` `icon`。`save()` 里 `slugify(name)` 自动填 slug；`Meta.verbose_name_plural='categories'`（否则后台显示 "Categorys"）。
- **Course**：`code` `title` `description` `term`；`unique_together=('code','term')`（同学期同代码不重复）。
- **Resource（核心模型）**：
  - 关系：`uploader→User(CASCADE)`、`course→Course(SET_NULL, 可空)`、`category→Category(PROTECT)`、`tags→Tag(M2M)`。
    - **on_delete 三种要会讲**：CASCADE=作者删了资源跟着删；SET_NULL=课程删了资源留着(course 变空)；PROTECT=分类下还有资源就不许删分类。
  - `file=FileField(upload_to='resources/%Y/%m/', validators=[大小, 扩展名])`。
  - `file_type` 用 `TextChoices`（PDF/DOC/PPT/IMG/OTHER），在 `save()` 里按扩展名**自动识别**。
  - `is_public`（游客可见性）、`views_count`、`download_count`、`created_at/updated_at`。
  - `get_absolute_url()` → `reverse('resource_detail', pk)`，Create/Update 成功后自动跳详情。

### Lei：Tag / SavedSearch
- **Tag**：`name(unique)` `slug(auto)`；被 Resource 以 M2M 引用。
- **SavedSearch**：`user` + `keyword/course/category/file_type`——保存一组搜索条件供重跑。

### Honghao：UserProfile（+ signal）
- **UserProfile**：`OneToOne→User`，加 `avatar(ImageField)` `student_id` `program` `bio`。
- **signal（文件底部）**：`@receiver(post_save, sender=USER)` 在**新建**用户时 `get_or_create` 一个 profile；`raw=True`（loaddata 时）直接 return，避免和 fixtures 打架。

### Kun：UserHistory / DailyVisitLog / ContactMessage
- **UserHistory**：`user` + `action`(VIEW/DOWNLOAD/SEARCH/UPLOAD/FAVOURITE 的 TextChoices) + `resource(可空)` + `keyword`。持久记录用户行为，History 页读它。
- **DailyVisitLog**：每人每天一行 `visit_count`。`user`（会员）或 `session_key`（游客）二选一，另一个留 NULL；`unique_together=[('user','date'),('session_key','date')]`——因为 SQL 里 NULL≠NULL，两条约束不会互相误伤（**viva 常问**）。
- **ContactMessage**：`name/email/subject/body/is_read`——Contact 表单入库。

### Zhihan：Comment / Favourite
- **Comment**：`resource→Resource(CASCADE)` + `author→User` + `body`。
- **Favourite**：`user` + `resource`，`unique_together=('user','resource')`——同一资源不能重复收藏（配合视图的 `get_or_create`）。

> 改了模型 → `python manage.py makemigrations && migrate`。当前迁移：`0001_initial`、`0002_alter_resource_file`（加校验器那次）。

---

## 6. 表单 `hub/forms.py`

- **`BootstrapMixin`（关键工具）**：`__init__` 里遍历 `self.fields`，给每个 widget 自动加 class（`form-control` / `form-select` / `form-check-input`）。放在继承链**最前面**（协作式多继承）。因此模板里不用手写 class。
- **Honghao**：`RegisterForm`(继承 `UserCreationForm`，加必填唯一 email，`clean_email` 查重)、`UserProfileForm`。
- **Tianyang**：`ResourceForm`（`uploader`/`file_type` 不在表单里，由视图和模型 `save()` 定）、`CategoryForm`、`CourseForm`。
- **Lei**：`SearchFilterForm`（`q` + 4 个下拉 `course/category/file_type/sort`，全 `required=False`——空搜索=列全部）、`SavedSearchForm`（ModelForm，被"保存搜索"按钮的隐藏字段填充）。
- **Kun**：`ContactForm`。
- **Zhihan**：`CommentForm`。
- 末尾：`BootstrapAuthenticationForm / BootstrapPasswordResetForm / BootstrapSetPasswordForm`——给 Django 内置 auth 表单套上 Bootstrap（根路由里指定给对应视图）。

> `clean_*` 校验是 **Testing(/2)** 的得分点：重复 email、非法/超大文件都在这里拦截并回显错误。

---

## 7. 视图 `hub/views.py`

**类视图 vs 函数视图**：需要"列表/详情/表单增删改"的用 CBV（少写样板）；轻量动作（收藏切换、加评论、保存搜索、清历史、下载）用 `@login_required` 的 FBV。

### Zhihan — HomeView（TemplateView）
`get_context_data` 里用 ORM 组装首页：`categories`（按资源数排序，`annotate(n=Count('resources'))`）、`recent`（最新 6 个公开资源，`select_related` 减查询）、`total_resources`/`total_courses` 统计。

### Honghao — 认证
- `RegisterView(CreateView)`：`dispatch` 里已登录就跳 home；`form_valid` 先存用户再 `login()` 自动登录（profile 由 signal 建）。
- `ProfileView(LoginRequiredMixin, TemplateView)`：展示当前用户的 profile + 上传 + 收藏。
- `ProfileUpdateView(LoginRequiredMixin, UpdateView)`：`get_object` 返回当前用户的 profile（头像上传走这里，模板需 `enctype`）。
- login/logout/找回密码 = Django 内置视图（根路由挂载 + `templates/registration/` 提供模板）。

### Lei — 浏览/搜索（**强制的 CBV**）
- `ResourceListView(ListView)` = **index**：`get_queryset` 里
  1. 游客只看 `is_public=True`；
  2. 用 `SearchFilterForm(request.GET)` 校验，`q` 用 `Q(title__icontains) | Q(description) | Q(tags__name) .distinct()`，下拉逐个 `filter`，`sort` 用 `order_by`；
  3. 有关键词就 `_record_search()` 写 session `recent_searches` + `UserHistory`；
  4. `paginate_by=6` 分页。
- `ResourceDetailView(DetailView)` = **detail**：`get_object` 用 `F('views_count')+1` **原子自增**浏览量（不走 `save()`，不动 `updated_at`），并把 id 压进 session `recently_viewed`；`get_context_data` 给评论表单 + `is_favourited`。
- `save_search` / `SavedSearchListView` / `delete_saved_search`：保存/列出/删除搜索条件。

### Tianyang — CRUD + 课程/分类管理
- `OwnerRequiredMixin(UserPassesTestMixin)`：`test_func` 判断 `资源.uploader == 当前用户`，`raise_exception=True`→非作者返回 **403**。
- `ResourceCreateView(LoginRequiredMixin, CreateView)`：`form_valid` 里把 `uploader` 设成当前用户、写 UPLOAD 历史。
- `ResourceUpdateView` / `ResourceDeleteView`（+`OwnerRequiredMixin`）：仅作者可改/删。
- `resource_download(FBV)`：`F('download_count')+1` 自增下载数、记历史，再重定向到文件。
- `CategoryListView`/`CourseListView`（目录，带 `Count` 计数）、`CategoryCreateView`/`CourseCreateView`（登录后新增，共用 `taxonomy_form.html`，靠 `extra_context={'kind':...}` 区分标题）。

### Kun — 会话/历史/联系
- `HistoryView(LoginRequiredMixin, TemplateView)`：拼 `recently_viewed`（按 session 顺序还原资源）、`recent_searches`、`daily_logs`（`user.visit_logs`）、`history`（`user.history`）。
- `clear_history(FBV)`：POST 清 session 两个键。
- `ContactView(CreateView)`：存 ContactMessage。

### Zhihan — 社交/静态页
- `toggle_favourite(FBV)`：`get_or_create` 收藏——已存在就删（切换），新建就写 FAVOURITE 历史。
- `add_comment(FBV)`：`CommentForm` 存评论（`author`/`resource` 视图里补）。
- `FavouritesListView`（我的收藏）、`AboutView`、`TeamView`（`members` 在 context 里硬编码）。

---

## 8. 会话/Cookie：`middleware.py` + `context_processors.py`（Kun · §5.4）

**为什么要中间件**：context processor 拿不到 response，**没法写 cookie**；写/刷新 cookie 必须在 middleware 的 response 阶段。

`VisitCountMiddleware.__call__`：
1. `_should_track`：只统计普通 GET（跳过 static/media/admin 和 AJAX）。
2. `_read_cookies`：读 `cs_last_visit`/`cs_daily_visits`/`cs_total_visits`；**同一天 +1，跨天归 1**；把 `{date, daily, total}` 挂到 `request.visit_stats`。
3. `get_response(request)` 生成响应。
4. `_write_cookies`：把三个计数写回 cookie（`max_age=1 年`, `samesite='Lax'`）。
5. `_write_db`：会员按 `user`、游客按 `session_key` `get_or_create` 当天的 `DailyVisitLog`，非新建则 `F('visit_count')+1`。

`context_processors.visit_counter(request)` → `{'visit_stats': request.visit_stats}`，于是任意模板（如 footer "You've visited N times today"）都能显示。**Session 部分**（`recently_viewed`/`recent_searches`）由 Lei 的列表/详情视图写入，History 页读出——这是 session 与 cookie 的分工。

> `settings.py` 里那条 `# TODO(Kun) ... no-op` 注释是**旧的**（功能已实现），提交前顺手删掉即可。

---

## 9. 文件校验 `hub/validators.py`（Zhihan · §5.5）
```python
MAX_UPLOAD_MB = 10
ALLOWED_EXTENSIONS = ['.pdf','.doc','.docx','.ppt','.pptx','.png','.jpg','.jpeg','.gif']
validate_file_size(value)      # >10MB 抛 ValidationError
validate_file_extension(value) # 不在白名单抛 ValidationError
```
挂在 `Resource.file` 的 `validators=[...]`。ModelForm 提交时经 `full_clean` 触发→**表单回显错误**，不会崩（Testing 边界项）。

---

## 10. 模板系统

- **`base.html`（全站骨架）**：`{% load static %}` + 本地 CSS/JS；白色 sticky navbar（`{% if user.is_authenticated %}` 决定游客/会员菜单）；flash 消息；`{% block content %}`；深色 footer；末尾 `<script>lucide.createIcons()</script>` 把所有 `<i data-lucide="...">` 渲染成 SVG。
- **`partials/_form.html`**：循环 `form` 字段，输出 Bootstrap 标签/输入/错误；checkbox 特殊处理。用法：`{% include 'partials/_form.html' %}` 或 `with form=xxx`。
- **`partials/_resource_card.html`**：资源卡片（文件类型图标 + 分类 chip + meta），首页与列表页复用。
- **`registration/*.html`**（Honghao，9 个）：login/register/logged_out/password_reset_form/done/confirm/complete + password_reset_email（邮件正文，含 `{% url 'password_reset_confirm' uidb64=uid token=token %}`）+ password_reset_subject（主题）。
- **`hub/*.html`**：home、resource_list/detail/form/confirm_delete、category_list、course_list、taxonomy_form、history、profile、profile_form、contact、favourites、saved_searches、about、team。

**Django 模板小坑（viva 可能问）**：`{# #}` 注释**只能单行**（跨行会把里面的 `{% %}` 当真标签执行）；多行注释用 `{% comment %}…{% endcomment %}`。

---

## 11. 前端设计系统 `static/css/theme.css` + Lucide（Zhihan · §6）

- **设计令牌**：`:root` 里定义品牌靛蓝 `--brand:#4f46e5`、slate 中性色、圆角、阴影、focus ring；并覆写 Bootstrap 变量（`--bs-primary` 等）。
- **组件**：`.app-navbar`（白色+底边）、`.brand-mark`/`.icon-box`（图标底座）、`.btn-*`（圆角+悬停）、`.card`（悬停上浮）、`.chip`（药丸标签）、`.hero`（渐变）、`.stat`（数字磁贴）、`.app-footer`（深色+社交圆钮）。
- **Lucide 用法**：`<i data-lucide="search"></i>` → `lucide.createIcons()` 在页面加载后替换为 SVG，`stroke=currentColor` 随字色变。**本地托管**（`static/js/lucide.min.js`）保证离线 demo 不挂。

---

## 12. 后台 `admin.py`（Tianyang）
11 个模型全部注册，配 `list_display`/`list_filter`/`search_fields`；`Category/Tag` 用 `prepopulated_fields` 自动填 slug；`ResourceAdmin` 用 `autocomplete_fields`、`filter_horizontal`（tags）、`readonly_fields`（计数/时间）。用途：`createsuperuser` 后访问 `/admin/` 快速造数据、看 ContactMessage 等。

---

## 13. 初始数据 `hub/fixtures/sample_data.json`（Tianyang · "database in JSON"）
JSON 格式的分类/课程/标签/用户/资源种子。加载：
```bash
python manage.py loaddata sample_data
```
样例登录：`hzhang` / `tren` / `ljiang`，密码 `CourseHub2026`（见 README）。
> 满足要求两点：初始数据用 **fixtures** 加载；数据可用 `dumpdata hub --indent 2 > 备份.json` 导出为 JSON。

---

## 14. 测试 `hub/tests.py`（Zhihan 框架 + 各人补自己模块）
`@override_settings(MEDIA_ROOT=临时目录)` 让上传不污染真实 `media/`。分 4 组，共 17+：
- **ModelTests**：slug 自动、profile signal、file_type 自动识别、Favourite 唯一约束。
- **FormTests**：重复 email 被拒、非法扩展名被拒、超大文件被拒。
- **ViewAccessTests**：home/list 200、游客看不到私有(404)、详情浏览量+1、上传需登录(302)、仅作者可编辑(403/200)、空搜索提示、History 需登录、收藏切换、分类/课程目录 200、保存搜索建记录。
- **AuthFlowTests**：注册后自动登录、错误密码被拒。
运行：`python manage.py test`。

---

## 15. 需求 → 实现 映射表（对着题目要求逐条）

| 要求 | 在哪实现 | 怎么实现 |
|---|---|---|
| 登录/登出/**找回密码** | 根 `urls.py` + `registration/*` + settings 邮件后端 | Django 内置视图 + console 邮件（链接打到终端） |
| 注册（自定义） | `RegisterView` + `RegisterForm` | UserCreationForm 扩展 email；注册后自动登录 |
| Models/Forms/**CRUD** | `models.py` + `ResourceForm` + `Resource*View` | Resource 增删改查全用 CBV，作者权限用 Mixin |
| **class-based views**（index/detail） | `ResourceListView`/`ResourceDetailView` | 直接用 ListView/DetailView |
| **搜索 + 下拉过滤** | `ResourceListView.get_queryset` + `SearchFilterForm` | `Q` 关键词 + course/category/file_type/sort 四下拉 |
| **Session & Cookie 历史** | `middleware.py` + 列表/详情视图 + `HistoryView` | cookie 记每日访问；session 记最近浏览/搜索 |
| **文件上传** | `Resource.file` + `validators.py` + `enctype` 表单 | 上传 + 大小/类型校验；头像也走 ImageField |
| **游客 vs 注册** 界面差异 | 各视图 `is_public` 过滤 + Mixin + `base.html` 条件菜单 | 游客只看公开、不能上传/收藏/评论 |
| **搜索栏 + 下拉** | `base.html` 导航搜索 + 列表页过滤卡 | 顶部 `?q=` 提交到列表页 |
| **User History 区** | `HistoryView` + `history.html` | 每日访问次数 + 最近浏览/搜索 + 行为日志 |
| **Footer** | `base.html` footer | 4 列 + 社交图标 + 版权 |
| **Bootstrap 美化** | `theme.css` + 本地 Bootstrap | 统一设计系统 + Lucide 图标 |
| **JSON fixtures** | `fixtures/sample_data.json` | `loaddata sample_data` |
| 附加页 | `about.html`/`team.html`/`contact.html` | About/Team/Contact |
| GitHub 追踪 | 仓库 + 每人分支提交 | 见 PROJECT_PLAN §7（多周提交） |

---

## 16. 人员分工 → 文件对照（再平衡后，Tianyang 主力）

| 成员 | 主要文件/代码块 |
|---|---|
| **Tianyang** | `models.py`(Category/Course/Resource) · `views.py`(Resource CRUD + download + Category/Course List/Create) · `forms.py`(Resource/Category/Course) · `admin.py`(全部) · `fixtures/sample_data.json` · 模板 resource_form/confirm_delete/category_list/course_list/taxonomy_form/about |
| **Honghao** | `views.py`(Register/Profile/ProfileUpdate/Team) · `forms.py`(Register/UserProfile + 3 个 Bootstrap auth) · `models.py`(UserProfile + signal) · 根 `urls.py` auth 覆盖 · 模板 registration/*(9) + profile/profile_form/team |
| **Lei** | `views.py`(ResourceList/Detail + save/list/delete search) · `forms.py`(SearchFilter/SavedSearch) · `models.py`(Tag/SavedSearch) · 模板 resource_list/detail/saved_searches |
| **Kun** | `middleware.py` · `context_processors.py` · `views.py`(History/clear/Contact) · `forms.py`(Contact) · `models.py`(UserHistory/DailyVisitLog/ContactMessage) · 模板 history/contact |
| **Zhihan** | `theme.css` + Lucide 集成 + `base.html` + partials · `validators.py` · `tests.py` 框架 · `views.py`(Home/toggle_favourite/add_comment/Favourites) · `models.py`(Comment/Favourite) · 模板 home/favourites |

---

## 17. 如何运行与逐功能使用说明

**本地跑起来**（README 同步）：
```bash
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata sample_data            # 载入样例数据
python manage.py createsuperuser                 # 建管理员（可选）
python manage.py runserver                       # 打开 http://127.0.0.1:8000/
```
改了 CSS/模板看不到变化 → **Ctrl+F5 硬刷新**。

**各功能怎么用**：
- **注册/登录**：右上 Sign up → 自动登录；Login 页有"Forgot password?"。
- **忘记密码**：填邮箱提交 → **看 runserver 的终端**，里面打印重置链接 → 打开 → 设新密码。
- **浏览/搜索**：顶部搜索栏或 Browse 页；左侧过滤卡选 course/category/type/sort；登录后可"Save this search"。
- **上传**：登录后 Upload；选文件（非法/超大会报错）；上传后进详情页。
- **编辑/删除**：只有作者在自己的详情页能看到 Edit/Delete。
- **收藏/评论**：详情页（需登录）。
- **历史**：右上头像菜单 → My History（今日/累计访问、最近浏览/搜索、行为日志）。
- **管理**：`/admin/`（超级用户）管所有数据。

**跑测试**：`python manage.py test`。

---

## 18. viva Q&A 备考（每人至少能答自己这几条）

- **Tianyang**：`on_delete` 三种(CASCADE/SET_NULL/PROTECT)区别？`UserPassesTestMixin.test_func` 怎么限作者？`Count('resources')` 注解怎么算每分类资源数？fixtures 和 admin 的关系？
- **Honghao**：`UserCreationForm` 怎么扩展 email？找回密码的 token 流程？为什么用 console 邮件后端？`login()` 在注册里干嘛？
- **Lei**：`Q` 对象与 `.distinct()` 为什么需要？`icontains` 命中什么？`ListView.get_queryset` vs 手写视图？分页怎么保留过滤参数？
- **Kun**：cookie 与 session 区别？为什么计数要放中间件不放 context processor？`DailyVisitLog` 的双 `unique_together` + NULL 为什么不冲突？
- **Zhihan**：`FileField` 校验器怎么在表单回显错误？`BootstrapMixin` 原理？Lucide `createIcons()` 怎么工作、为什么本地托管？`@override_settings(MEDIA_ROOT=...)` 测试为什么这么写？

---

*本文件位于 `docs/`（已 gitignore，不进提交）。发全组直接传文件即可。*
