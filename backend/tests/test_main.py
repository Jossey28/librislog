"""Tests for app.main module-level code and lifespan helpers."""

import asyncio
import importlib
from unittest.mock import MagicMock, patch


def test_periodic_temp_cleanup_logs_success() -> None:
    """Successful cleanup should log info and reset failures."""
    from app.main import _periodic_temp_cleanup

    async def _run() -> MagicMock:
        with patch("app.main.cleanup_temp_files"):
            with patch("app.main.asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
                with patch("app.main.logger") as mock_logger:
                    try:
                        await _periodic_temp_cleanup()
                    except asyncio.CancelledError:
                        pass
        return mock_logger

    mock_logger = asyncio.run(_run())
    assert mock_logger.info.call_count == 1
    assert "cleanup completed" in str(mock_logger.info.call_args_list[0])


def test_periodic_temp_cleanup_logs_warning_on_first_failure() -> None:
    """First failure should log a warning."""
    from app.main import _periodic_temp_cleanup

    async def _run() -> MagicMock:
        with patch("app.main.cleanup_temp_files", side_effect=RuntimeError("boom")):
            with patch("app.main.asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
                with patch("app.main.logger") as mock_logger:
                    try:
                        await _periodic_temp_cleanup()
                    except asyncio.CancelledError:
                        pass
        return mock_logger

    mock_logger = asyncio.run(_run())
    assert mock_logger.warning.call_count == 1
    assert "cleanup failed" in str(mock_logger.warning.call_args_list[0]).lower()


def test_periodic_temp_cleanup_logs_error_after_three_failures() -> None:
    """Three consecutive failures should log an error."""
    from app.main import _periodic_temp_cleanup

    async def _run() -> MagicMock:
        with patch("app.main.cleanup_temp_files", side_effect=RuntimeError("boom")):
            with patch("app.main.asyncio.sleep", side_effect=[None, None, None, asyncio.CancelledError()]):
                with patch("app.main.logger") as mock_logger:
                    try:
                        await _periodic_temp_cleanup()
                    except asyncio.CancelledError:
                        pass
        return mock_logger

    mock_logger = asyncio.run(_run())
    assert mock_logger.error.call_count == 1
    assert "consecutively" in str(mock_logger.error.call_args_list[0]).lower()


def test_cookie_samesite_invalid_value_falls_back_to_lax() -> None:
    """An invalid auth_cookie_samesite value should fall back to 'lax'."""
    from app.config import settings
    import app.main as main_module

    original_value = settings.auth_cookie_samesite
    try:
        settings.auth_cookie_samesite = "INVALID"
        importlib.reload(main_module)
        assert main_module.cookie_samesite == "lax"
    finally:
        settings.auth_cookie_samesite = original_value
        importlib.reload(main_module)
