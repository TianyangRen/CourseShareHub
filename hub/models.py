"""
CourseShare Hub — data models.

Reference implementation (11 models, ~2 per member). READ IT, then re-author in
your own words: the viva checks that YOU understand FKs, on_delete, M2M,
unique_together, choices, and save() overrides. Design notes: docs/PROJECT_PLAN.md §2.
"""
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

from .validators import validate_file_size, validate_file_extension

# Referencing the User model via settings.AUTH_USER_MODEL (best practice) keeps
# FK relations valid even if a project later swaps in a custom user model.
USER = settings.AUTH_USER_MODEL


# ============================================================================
#  Tianyang — Category, Course, Resource  (§5.2 Models / CRUD)
# ============================================================================
class Category(models.Model):
    """A resource category, e.g. Notes, Labs, Slides, Past Exams."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50, blank=True,
        help_text="Optional Bootstrap Icons name, e.g. 'journal-text'.",
    )

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        # Auto-fill the slug from the name the first time it is saved.
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    """A university course that resources can belong to, e.g. COMP-8347."""
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    term = models.CharField(max_length=50, blank=True, help_text="e.g. Summer 2026")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']
        # The same course code should not be duplicated within one term.
        unique_together = ('code', 'term')

    def __str__(self):
        return f"{self.code} – {self.title}"


class Tag(models.Model):
    """A free-form label attached to resources (many-to-many). Owner: Lei."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True) # blank=True → 表单可空，save() 里自动生成

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) #覆写：slugify(self.name) 把 "Past Exams" → "past-exams"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Resource(models.Model):
    """An uploaded course resource (the central model of the app)."""

    class FileType(models.TextChoices):
        PDF = 'PDF', 'PDF'
        DOC = 'DOC', 'Document'
        PPT = 'PPT', 'Slides'
        IMG = 'IMG', 'Image'
        OTHER = 'OTHER', 'Other'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # If the uploader is deleted, their resources go too (CASCADE).
    uploader = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='resources')
    # Keep the resource if the course is removed (SET_NULL, so course is optional).
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='resources',
    )
    # Block deletion of a category that still has resources (PROTECT).
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='resources')
    tags = models.ManyToManyField(Tag, blank=True, related_name='resources') # M2M: a resource can have many tags, a tag can belong to many resources，tag.resources.all() 反查、resource.tags.all() 正查

    file = models.FileField(
        upload_to='resources/%Y/%m/',
        validators=[validate_file_size, validate_file_extension],
    )
    file_type = models.CharField(max_length=10, choices=FileType.choices, default=FileType.OTHER)

    # Public resources are visible to guests; private ones only to members (§5.6).
    is_public = models.BooleanField(default=True, help_text="Visible to guests?")
    views_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Auto-detect the file type from the extension when not set explicitly.
        if self.file and self.file_type == self.FileType.OTHER:
            name = self.file.name.lower()
            if name.endswith('.pdf'):
                self.file_type = self.FileType.PDF
            elif name.endswith(('.doc', '.docx')):
                self.file_type = self.FileType.DOC
            elif name.endswith(('.ppt', '.pptx')):
                self.file_type = self.FileType.PPT
            elif name.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                self.file_type = self.FileType.IMG
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('resource_detail', args=[self.pk])


# ============================================================================
#  Lei — Tag (above) + SavedSearch  (§5.3 Search / Filter)
# ============================================================================
class SavedSearch(models.Model):
    """A search + filter combination a member chose to save and re-run."""
    # 为什么 user 用 CASCADE 而 course/category 用 SET_NULL？ 因为保存搜索离开用户就没意义（级联删），但离开某个课程仍然有意义（保留记录，字段置空）
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='saved_searches') # 用户删了，他的保存搜索一起删
    keyword = models.CharField(max_length=200, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True) # 课程删了，保存搜索还在，只是 course 变 NULL
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    file_type = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user}: {self.keyword or 'filter'}"


