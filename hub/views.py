"""
CourseShare Hub — views.

Reference implementation. The viva/Q&A (highest-weight grading item) tests that
YOU understand these — CBVs, mixins, sessions, auth, and the ORM queries. Read
each view, then re-author it in your own words. Full spec: docs/PROJECT_PLAN.md.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q, F, Count
from django.views.generic import (
    TemplateView, CreateView, UpdateView, DeleteView, ListView, DetailView,
)

from .forms import (
    RegisterForm, UserProfileForm, ContactForm, SearchFilterForm, ResourceForm, CommentForm,
    CategoryForm, CourseForm, SavedSearchForm,
)
from .models import UserProfile, Resource, UserHistory, Favourite, Category, Course, SavedSearch


class HomeView(TemplateView):
    """Public landing page (guests + registered).  OWNER: Zhihan — §3."""
    template_name = 'hub/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = (Category.objects
                             .annotate(n=Count('resources'))
                             .order_by('-n', 'name')[:6])
        ctx['recent'] = (Resource.objects.filter(is_public=True)
                         .select_related('category', 'course', 'uploader')
                         .order_by('-created_at')[:6])
        ctx['total_resources'] = Resource.objects.filter(is_public=True).count()
        ctx['total_courses'] = Course.objects.count()
        return ctx


# ============================================================================
#  Honghao — Authentication / Profile  (§5.1)  (Contact moved to Kun)
#  login / logout / password-reset are Django's built-in views, wired in the
#  project urls.py.  The views below are the custom parts.
# ============================================================================
class RegisterView(CreateView):
    """Create an account, then log the new user straight in."""
    form_class = RegisterForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('home')

    def dispatch(self, request, *args, **kwargs):
        # An already-logged-in user has no reason to see the register page.
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)   # saves the User -> self.object
        login(self.request, self.object)      # a UserProfile is created by signal
        messages.success(self.request, 'Welcome to CourseShare Hub! Your account is ready.')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """The logged-in user's own profile, with their uploads and favourites."""
    template_name = 'hub/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        ctx['profile'] = profile
        ctx['resources'] = user.resources.all()[:20]
        ctx['favourites'] = user.favourites.select_related('resource')[:20]
        return ctx


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Edit the current user's profile (avatar upload happens here)."""
    form_class = UserProfileForm
    template_name = 'hub/profile_form.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated.')
        return super().form_valid(form)


# ============================================================================
#  Lei — Browse: search + dropdown filters  (§5.3)
# ============================================================================
class ResourceListView(ListView):
    """The resource index, as a class-based ListView. Handles keyword search,
    four dropdown filters, guest-vs-member visibility, and pagination."""
    model = Resource
    template_name = 'hub/resource_list.html'
    context_object_name = 'resources'
    paginate_by = 6

    # 链式构建 queryset
    def get_queryset(self):
        # 性能：select_related（FK，SQL JOIN 一次取完）+ prefetch_related（M2M tags，另一条查询）→ 避免模板循环里的 N+1 查询。
        qs = (Resource.objects
              .select_related('course', 'category', 'uploader')
              .prefetch_related('tags'))
        # Guests only see public resources (registered-vs-guest difference, §5.6).
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_public=True)

        self.form = SearchFilterForm(self.request.GET or None)
        if self.form.is_valid():
            cd = self.form.cleaned_data
            if cd.get('q'):
                qs = qs.filter(
                    Q(title__icontains=cd['q'])
                    | Q(description__icontains=cd['q'])
                    | Q(tags__name__icontains=cd['q'])
                ).distinct() # 因为跨了 M2M（tags），一条资源多个 tag 会产生重复行，所以末尾 .distinct() 去重。
                self._record_search(cd['q'])
            if cd.get('course'):
                qs = qs.filter(course=cd['course'])
            if cd.get('category'):
                qs = qs.filter(category=cd['category'])
            if cd.get('file_type'):
                qs = qs.filter(file_type=cd['file_type'])
            if cd.get('sort'):
                qs = qs.order_by(cd['sort'])
        return qs

    # 搜一次就把关键词塞进 session['recent_searches']（最多 10 个，去重后插到最前），登录用户还写一条 UserHistory。
    def _record_search(self, keyword):
        """Keep recent search keywords in the session (Kun's History page reads these)."""
        searches = self.request.session.get('recent_searches', [])
        if keyword in searches:
            searches.remove(keyword)
        searches.insert(0, keyword)
        self.request.session['recent_searches'] = searches[:10]
        if self.request.user.is_authenticated:
            UserHistory.objects.create(
                user=self.request.user, action=UserHistory.Action.SEARCH, keyword=keyword,
            )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = self.form
        return ctx


