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
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        track = self._should_track(request)
        if track:
            self._read_cookies(request)
        response = self.get_response(request)
        if track:
            self._write_cookies(request, response)
            self._write_db(request)
        return response

    def _should_track(self, request):
        if request.method != 'GET':
            return False
        if request.path.startswith(('/static/', '/media/', '/admin/')):
            return False
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return False
        return True

    def _read_cookies(self, request):
        today = timezone.localdate().isoformat()
        last = request.COOKIES.get(COOKIE_DATE)
        try:
            daily = int(request.COOKIES.get(COOKIE_DAILY, 0))
            total = int(request.COOKIES.get(COOKIE_TOTAL, 0))
        except (TypeError, ValueError):
            daily = total = 0
        daily = daily + 1 if last == today else 1   # reset the counter on a new day
        total += 1
        request.visit_stats = {'date': today, 'daily': daily, 'total': total}

    def _write_cookies(self, request, response):
        stats = getattr(request, 'visit_stats', None)
        if not stats:
            return
        response.set_cookie(COOKIE_DATE, stats['date'], max_age=ONE_YEAR, samesite='Lax')
        response.set_cookie(COOKIE_DAILY, stats['daily'], max_age=ONE_YEAR, samesite='Lax')
        response.set_cookie(COOKIE_TOTAL, stats['total'], max_age=ONE_YEAR, samesite='Lax')

    def _write_db(self, request):
        today = timezone.localdate()
        if request.user.is_authenticated:
            obj, created = DailyVisitLog.objects.get_or_create(
                user=request.user, date=today, defaults={'visit_count': 1})
        else:
            if not request.session.session_key:
                request.session.save()
            obj, created = DailyVisitLog.objects.get_or_create(
                session_key=request.session.session_key, date=today, defaults={'visit_count': 1})
        if not created:
            DailyVisitLog.objects.filter(pk=obj.pk).update(visit_count=F('visit_count') + 1)
