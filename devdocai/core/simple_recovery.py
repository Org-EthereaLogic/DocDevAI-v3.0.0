"""
Simplified Recovery System for DocDevAI v3.0.0

A more reliable implementation focused on the most critical recovery scenarios:
- Database lock handling with progressive backoff
- Connection recovery after failures  
- Simple retry mechanism with exponential backoff
- Read-only mode fallback

Addresses ISS-015: Recovery scenarios failing (simplified approach)
"""

import time
import logging
import sqlite3
import functools
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0
):
    """
    Simple retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay increase
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (sqlite3.OperationalError, sqlite3.DatabaseError, ConnectionError, IOError) as e:
                    last_exception = e
                    
                    # Don't retry on last attempt
                    if attempt == max_attempts:
                        break
                    
                    # Log retry attempt
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}. Retrying in {delay:.1f}s...")
                    
                    # Wait with exponential backoff
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
                
                except Exception as e:
                    # Don't retry non-recoverable errors
                    logger.error(f"Non-recoverable error: {e}")
                    raise
            
            # All retries exhausted
            logger.error(f"All {max_attempts} attempts failed. Last error: {last_exception}")
            raise last_exception
        
        return wrapper
    return decorator


def handle_database_locks(operation: Callable, max_wait: float = 30.0) -> Any:
    """
    Handle SQLite database locks with progressive backoff.
    
    Args:
        operation: Database operation to execute
        max_wait: Maximum time to wait for lock release
        
    Returns:
        Operation result
        
    Raises:
        TimeoutError: If database remains locked
    """
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < max_wait:
        try:
            return operation()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                attempt += 1
                # Progressive backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s, max 5s
                wait_time = min(0.1 * (2 ** attempt), 5.0)
                logger.debug(f"Database locked, waiting {wait_time:.1f}s (attempt {attempt})")
                time.sleep(wait_time)
            else:
                raise
    
    raise TimeoutError(f"Database remained locked for {max_wait}s")


class SimpleStorage:
    """
    Simplified storage with basic recovery capabilities.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._read_only = False
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists with basic schema."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self._read_only = True
    
    @retry_with_backoff(max_attempts=3)
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with retry."""
        return sqlite3.connect(self.db_path, timeout=30.0)
    
    def create_document(self, title: str, content: str) -> dict:
        """Create document with lock handling."""
        if self._read_only:
            raise Exception("Database is in read-only mode")
        
        def insert_operation():
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "INSERT INTO documents (title, content) VALUES (?, ?)",
                    (title, content)
                )
                doc_id = cursor.lastrowid
                conn.commit()
                return {'id': doc_id, 'title': title}
            finally:
                conn.close()
        
        return handle_database_locks(insert_operation, max_wait=10.0)
    
    def get_document(self, doc_id: int) -> Optional[dict]:
        """Get document with connection recovery."""
        def select_operation():
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "SELECT id, title, content FROM documents WHERE id = ?",
                    (doc_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {'id': row[0], 'title': row[1], 'content': row[2]}
                return None
            finally:
                conn.close()
        
        try:
            return handle_database_locks(select_operation, max_wait=5.0)
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def list_documents(self, limit: int = 10) -> list:
        """List documents with graceful degradation."""
        def select_operation():
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "SELECT id, title FROM documents ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
                return [{'id': row[0], 'title': row[1]} for row in cursor.fetchall()]
            finally:
                conn.close()
        
        try:
            return handle_database_locks(select_operation, max_wait=5.0)
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []  # Graceful degradation
    
    def health_check(self) -> dict:
        """Check storage health."""
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1")
            conn.close()
            return {
                'healthy': not self._read_only,
                'status': 'healthy' if not self._read_only else 'read_only'
            }
        except Exception as e:
            return {
                'healthy': False,
                'status': 'error',
                'error': str(e)
            }