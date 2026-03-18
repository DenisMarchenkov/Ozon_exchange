import pytest
import sqlite3
from pathlib import Path
from Common.db.database import Database
from Common.db.init_db import init_confirmations_schema, init_dispatch_schema
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.db_confirmations.dispatch_repository import DispatchRepository
from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService

class MockFilesService:
    def generate_missing_files(self, dispatch_id):
        return set()

@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(str(db_file))
    init_confirmations_schema(db)
    init_dispatch_schema(db)
    return db

def test_retry_failed_marks_empty_dispatch_as_cancelled(db):
    dispatch_repo = DispatchRepository(db)
    confirmations_repo = ConfirmationsRepository(db)
    files_service = MockFilesService()
    
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service
    )

    # 1. Создаем пустую отгрузку в статусе ERROR
    dispatch_id = "test_empty_dispatch"
    dispatch_repo.create_dispatch(dispatch_id, status="ERROR")
    
    # Убеждаемся, что заказов нет
    assert len(confirmations_repo.get_postings_by_dispatch(dispatch_id)) == 0
    assert dispatch_repo.get_status(dispatch_id) == "ERROR"

    # 2. Запускаем retry
    retry_service.retry_failed()

    # 3. Проверяем, что статус стал CANCELLED
    assert dispatch_repo.get_status(dispatch_id) == "CANCELLED"

def test_retry_failed_does_not_cancel_non_empty_dispatch(db):
    dispatch_repo = DispatchRepository(db)
    confirmations_repo = ConfirmationsRepository(db)
    files_service = MockFilesService()
    
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service
    )

    # 1. Создаем отгрузку и привязываем к ней заказ
    dispatch_id = "test_non_empty_dispatch"
    dispatch_repo.create_dispatch(dispatch_id, status="ERROR")
    
    # Добавляем фейковый заказ
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO confirmations (posting_number, division_id, status, dispatch_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("TEST_POSTING_123", 1, "awaiting_delivery", dispatch_id, "now", "now"))
        conn.commit()

    assert len(confirmations_repo.get_postings_by_dispatch(dispatch_id)) == 1
    assert dispatch_repo.get_status(dispatch_id) == "ERROR"

    # 2. Запускаем retry
    retry_service.retry_failed()

    # 3. Проверяем, что статус стал PREPARED (так как MockFilesService вернул пустые missing_files)
    assert dispatch_repo.get_status(dispatch_id) == "PREPARED"
