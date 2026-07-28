"""
CourseShare Hub — automated tests.

Run with:  python manage.py test
Uploads are redirected to a temp MEDIA_ROOT so tests never touch real media/.
These cover the graded edge cases (validation, wrong logins, empty search,
access control) that the Testing (/2) rubric rewards. Re-author / extend these
with your own cases and understand each assertion for the viva.
"""
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import RegisterForm, ResourceForm
from .models import Category, Resource, Favourite, UserProfile, SavedSearch

MEDIA = tempfile.mkdtemp()


def a_pdf(name='f.pdf', size=32):
    # Shared helper so every test that needs "some valid uploaded file" doesn't
    # repeat the SimpleUploadedFile boilerplate — a minimal but real PDF header
    # is enough for validate_file_extension/size to treat it as legitimate.
    return SimpleUploadedFile(name, b'%PDF-1.4' + b'x' * size, content_type='application/pdf')


def tearDownModule():
    shutil.rmtree(MEDIA, ignore_errors=True)


@override_settings(MEDIA_ROOT=MEDIA)
class ModelTests(TestCase):
    """Model-level behaviour: save() overrides, signals, and DB constraints —
    the things that would silently break without a test if a migration or
    model edit changed them."""
    def test_category_slug_autofill(self):
        self.assertEqual(Category.objects.create(name='Lecture Notes').slug, 'lecture-notes')

    def test_profile_created_by_signal(self):
        u = User.objects.create_user('a', password='x')
        self.assertTrue(UserProfile.objects.filter(user=u).exists())

    def test_resource_filetype_autodetect(self):
        u = User.objects.create_user('b', password='x')
        cat = Category.objects.create(name='N')
        r = Resource.objects.create(title='t', uploader=u, category=cat, file=a_pdf())
        self.assertEqual(r.file_type, Resource.FileType.PDF)

    def test_favourite_is_unique_per_user_resource(self):
        # Proves the unique_together=('user', 'resource') constraint on
        # Favourite is actually enforced at the DB level, not just assumed —
        # the second create() for the same pair must raise IntegrityError.
        # The nested transaction.atomic() is required here: once a query
        # inside a Django test fails, the outer test transaction is left
        # unusable unless the failing part is wrapped in its own atomic block
        # that can be rolled back on its own.
        u = User.objects.create_user('c', password='x')
        cat = Category.objects.create(name='N')
        r = Resource.objects.create(title='t', uploader=u, category=cat, file=a_pdf())
        Favourite.objects.create(user=u, resource=r)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favourite.objects.create(user=u, resource=r)


@override_settings(MEDIA_ROOT=MEDIA)
class FormTests(TestCase):
    """Form-level validation edge cases — these back the graded 'reject bad
    input with a clear error' rubric item, so each test checks the form is
    invalid AND that the error lands on the expected field."""
    def test_register_rejects_duplicate_email(self):
        User.objects.create_user('x', email='e@e.com', password='x')
        f = RegisterForm(data={'username': 'y', 'email': 'e@e.com',
                               'password1': 'Str0ng!pass9', 'password2': 'Str0ng!pass9'})
        self.assertFalse(f.is_valid())
        self.assertIn('email', f.errors)

    def test_resourceform_rejects_bad_extension(self):
        cat = Category.objects.create(name='N')
        bad = SimpleUploadedFile('m.exe', b'MZ', content_type='application/octet-stream')
        f = ResourceForm(data={'title': 't', 'category': cat.pk}, files={'file': bad})
        self.assertFalse(f.is_valid())
        self.assertIn('file', f.errors)

    def test_resourceform_rejects_oversized(self):
        cat = Category.objects.create(name='N')
        big = SimpleUploadedFile('b.pdf', b'x' * (11 * 1024 * 1024), content_type='application/pdf')
        f = ResourceForm(data={'title': 't', 'category': cat.pk}, files={'file': big})
        self.assertFalse(f.is_valid())


