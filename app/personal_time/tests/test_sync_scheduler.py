from unittest.mock import patch

from app.personal_time.jobs import sync_scheduler


class TestStartScheduler:
    """La sincronización diaria de Humand solo se programa si la integración está activa."""

    def test_sin_api_key_no_programa_ni_arranca_nada(self):
        with patch.object(sync_scheduler.settings, "HUMAND_API_KEY", ""), patch.object(
            sync_scheduler, "scheduler"
        ) as scheduler:
            sync_scheduler.start_scheduler()

        scheduler.add_job.assert_not_called()
        scheduler.start.assert_not_called()

    def test_con_api_key_programa_el_job_diario(self):
        with patch.object(
            sync_scheduler.settings, "HUMAND_API_KEY", "clave"
        ), patch.object(sync_scheduler, "scheduler") as scheduler:
            sync_scheduler.start_scheduler()

        scheduler.add_job.assert_called_once()
        assert scheduler.add_job.call_args.kwargs["id"] == "timeoff_sync_daily"
        scheduler.start.assert_called_once()
