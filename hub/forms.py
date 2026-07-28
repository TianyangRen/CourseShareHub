"""
CourseShare Hub — forms.

Reference implementation. Each form's clean_*/validation is what powers the
Testing (/2) edge cases (empty title, duplicate email, invalid file). Re-author
in your own words and be ready to explain it. See docs/PROJECT_PLAN.md §4.
"""
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm,
)
from django.contrib.auth.models import User

from .models import UserProfile, ContactMessage, Resource, Comment, Course, Category, SavedSearch


class BootstrapMixin:
    """Adds Bootstrap CSS classes to every widget so templates stay clean.

    Put this FIRST in the inheritance list so its __init__ runs and then calls
    super().__init__ (cooperative multiple inheritance).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


# ---- Honghao — Auth / Profile (§5.1) --------------------------------------
class RegisterForm(BootstrapMixin, UserCreationForm):
    """Extends Django's UserCreationForm with a required, unique email."""
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class UserProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'student_id', 'program', 'bio']
        widgets = {'bio': forms.Textarea(attrs={'rows': 3})}


# ---- Tianyang — Resource + taxonomy (Course/Category) forms (§5.2) ---------
class ResourceForm(BootstrapMixin, forms.ModelForm):
    """Upload / edit a resource. `uploader` and `file_type` are set server-side
    (in the view and the model's save()), so they are NOT in this form."""
    class Meta:
        model = Resource
        fields = ['title', 'description', 'course', 'category', 'tags', 'file', 'is_public']
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}


class CategoryForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class CourseForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Course
        fields = ['code', 'title', 'description', 'term']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


# ---- Zhihan — Comment (§5.5) ----------------------------------------------
class CommentForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {'body': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a comment…'})}


# ---- Lei — Search filters + saved searches (§5.3) --------------------------
class SearchFilterForm(BootstrapMixin, forms.Form):
    """Powers the search bar + the four dropdown filters on the list page.
    All fields are optional so an empty search simply lists everything."""
    # 普通 forms.Form（不是 ModelForm，因为它不保存东西，只是收集查询参数）
    SORT_CHOICES = [
        ('-created_at', 'Newest'),
        ('created_at', 'Oldest'),
        ('-views_count', 'Most viewed'),
        ('-download_count', 'Most downloaded'),
    ]
    # q 关键词、course/category 用 ModelChoiceField（下拉自动填数据库选项，带 empty_label）、file_type/sort 用 ChoiceField。
    q = forms.CharField(
        required=False, label='Keyword',
        widget=forms.TextInput(attrs={'placeholder': 'Search resources…'}),
    )
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=False, empty_label='All courses')
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label='All categories')
    file_type = forms.ChoiceField(required=False, choices=[('', 'All types')] + list(Resource.FileType.choices))
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)


class SavedSearchForm(BootstrapMixin, forms.ModelForm):
    """Persists a search + filter combination for the logged-in user. Populated
    from the current filter values (hidden inputs) when 'Save this search' is used."""
    class Meta:
        model = SavedSearch
        fields = ['keyword', 'course', 'category', 'file_type']


# ---- Kun — Contact (§5.5, moved here to balance the workload) --------------
class ContactForm(BootstrapMixin, forms.ModelForm):
    # A ModelForm built straight from ContactMessage: the fields below map to model
    # fields, so form.save() creates the row for us. is_read/created_at are excluded
    # on purpose — they're set server-side, not by the visitor. BootstrapMixin (first
    # in the MRO) styles every widget. The email field is validated as a real address
    # automatically because the model uses EmailField.
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'body']
        widgets = {'body': forms.Textarea(attrs={'rows': 5})}  # taller multi-line box for the message


# ---- Bootstrap-styled versions of Django's built-in auth forms -------------
# The auth views (login / password reset / set new password) use Django's own
# forms; subclassing with BootstrapMixin makes those pages match our theme.
class BootstrapAuthenticationForm(BootstrapMixin, AuthenticationForm):
    pass


class BootstrapPasswordResetForm(BootstrapMixin, PasswordResetForm):
    pass


class BootstrapSetPasswordForm(BootstrapMixin, SetPasswordForm):
    pass
