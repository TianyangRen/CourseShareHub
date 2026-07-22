"""
Site-wide template context.  OWNER: Kun (Sessions/Cookies/History — §5.4).

Wired into settings.TEMPLATES so every template can show visit info. The numbers
are computed by VisitCountMiddleware (which stashes them on request.visit_stats);
here we simply expose them to templates.
"""


def visit_counter(request):
    return {'visit_stats': getattr(request, 'visit_stats', None)}