# ============================================================================
#  Honghao — UserProfile  (§5.1 Auth / Profile)
# ============================================================================
class UserProfile(models.Model):
    """Extra per-user data attached one-to-one to the built-in User.

    Design decision — extend, don't replace: the assignment keeps Django's default
    auth User (which already handles username / email / hashed password / login)
    and hangs the app-specific fields off it through a OneToOneField. This is the
    standard "profile" pattern and is less risky than swapping in a custom user
    model, which would require rewiring auth from the start of the project.

    Key field notes:
      * OneToOneField → exactly one profile per user (a ForeignKey would allow
        many, a plain field none). `related_name='profile'` is what lets templates
        and views read the data back as `request.user.profile.bio`, etc.
      * on_delete=models.CASCADE → the profile's lifetime is tied to its user:
        delete the user and this row is deleted with them, so no orphan profiles
        are ever left pointing at a user that no longer exists.
      * Almost every field is blank=True → the profile is auto-created empty by
        the post_save signal below, and the user fills it in later on the edit
        form; nothing here is mandatory at sign-up time.
    """
    # The link back to auth.User. USER is settings.AUTH_USER_MODEL (see top of file).
    user = models.OneToOneField(USER, on_delete=models.CASCADE, related_name='profile')
    # ImageField needs the Pillow library installed; uploaded files are written to
    # MEDIA_ROOT/avatars/. null=True lets the DB column be empty, blank=True lets
    # the form field be left empty — you generally want BOTH on an optional file.
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    # Free-text fields; blank=True keeps them optional on the profile-edit form.
    # CharField needs max_length (DB varchar size); TextField is unbounded prose.
    student_id = models.CharField(max_length=20, blank=True)   # e.g. "110211732"
    program = models.CharField(max_length=100, blank=True)     # e.g. "MSc Computer Science"
    bio = models.TextField(blank=True)                          # short "about me" blurb
    # auto_now_add stamps the creation time ONCE on insert and never changes it
    # (contrast with auto_now, which would update on every save).
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Shown in the admin list and anywhere a UserProfile is printed.
        return f"{self.user.username}'s profile"


# ============================================================================
#  Kun — UserHistory, DailyVisitLog, ContactMessage  (§5.4 + Contact §5.5)
# ============================================================================
class UserHistory(models.Model):
    """A persistent record of a member's actions (for the History page).

    A database-backed "action log": who, when, and what action (view / download
    / search / upload / favourite). Unlike the temporary browsing list kept in
    the session, this table is persistent — the History page renders its
    "Action log" feed from it.
    """

    class Action(models.TextChoices):
        # TextChoices: the DB stores the short code on the left ('VIEW') while the
        # page shows the human label on the right ('Viewed'). Templates read the
        # label via get_action_display.
        VIEW = 'VIEW', 'Viewed'
        DOWNLOAD = 'DOWNLOAD', 'Downloaded'
        SEARCH = 'SEARCH', 'Searched'
        UPLOAD = 'UPLOAD', 'Uploaded'
        FAVOURITE = 'FAVOURITE', 'Favourited'

    # A log belongs to a user: delete the user and their logs go too (CASCADE).
    # related_name='history' lets user.history.all() reverse-query their records.
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=12, choices=Action.choices)
    # Resource is optional: SEARCH actions have none; and if a resource is deleted
    # SET_NULL keeps the log (nulling the resource) instead of losing the history.
    resource = models.ForeignKey(
        Resource, on_delete=models.SET_NULL, null=True, blank=True, related_name='history_entries',
    )
    keyword = models.CharField(max_length=200, blank=True)  # only SEARCH actions fill this
    created_at = models.DateTimeField(auto_now_add=True)  # set once on creation, never changes

    class Meta:
        ordering = ['-created_at']  # newest first, so the feed reads reverse-chronologically
        verbose_name_plural = 'user histories'  # admin plural, else it shows "historys"

    def __str__(self):
        return f"{self.user} {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"


