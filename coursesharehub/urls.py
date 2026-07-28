"""
Project URL configuration for CourseShare Hub.

We override three of Django's built-in auth views so they use our Bootstrap-
styled forms, THEN include the rest of django.contrib.auth.urls. URL resolution
takes the first match, so these overrides win while keeping the standard names
(login, password_reset, password_reset_confirm). See docs/PROJECT_PLAN.md §5.1.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from hub.forms import (
    BootstrapAuthenticationForm, BootstrapPasswordResetForm, BootstrapSetPasswordForm,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Auth view overrides (Bootstrap-styled forms) ---
    # We reuse Django's ready-made auth views but swap in our Bootstrap form
    # classes so the pages match the site theme. Keeping the SAME url names
    # (login / password_reset / password_reset_confirm) means {% url %} tags and
    # Django's own redirects keep working. Django resolves top-to-bottom, so
    # these three lines must sit ABOVE the include() below to win the match;
    # the reset-confirm route needs the <uidb64>/<token> captured from the email link.
    path('accounts/login/',
         auth_views.LoginView.as_view(authentication_form=BootstrapAuthenticationForm),
         name='login'),
    path('accounts/password_reset/',
         auth_views.PasswordResetView.as_view(form_class=BootstrapPasswordResetForm),
         name='password_reset'),
    path('accounts/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(form_class=BootstrapSetPasswordForm),
         name='password_reset_confirm'),
    # The rest (logout, password_reset_done, password_reset_complete) keep
    # Django's defaults, pulled in by including the standard auth URLconf:
    path('accounts/', include('django.contrib.auth.urls')),

    # Main app.
    path('', include('hub.urls')),
]

# Serve user-uploaded media during development only (never in production).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
