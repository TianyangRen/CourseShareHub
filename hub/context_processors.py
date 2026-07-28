"""
Site-wide template context.  OWNER: Kun (Sessions/Cookies/History — §5.4).

Wired into settings.TEMPLATES so every template can show visit info. The numbers
are computed by VisitCountMiddleware (which stashes them on request.visit_stats);
here we simply expose them to templates.
"""


def visit_counter(request):
    # A context processor runs for every template render and returns a dict that
    # is merged into that template's context. Here we simply forward the
    # visit_stats dict that VisitCountMiddleware attached to the request, so any
    # template (navbar, History page, ...) can show today's/total visits without
    # each view having to pass it in. getattr(..., None) is a safe fallback for
    # requests the middleware skipped (e.g. static/admin), where the attribute
    # is absent.
    return {'visit_stats': getattr(request, 'visit_stats', None)}
