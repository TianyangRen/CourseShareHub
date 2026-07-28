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

    Why subclass UserCreationForm instead of building a form from scratch: it
    already ships the username field, the two password fields (password1 +
    password2), the "the two passwords must match" check, and runs the passwords
    through AUTH_PASSWORD_VALIDATORS (length / not-too-common / not-all-numeric /
    not-similar-to-username). Reusing it means we inherit all of that for free and
    only add what's missing — a mandatory, unique email.

    Inheritance order matters: BootstrapMixin is listed FIRST so its __init__ runs
    and adds the `form-control` CSS classes, then cooperatively calls up to
    UserCreationForm via super() (see the mixin at the top of this file).
    """
    # required=True → the field cannot be left blank (User.email is optional by
    # default, so we tighten it here for our sign-up flow).
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        # Subclass the parent Meta so we keep its settings, but override two things:
        #   model  → the User model these fields map onto.
        #   fields → also fixes the ORDER the fields render on the page.
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        # Per-field validation hook: Django automatically calls clean_<fieldname>
        # during is_valid(). We enforce email uniqueness ourselves because Django's
        # default User model does NOT make email unique at the database level.
        email = self.cleaned_data['email']
        # __iexact = case-insensitive exact match, so Bob@x.com and bob@x.com are
        # treated as the same address and the second sign-up is rejected.
        if User.objects.filter(email__iexact=email).exists():
            # Raising ValidationError here attaches the message to the email field
            # and stops the form validating — the user sees it inline on the page.
            raise forms.ValidationError('An account with this email already exists.')
        # Whatever clean_email returns becomes the field's final cleaned value.
        return email


class UserProfileForm(BootstrapMixin, forms.ModelForm):
    """Edit form for the extra profile fields (used by ProfileUpdateView).

    A ModelForm derives its fields straight from the model, so form.save() writes
    the changes back to the UserProfile row for us. We expose only the four fields
    the user should control; `user` and `created_at` are intentionally left out
    because they are set server-side (the signal links the user, auto_now_add sets
    the timestamp) and must not be user-editable.
    """
    class Meta:
        model = UserProfile
        fields = ['avatar', 'student_id', 'program', 'bio']
        # Swap the default single-line input for a 3-row textarea on the bio so
        # there's room to type a short paragraph.
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
    """The only field a commenter fills in is the body text. `resource` and
    `author` are deliberately left out: they must come from the URL/session
    (the resource being viewed, the logged-in user), never from client input,
    or a user could forge a comment as someone else on a resource they never
    opened. The view sets both after form.save(commit=False) — see
    add_comment() in views.py."""
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
# Django ships fully-working forms for login, password-reset and set-new-password,
# but they render as plain, unstyled inputs. Rather than reimplement any of their
# logic, we subclass each one together with BootstrapMixin: the `pass` body means
# "behave exactly like the parent", while the mixin's __init__ adds our
# `form-control` CSS classes so the pages match the rest of the site. Each class
# is then plugged into the matching built-in auth view (via authentication_form=
# / form_class=) in coursesharehub/urls.py — that wiring is the only reason these
# subclasses need to exist.
class BootstrapAuthenticationForm(BootstrapMixin, AuthenticationForm):
    pass  # login page — validates username + password against the auth backend


class BootstrapPasswordResetForm(BootstrapMixin, PasswordResetForm):
    pass  # "forgot password" — takes an email and sends the reset link (step 1)


class BootstrapSetPasswordForm(BootstrapMixin, SetPasswordForm):
    pass  # "choose a new password" reached from the emailed link (step 3),
          # incl. the two-passwords-must-match + strength checks from the parent
