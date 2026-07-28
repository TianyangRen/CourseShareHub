"""
Visit-tracking middleware.  OWNER: Kun (Sessions/Cookies/History — §5.4).

For every normal page GET this:
  * reads a per-day visit COOKIE, increments today's count (resets on a new day),
    and writes it back on the response — this is the care2-style "visits today";
  * stashes the numbers on request.visit_stats so the context processor and the
    History page can show them;
  * increments a DailyVisitLog row in the DB (per user, or per session for guests).

A context processor cannot set cookies (it has no response), which is exactly why
this lives in middleware.
"""
from django.db.models import F
from django.utils import timezone

from .models import DailyVisitLog

COOKIE_DATE = 'cs_last_visit'
COOKIE_DAILY = 'cs_daily_visits'
COOKIE_TOTAL = 'cs_total_visits'
ONE_YEAR = 60 * 60 * 24 * 365


class VisitCountMiddleware:
    # Standard Django middleware shape: __init__ runs once at server startup and
    # receives get_response (the "next layer"); __call__ runs once per request.
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Full per-request flow: decide whether to track -> read cookies and
        # compute numbers before the view -> let the view run -> after the view,
        # write the numbers back to cookies and update the database.
        track = self._should_track(request)
        if track:
            self._read_cookies(request)          # compute the numbers before we have a response
        response = self.get_response(request)     # hand off to the next middleware/view
        if track:
            self._write_cookies(request, response)  # set_cookie must act on the response
            self._write_db(request)
        return response

    def _should_track(self, request):
        """Filter out requests that shouldn't count, so we don't inflate visits."""
        if request.method != 'GET':
            return False  # only count page views (GET), not POST form submissions etc.
        if request.path.startswith(('/static/', '/media/', '/admin/')):
            return False  # static assets, uploads and the admin don't count as a "visit"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return False  # ignore AJAX requests
        return True

    def _read_cookies(self, request):
        """Read the old counts from cookies and compute today's/total visits (this is the cookie usage)."""
        today = timezone.localdate().isoformat()   # today's date string, used to detect a new day
        last = request.COOKIES.get(COOKIE_DATE)     # the date of the previous visit
        try:
            daily = int(request.COOKIES.get(COOKIE_DAILY, 0))
            total = int(request.COOKIES.get(COOKIE_TOTAL, 0))
        except (TypeError, ValueError):
            daily = total = 0   # fallback if a cookie was tampered into a non-number, so we don't crash
        # Key logic: same day -> +1; a new day -> reset today's count to 1.
        daily = daily + 1 if last == today else 1
        total += 1              # the running total only ever grows
        # Stash on request so _write_cookies, the context processor and the History page can share it.
        request.visit_stats = {'date': today, 'daily': daily, 'total': total}

    def _write_cookies(self, request, response):
        """Write the freshly computed numbers back to the browser's cookies, so the next request can keep accumulating."""
        stats = getattr(request, 'visit_stats', None)
        if not stats:
            return
        # max_age=one year keeps the cookies around; samesite='Lax' blocks cross-site sending, which is safer.
        response.set_cookie(COOKIE_DATE, stats['date'], max_age=ONE_YEAR, samesite='Lax')
        response.set_cookie(COOKIE_DAILY, stats['daily'], max_age=ONE_YEAR, samesite='Lax')
        response.set_cookie(COOKIE_TOTAL, stats['total'], max_age=ONE_YEAR, samesite='Lax')

    def _write_db(self, request):
        """Record a row in DailyVisitLog: members keyed by user, guests by session_key."""
        today = timezone.localdate()
        if request.user.is_authenticated:
            # First visit of the day creates the row (visit_count=1), otherwise fetch the existing one.
            obj, created = DailyVisitLog.objects.get_or_create(
                user=request.user, date=today, defaults={'visit_count': 1})
        else:
            # Guests have no user, so identify by session; if there's no session_key yet, save to create one.
            if not request.session.session_key:
                request.session.save()
            obj, created = DailyVisitLog.objects.get_or_create(
                session_key=request.session.session_key, date=today, defaults={'visit_count': 1})
        if not created:
            # Already exists -> increment. Using an F() expression does the +1 at the
            # database level as an atomic operation, avoiding lost updates under
            # concurrency (the classic read-modify-write race).
            DailyVisitLog.objects.filter(pk=obj.pk).update(visit_count=F('visit_count') + 1)
