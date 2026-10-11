from contextlib import contextmanager
import mysql.connector
from mysql.connector import pooling
from .config import settings


class Database:
    def __init__(self):
        self.pool = pooling.MySQLConnectionPool(
            pool_name="bank_management_pool",
            pool_size=5,
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            autocommit=False,
        )

    @contextmanager
    def connection(self):
        conn = self.pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        with self.connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def ping(self):
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
