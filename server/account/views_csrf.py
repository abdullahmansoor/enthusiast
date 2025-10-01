from django.http import HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def csrf_cookie(request):
    # This sets the "csrftoken" cookie; no body needed.
    return HttpResponse(status=204)

