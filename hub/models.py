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
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
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
    tags = models.ManyToManyField(Tag, blank=True, related_name='resources')

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
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='saved_searches')
    keyword = models.CharField(max_length=200, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
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
    """Extra per-user data attached one-to-one to the built-in User."""
    user = models.OneToOneField(USER, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)  # ImageField needs Pillow
    student_id = models.CharField(max_length=20, blank=True)
    program = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


# ============================================================================
#  Kun — UserHistory, DailyVisitLog, ContactMessage  (§5.4 + Contact §5.5)
# ============================================================================
class UserHistory(models.Model):
    """A persistent record of a member's actions (for the History page)."""

    class Action(models.TextChoices):
        VIEW = 'VIEW', 'Viewed'
        DOWNLOAD = 'DOWNLOAD', 'Downloaded'
        SEARCH = 'SEARCH', 'Searched'
        UPLOAD = 'UPLOAD', 'Uploaded'
        FAVOURITE = 'FAVOURITE', 'Favourited'

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=12, choices=Action.choices)
    resource = models.ForeignKey(
        Resource, on_delete=models.SET_NULL, null=True, blank=True, related_name='history_entries',
    )
    keyword = models.CharField(max_length=200, blank=True)  # for SEARCH actions
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'user histories'

    def __str__(self):
        return f"{self.user} {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"


class DailyVisitLog(models.Model):
    """One row per visitor per day, storing that day's visit count (care2-style).

    Either `user` (members) or `session_key` (guests) identifies the visitor;
    the other is left NULL. Because SQL treats NULLs as distinct, the two
    unique_together rules below never collide across the NULL column.
    """
    user = models.ForeignKey(USER, on_delete=models.CASCADE, null=True, blank=True, related_name='visit_logs')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    date = models.DateField()
    visit_count = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-date']
        unique_together = [('user', 'date'), ('session_key', 'date')]

    def __str__(self):
        who = self.user or f"guest:{self.session_key}"
        return f"{who} — {self.date}: {self.visit_count}"


class ContactMessage(models.Model):
    """A message submitted through the Contact Us form.  Owner: Kun."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.email})"


# ============================================================================
#  Zhihan — Comment, Favourite  (§5.5 social features around uploads)
# ============================================================================
class Comment(models.Model):
    """A comment left on a resource by a registered user."""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.resource}"


class Favourite(models.Model):
    """A user 'saving' a resource. unique_together stops duplicate favourites."""
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='favourites')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='favourited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'resource')

    def __str__(self):
        return f"{self.user} ♥ {self.resource}"


# ============================================================================
#  Signal: auto-create a UserProfile whenever a User is created.
#  raw=True happens during `loaddata`; we skip then so fixtures stay in control.
# ============================================================================
@receiver(post_save, sender=USER)
def create_user_profile(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    if created:
        UserProfile.objects.get_or_create(user=instance)