@override_settings(MEDIA_ROOT=MEDIA)
class ViewAccessTests(TestCase):
    """Who can see/do what: guest vs member visibility (§5.6) and the
    owner-only edit/delete rule, plus one smoke test per other member's
    feature (search, saved searches, taxonomy pages) so a regression there
    fails a test instead of only showing up in the demo."""
    @classmethod
    def setUpTestData(cls):
        # setUpTestData (not setUp) creates these once per class, wrapped in a
        # transaction that every test method rolls back from — much faster
        # than re-creating owner/other/cat before each individual test.
        cls.owner = User.objects.create_user('owner', password='pw')
        cls.other = User.objects.create_user('other', password='pw')
        cls.cat = Category.objects.create(name='Notes')

    def _mkres(self, pub=True, owner=None):
        # Leading underscore marks this as a private test helper, not a test
        # itself — Django's test runner only collects methods named test_*.
        return Resource.objects.create(title='R', uploader=owner or self.owner,
                                       category=self.cat, is_public=pub, file=a_pdf())

    def test_home_and_list_ok(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('resource_list')).status_code, 200)

    def test_guest_cannot_see_private(self):
        r = self._mkres(pub=False)
        names = [x.title for x in self.client.get(reverse('resource_list')).context['resources']]
        self.assertNotIn('R', names)
        self.assertEqual(self.client.get(reverse('resource_detail', args=[r.pk])).status_code, 404)

    def test_detail_increments_view_count(self):
        r = self._mkres()
        self.client.get(reverse('resource_detail', args=[r.pk]))
        r.refresh_from_db()
        self.assertEqual(r.views_count, 1)

    def test_upload_requires_login(self):
        self.assertEqual(self.client.get(reverse('resource_create')).status_code, 302)

    def test_only_owner_can_edit(self):
        r = self._mkres()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('resource_update', args=[r.pk])).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('resource_update', args=[r.pk])).status_code, 200)

    def test_empty_search_shows_message(self):
        self.assertContains(self.client.get(reverse('resource_list'), {'q': 'zzzznope'}),
                            'No resources match')

    def test_history_requires_login(self):
        self.assertEqual(self.client.get(reverse('history')).status_code, 302)

    def test_favourite_toggle(self):
        # Two POSTs to the same URL must round-trip: first adds the Favourite
        # row, second removes it — this is what proves toggle_favourite's
        # get_or_create/delete branching (views.py) actually toggles instead
        # of only ever adding.
        r = self._mkres()
        self.client.force_login(self.other)
        self.client.post(reverse('toggle_favourite', args=[r.pk]))
        self.assertTrue(Favourite.objects.filter(user=self.other, resource=r).exists())
        self.client.post(reverse('toggle_favourite', args=[r.pk]))
        self.assertFalse(Favourite.objects.filter(user=self.other, resource=r).exists())

    def test_category_and_course_directories_ok(self):   # Tianyang's taxonomy pages
        self.assertEqual(self.client.get(reverse('category_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('course_list')).status_code, 200)

    def test_save_search_creates_record(self):           # Lei's SavedSearch feature
        self.client.force_login(self.other)
        self.client.post(reverse('save_search'), {'keyword': 'django'})
        self.assertTrue(SavedSearch.objects.filter(user=self.other, keyword='django').exists())


@override_settings(MEDIA_ROOT=MEDIA)
class AuthFlowTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(reverse('register'),
                                {'username': 'newbie', 'email': 'n@e.com',
                                 'password1': 'Str0ng!pass9', 'password2': 'Str0ng!pass9'})
        self.assertRedirects(resp, reverse('home'))
        self.assertTrue(User.objects.filter(username='newbie').exists())
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)  # already logged in

    def test_wrong_password_rejected(self):
        User.objects.create_user('joe', password='rightpass123')
        resp = self.client.post(reverse('login'), {'username': 'joe', 'password': 'WRONG'})
        self.assertEqual(resp.status_code, 200)          # re-renders the login form
        self.assertFalse(resp.context['user'].is_authenticated)
