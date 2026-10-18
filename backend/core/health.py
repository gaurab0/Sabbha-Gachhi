from django.http import JsonResponse


def healthz(_request):
    """Liveness endpoint that does not depend on MongoDB or Redis."""
    return JsonResponse({'status': 'ok'})
