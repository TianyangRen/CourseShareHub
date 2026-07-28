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
    """Extends Django's UserCreationForm with a required, unique email.

    UserCreationForm already gives us username + the two password fields with
    Django's password-strength validation and the "passwords must match" check,
    so we only add `email`. Django's User.email is NOT unique by default, hence
    the clean_email() check below enforces uniqueness ourselves.
    """
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        # Inherit the parent Meta but pin the field order shown on the form.
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        # Field-level validation: Django calls clean_<fieldname> automatically.
        # __iexact makes the duplicate check case-insensitive (A@x.com == a@x.com).
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class UserProfileForm(BootstrapMixin, forms.ModelForm):
    # ModelForm built straight from UserProfile: the four editable fields the user
    # controls. `user` and `created_at` are deliberately excluded — they are set
    # server-side (by the signal / the view), never chosen on the form.
    class Meta:
        model = UserProfile
        fields = ['avatar', 'student_id', 'program', 'bio']
        widgets = {'bio': forms.Textarea(attrs={'rows': 3})}  # multi-line box for the bio


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
# We keep the parent's logic entirely — the mixin only injects CSS classes —
# and wire each one into the matching auth view in coursesharehub/urls.py.
class BootstrapAuthenticationForm(BootstrapMixin, AuthenticationForm):
    pass  # login page — username + password


class BootstrapPasswordResetForm(BootstrapMixin, PasswordResetForm):
    pass  # "forgot password" page — enter email to receive a reset link


class BootstrapSetPasswordForm(BootstrapMixin, SetPasswordForm):
    pass  # "choose a new password" page reached from the emailed link
