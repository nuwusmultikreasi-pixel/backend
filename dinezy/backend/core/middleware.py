import logging

from django.conf import settings
from django.db import OperationalError, ProgrammingError, InterfaceError
from django.shortcuts import render

logger = logging.getLogger(__name__)


class DatabaseErrorMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, (OperationalError, ProgrammingError, InterfaceError)):
            return None
        pesan = str(exception)
        logger.error("Database error pada %s: %s", request.path, pesan)
        lower = pesan.lower()
        if any(k in lower for k in ("can't connect", 'connection refused', '2003', 'gone away', 'lost connection', '10061')):
            jenis = 'koneksi'
        elif any(k in lower for k in ('unknown database', '1049')):
            jenis = 'database'
        elif any(k in lower for k in ('access denied', '1045')):
            jenis = 'akses'
        elif any(k in lower for k in ("doesn't exist", 'no such table', 'unknown column', 'no such column', '1146', '1054')):
            jenis = 'migrasi'
        else:
            jenis = 'lain'
        db = settings.DATABASES['default']
        context = {
            'jenis': jenis,
            'detail': pesan if settings.DEBUG else '',
            'db_name': db.get('NAME'), 'db_host': db.get('HOST', ''), 'db_port': db.get('PORT', ''),
            'db_user': db.get('USER', ''), 'engine': db.get('ENGINE', '').rsplit('.', 1)[-1],
        }
        if request.path.startswith('/api/'):
            from django.http import JsonResponse
            return JsonResponse({'error': 'Database tidak dapat diakses.', 'jenis': jenis,
                                 'detail': context['detail']}, status=503)
        return render(request, 'database_error.html', context, status=503)
