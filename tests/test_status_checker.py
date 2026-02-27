import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from Statuses.services.status_checker import StatusChecker

def test_status_checker_run_success():
    async def _test():
        # Mock DB and repository functions
        db = MagicMock()
        active_postings = [
            {"id": 1, "posting_number": "POST1", "status": "new"},
            {"id": 2, "posting_number": "POST2", "status": "new"}
        ]
        
        # Patching dependencies used in _process_single_posting
        with patch("Statuses.services.status_checker.get_active_postings", return_value=active_postings), \
             patch("Statuses.services.status_checker.update_ozon_info") as mock_update, \
             patch("Statuses.services.status_checker.OzonClient") as mock_client_cls, \
             patch("Statuses.services.status_checker.asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)):
            
            # Setup mock client
            mock_client = mock_client_cls.return_value
            # Note: get_posting_status is now called instead of get_many
            mock_client.get_posting_status = AsyncMock()
            mock_client.get_posting_status.side_effect = [
                {"posting_number": "POST1", "status": "delivering", "cancel_reason": None, "error": None},
                {"posting_number": "POST2", "status": "cancelled", "cancel_reason": "customer_cancelled", "error": None}
            ]
            
            checker = StatusChecker(db, ozon_headers={})
            await checker.run()
            
            # Verify update calls
            assert mock_update.call_count == 2
            mock_update.assert_any_call(
                db, 1, marketplace_status="delivering", marketplace_cancel_reason=None
            )
            mock_update.assert_any_call(
                db, 2, marketplace_status="cancelled", marketplace_cancel_reason="customer_cancelled"
            )
    
    asyncio.run(_test())

def test_status_checker_run_with_api_error():
    async def _test():
        db = MagicMock()
        active_postings = [{"id": 1, "posting_number": "POST_ERR", "status": "new"}]
        
        with patch("Statuses.services.status_checker.get_active_postings", return_value=active_postings), \
             patch("Statuses.services.status_checker.set_check_error") as mock_set_error, \
             patch("Statuses.services.status_checker.OzonClient") as mock_client_cls, \
             patch("Statuses.services.status_checker.asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)):
            
            mock_client = mock_client_cls.return_value
            mock_client.get_posting_status = AsyncMock(return_value={
                "posting_number": "POST_ERR", "error": "API Timeout", "status": None
            })
            
            checker = StatusChecker(db, ozon_headers={})
            await checker.run()
            
            mock_set_error.assert_called_once_with(db, 1, "API Timeout")
            
    asyncio.run(_test())

def test_status_checker_no_postings():
    async def _test():
        db = MagicMock()
        with patch("Statuses.services.status_checker.get_active_postings", return_value=[]), \
             patch("Statuses.services.status_checker.OzonClient") as mock_client_cls:
            
            mock_client = mock_client_cls.return_value
            # If no postings, session is never even opened in run()
            
            checker = StatusChecker(db, ozon_headers={})
            await checker.run()
            
            assert not mock_client.get_posting_status.called
            
    asyncio.run(_test())
