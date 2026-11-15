import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def auto_migrate(sumber):
    from django.conf import settings
    if not getattr(settings, 'DINEZY_AUTO_MIGRATE', False):
        return
    try:
        from django.core.management import call_command
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        rencana = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if not rencana:
            return
        nama = ', '.join(f"{m.app_label}.{m.name}" for m, _ in rencana)
        logger.warning("[auto-migrate] (%s) menerapkan migrasi: %s", sumber, nama)
        call_command('migrate', interactive=False, verbosity=0)
        logger.warning("[auto-migrate] selesai.")
    except Exception as exc:
        logger.error("[auto-migrate] gagal (%s): %s. Jalankan 'python manage.py cek_database'.", sumber, exc)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        if len(sys.argv) > 1 and sys.argv[1] == 'runserver' and os.environ.get('RUN_MAIN') == 'true':
            auto_migrate('runserver')