class DailyVisitLog(models.Model):
    """One row per visitor per day, storing that day's visit count (care2-style).

    Either `user` (members) or `session_key` (guests) identifies the visitor;
    the other is left NULL. Because SQL treats NULLs as distinct, the two
    unique_together rules below never collide across the NULL column.

    "One row per visitor per day", storing that day's visit count (care2-style
    daily counting). The visitor is identified one of two ways: members by user,
    guests by session_key, with the other left NULL. The History page's "Visits
    per day" reads from this table.
    """
    # A member's log: delete the user and it goes too. Guest rows leave this NULL,
    # hence null=True.
    user = models.ForeignKey(USER, on_delete=models.CASCADE, null=True, blank=True, related_name='visit_logs')
    session_key = models.CharField(max_length=40, null=True, blank=True)  # guests identified by session id
    date = models.DateField()  # which day
    visit_count = models.PositiveIntegerField(default=1)  # how many visits that day

    class Meta:
        ordering = ['-date']  # most recent date first
        # Two uniqueness rules: one row per user per day; one row per guest
        # (session) per day. Key point: SQL treats NULLs as distinct, so guest
        # rows (user=NULL) never collide with each other, and member rows
        # (session_key=NULL) never collide either — the two rules don't clash.
        unique_together = [('user', 'date'), ('session_key', 'date')]

    def __str__(self):
        who = self.user or f"guest:{self.session_key}"  # show the user, else mark as a guest
        return f"{who} — {self.date}: {self.visit_count}"


class ContactMessage(models.Model):
    """A message submitted through the Contact Us form.  Owner: Kun.

    A single message saved when the Contact Us form is submitted. There is no
    user FK on purpose: guests can send a message without logging in, so it
    carries its own name/email fields to identify the sender.
    """
    name = models.CharField(max_length=100)
    email = models.EmailField()  # EmailField validates the address format
    subject = models.CharField(max_length=200)
    body = models.TextField()
    is_read = models.BooleanField(default=False)  # admin marks it read in the backend
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # newest messages first

    def __str__(self):
        return f"{self.subject} ({self.email})"


# ============================================================================
#  Zhihan — Comment, Favourite  (§5.5 social features around uploads)
# ============================================================================
class Comment(models.Model):
    """A comment left on a resource by a registered user."""
    # Both FKs use CASCADE: a comment has no meaning once either its resource or
    # its author is gone, so deleting either side should delete the comment too
    # (contrast with Resource.course, which uses SET_NULL because the resource
    # itself still makes sense with no course attached).
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Oldest-first, unlike most other models here: a comment thread reads
        # top-to-bottom in the order it was written, not newest-first.
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.resource}"


class Favourite(models.Model):
    """A user 'saving' a resource. unique_together stops duplicate favourites."""
    # related_name choices read naturally from both sides: user.favourites.all()
    # (what has this user saved?) and resource.favourited_by.all() (who saved
    # this resource?).
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='favourites')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='favourited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # DB-level guarantee that a (user, resource) pair can only exist once,
        # so toggle_favourite's get_or_create can never insert a duplicate row
        # even under a race (two rapid clicks / concurrent requests).
        unique_together = ('user', 'resource')

    def __str__(self):
        return f"{self.user} ♥ {self.resource}"


# ============================================================================
#  Signal: auto-create a UserProfile whenever a User is created.
#
#  What a signal is: Django "fires" post_save every time a model row is saved.
#  @receiver(post_save, sender=USER) subscribes this function to that event for
#  the User model, so the function runs automatically right after any User save.
#
#  Why do it here instead of in the register view: putting the creation in the
#  signal guarantees that EVERY new User gets a profile no matter how it was made
#  — the register form, the admin site, `createsuperuser`, a shell, or a data
#  migration — so code elsewhere can rely on `user.profile` always existing and
#  never hit a RelatedObjectDoesNotExist / 404.
#
#  The three guards below, in order:
#    * raw=True  → we are inside `loaddata` (loading fixtures). We return early so
#                  the fixtures themselves stay the single source of truth and we
#                  don't fight them by inserting extra rows.
#    * created   → True only on INSERT (a brand-new user). Editing an existing
#                  user re-fires post_save with created=False, and we skip then so
#                  we never wipe or duplicate an existing profile.
#    * get_or_create → defensive: if a matching profile somehow already exists it
#                  is returned instead of raising a duplicate/IntegrityError.
# ============================================================================
@receiver(post_save, sender=USER)
def create_user_profile(sender, instance, created, raw=False, **kwargs):
    if raw:                 # loading fixtures — let them control profile rows
        return
    if created:             # only for newly-inserted users, not updates
        UserProfile.objects.get_or_create(user=instance)