class ResourceDetailView(DetailView):
    """A single resource, as a class-based DetailView. Bumps the view counter
    and records the visit in the session's 'recently viewed' list."""
    model = Resource
    template_name = 'hub/resource_detail.html'
    context_object_name = 'resource'

    def get_queryset(self):
        qs = (Resource.objects
              .select_related('course', 'category', 'uploader')
              .prefetch_related('tags', 'comments__author'))
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_public=True)
        return qs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Atomic +1 that does NOT run save() (so updated_at is left untouched).
        Resource.objects.filter(pk=obj.pk).update(views_count=F('views_count') + 1)
        obj.views_count += 1
        self._track_recently_viewed(obj)
        return obj

    def _track_recently_viewed(self, obj):
        viewed = self.request.session.get('recently_viewed', [])
        if obj.pk in viewed:
            viewed.remove(obj.pk)
        viewed.insert(0, obj.pk)
        self.request.session['recently_viewed'] = viewed[:10]
        if self.request.user.is_authenticated:
            UserHistory.objects.create(
                user=self.request.user, action=UserHistory.Action.VIEW, resource=obj,
            )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['comment_form'] = CommentForm()
        if self.request.user.is_authenticated:
            ctx['is_favourited'] = self.object.favourited_by.filter(user=self.request.user).exists()
        return ctx


@login_required
def save_search(request):
    """Save the current search + filter combination for the user.  Owner: Lei."""
    if request.method == 'POST':
        form = SavedSearchForm(request.POST)
        if form.is_valid():
            saved = form.save(commit=False) # 用 form.save(commit=False) 先拿到对象但不入库，补上 saved.user = request.user，再 .save()。为什么 commit=False？ 因为 user 不在表单里（不能让前端伪造别人的 user），必须服务端注入。
            saved.user = request.user
            saved.save()
            messages.success(request, 'Search saved.')
    return redirect('saved_searches')


class SavedSearchListView(LoginRequiredMixin, ListView):
    """The current user's saved searches.  Owner: Lei."""
    template_name = 'hub/saved_searches.html'
    context_object_name = 'saved_searches'

    def get_queryset(self):
        return self.request.user.saved_searches.select_related('course', 'category')


@login_required
def delete_saved_search(request, pk):
    """Remove one saved search.  Owner: Lei."""
    if request.method == 'POST':
        request.user.saved_searches.filter(pk=pk).delete() # 在用户自己的关系集合里过滤，别人的 pk 删不到，这是很干净的权限隔离写法（不需要额外的 owner 检查）。
        messages.info(request, 'Saved search removed.')
    return redirect('saved_searches')


# ============================================================================
#  Tianyang — Resource CRUD  (§5.2)
# ============================================================================
class OwnerRequiredMixin(UserPassesTestMixin):
    """Only the resource's uploader may edit or delete it (else 403 Forbidden)."""
    raise_exception = True

    def test_func(self):
        return self.get_object().uploader == self.request.user


class ResourceCreateView(LoginRequiredMixin, CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'hub/resource_form.html'

    def form_valid(self, form):
        form.instance.uploader = self.request.user    # the current user owns it
        response = super().form_valid(form)           # saves -> self.object
        UserHistory.objects.create(
            user=self.request.user, action=UserHistory.Action.UPLOAD, resource=self.object,
        )
        messages.success(self.request, 'Your resource has been uploaded.')
        return response
    # success_url is provided by Resource.get_absolute_url()


class ResourceUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'hub/resource_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Your resource has been updated.')
        return super().form_valid(form)


class ResourceDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Resource
    template_name = 'hub/resource_confirm_delete.html'
    success_url = reverse_lazy('resource_list')

    def form_valid(self, form):
        messages.success(self.request, 'Your resource has been deleted.')
        return super().form_valid(form)


def resource_download(request, pk):
    """Increment the download counter, record history, then hand over the file."""
    resource = get_object_or_404(Resource, pk=pk)
    if not resource.is_public and not request.user.is_authenticated:
        return redirect('login')
    Resource.objects.filter(pk=pk).update(download_count=F('download_count') + 1)
    if request.user.is_authenticated:
        UserHistory.objects.create(
            user=request.user, action=UserHistory.Action.DOWNLOAD, resource=resource,
        )
    return redirect(resource.file.url)


# ---- Tianyang — Course / Category browse + management (§5.2) ---------------
class CategoryListView(ListView):
    """Directory of all categories with resource counts."""
    template_name = 'hub/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.annotate(n=Count('resources')).order_by('name')


class CourseListView(ListView):
    """Directory of all courses with resource counts."""
    template_name = 'hub/course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.annotate(n=Count('resources')).order_by('code')


class CategoryCreateView(LoginRequiredMixin, CreateView):
    form_class = CategoryForm
    template_name = 'hub/taxonomy_form.html'
    success_url = reverse_lazy('category_list')
    extra_context = {'kind': 'category'}

    def form_valid(self, form):
        messages.success(self.request, 'Category added.')
        return super().form_valid(form)


class CourseCreateView(LoginRequiredMixin, CreateView):
    form_class = CourseForm
    template_name = 'hub/taxonomy_form.html'
    success_url = reverse_lazy('course_list')
    extra_context = {'kind': 'course'}

    def form_valid(self, form):
        messages.success(self.request, 'Course added.')
        return super().form_valid(form)


# ============================================================================
#  Kun — Sessions / Cookies / History  (§5.4)
# ============================================================================
class HistoryView(LoginRequiredMixin, TemplateView):
    """Shows the user's activity: today's/total visits (cookie), visits-per-day
    (DB), recently viewed + recent searches (session), and a logged-action feed."""
    template_name = 'hub/history.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        session = self.request.session

        # 'recently_viewed' holds resource ids, newest first — keep that order.
        viewed_ids = session.get('recently_viewed', [])
        resources = list(Resource.objects.filter(pk__in=viewed_ids))
        resources.sort(key=lambda r: viewed_ids.index(r.pk))

        ctx['recently_viewed'] = resources
        ctx['recent_searches'] = session.get('recent_searches', [])
        ctx['daily_logs'] = self.request.user.visit_logs.all()[:14]
        ctx['history'] = self.request.user.history.select_related('resource')[:30]
        return ctx


def clear_history(request):
    """Clear the session-based browsing history (recently viewed + searches)."""
    if request.method == 'POST':
        request.session.pop('recently_viewed', None)
        request.session.pop('recent_searches', None)
        messages.info(request, 'Your browsing history has been cleared.')
    return redirect('history')


class ContactView(CreateView):
    """Contact Us — saves a ContactMessage and thanks the visitor.  Owner: Kun."""
    form_class = ContactForm
    template_name = 'hub/contact.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        messages.success(self.request, 'Thanks! Your message has been sent.')
        return super().form_valid(form)


# ============================================================================
#  Zhihan — Comments, Favourites, static pages  (§5.5)
# ============================================================================
@login_required
def toggle_favourite(request, pk):
    """Add the resource to favourites, or remove it if already favourited."""
    resource = get_object_or_404(Resource, pk=pk)
    fav, created = Favourite.objects.get_or_create(user=request.user, resource=resource)
    if created:
        UserHistory.objects.create(
            user=request.user, action=UserHistory.Action.FAVOURITE, resource=resource)
        messages.success(request, 'Added to your favourites.')
    else:
        fav.delete()
        messages.info(request, 'Removed from your favourites.')
    return redirect('resource_detail', pk=pk)


@login_required
def add_comment(request, pk):
    """Post a comment on a resource."""
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.resource = resource
            comment.author = request.user
            comment.save()
            messages.success(request, 'Your comment has been posted.')
        else:
            messages.error(request, 'Your comment could not be posted.')
    return redirect('resource_detail', pk=pk)


class FavouritesListView(LoginRequiredMixin, ListView):
    template_name = 'hub/favourites.html'
    context_object_name = 'favourites'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.favourites.select_related('resource', 'resource__category')


class AboutView(TemplateView):
    """About page.  Owner: Tianyang (moved for balance)."""
    template_name = 'hub/about.html'


class TeamView(TemplateView):
    """Team page.  Owner: Honghao (moved for balance)."""
    template_name = 'hub/team.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['members'] = [
            {'name': 'Honghao Zhang', 'role': 'Auth & Project Coordination',
             'detail': 'Registration, login/logout, forgot password, user profile.'},
            {'name': 'Tianyang Ren', 'role': 'Resource Models & CRUD',
             'detail': 'Course/Category/Resource models, create/read/update/delete, relationships.'},
            {'name': 'Lei Jiang', 'role': 'Search, Filter & Class-Based Views',
             'detail': 'Keyword search, dropdown filters, class-based list and detail views.'},
            {'name': 'Kun Lan', 'role': 'Sessions, Cookies & History',
             'detail': 'Visit tracking, recently viewed, search history, History page.'},
            {'name': 'Zhihan Zhang', 'role': 'UI/UX, Upload & Testing',
             'detail': 'Bootstrap layout, file upload, About/Contact pages, testing.'},
        ]
        return ctx
