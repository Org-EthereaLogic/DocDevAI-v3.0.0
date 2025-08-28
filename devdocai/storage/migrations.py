"""
Database migration system for M002 Local Storage.

Provides schema versioning and migration capabilities using Alembic.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages database schema migrations for the storage system.
    
    Provides version control, upgrade/downgrade capabilities,
    and migration history tracking.
    """
    
    def __init__(self, db_path: str, migrations_dir: Optional[str] = None):
        """
        Initialize migration manager.
        
        Args:
            db_path: Path to SQLite database
            migrations_dir: Directory for migration scripts
        """
        self.db_path = db_path
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url)
        
        # Set up migrations directory
        if migrations_dir:
            self.migrations_dir = Path(migrations_dir)
        else:
            self.migrations_dir = Path(__file__).parent / 'alembic'
        
        self._ensure_migrations_dir()
        self._init_alembic()
    
    def _ensure_migrations_dir(self):
        """Ensure migrations directory structure exists."""
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Create versions directory
        versions_dir = self.migrations_dir / 'versions'
        versions_dir.mkdir(exist_ok=True)
        
        # Create alembic.ini if it doesn't exist
        ini_path = self.migrations_dir / 'alembic.ini'
        if not ini_path.exists():
            self._create_alembic_ini()
        
        # Create env.py if it doesn't exist
        env_path = self.migrations_dir / 'env.py'
        if not env_path.exists():
            self._create_env_py()
    
    def _create_alembic_ini(self):
        """Create basic alembic.ini configuration."""
        ini_content = f"""
# Alembic Configuration for DevDocAI Storage

[alembic]
script_location = {self.migrations_dir}
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = {self.db_url}

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
        ini_path = self.migrations_dir / 'alembic.ini'
        ini_path.write_text(ini_content.strip())
    
    def _create_env_py(self):
        """Create env.py for Alembic."""
        env_content = '''
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your models
from devdocai.storage.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        env_path = self.migrations_dir / 'env.py'
        env_path.write_text(env_content.strip())
    
    def _init_alembic(self):
        """Initialize Alembic configuration."""
        self.alembic_cfg = Config(str(self.migrations_dir / 'alembic.ini'))
        self.alembic_cfg.set_main_option('script_location', str(self.migrations_dir))
        self.alembic_cfg.set_main_option('sqlalchemy.url', self.db_url)
    
    def init_db(self):
        """
        Initialize database with migration tracking.
        
        Creates alembic_version table and stamps with initial revision.
        """
        try:
            # Create alembic version table
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                """))
                conn.commit()
            
            # Stamp with initial revision if needed
            current = self.get_current_revision()
            if not current:
                command.stamp(self.alembic_cfg, "head")
                logger.info("Database initialized with migration tracking")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_current_revision(self) -> Optional[str]:
        """
        Get current database revision.
        
        Returns:
            Current revision ID or None
        """
        with self.engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    
    def get_head_revision(self) -> Optional[str]:
        """
        Get latest available revision.
        
        Returns:
            Head revision ID or None
        """
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        head = script_dir.get_current_head()
        return head
    
    def is_up_to_date(self) -> bool:
        """
        Check if database is at latest revision.
        
        Returns:
            True if up to date
        """
        current = self.get_current_revision()
        head = self.get_head_revision()
        return current == head
    
    def create_migration(self, message: str, auto: bool = True) -> str:
        """
        Create a new migration.
        
        Args:
            message: Migration description
            auto: Auto-generate based on model changes
            
        Returns:
            Path to created migration file
        """
        if auto:
            revision = command.revision(
                self.alembic_cfg,
                message=message,
                autogenerate=True
            )
        else:
            revision = command.revision(
                self.alembic_cfg,
                message=message
            )
        
        logger.info(f"Created migration: {revision}")
        return str(revision)
    
    def upgrade(self, revision: str = "head") -> bool:
        """
        Upgrade database to a revision.
        
        Args:
            revision: Target revision (default "head" for latest)
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Upgrading database to {revision}")
            command.upgrade(self.alembic_cfg, revision)
            logger.info("Database upgrade completed")
            return True
        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            return False
    
    def downgrade(self, revision: str = "-1") -> bool:
        """
        Downgrade database to a revision.
        
        Args:
            revision: Target revision (default "-1" for previous)
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Downgrading database to {revision}")
            command.downgrade(self.alembic_cfg, revision)
            logger.info("Database downgrade completed")
            return True
        except Exception as e:
            logger.error(f"Downgrade failed: {e}")
            return False
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get migration history.
        
        Returns:
            List of migration records
        """
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        history = []
        
        for revision in script_dir.walk_revisions():
            history.append({
                'revision': revision.revision,
                'branch_labels': list(revision.branch_labels or []),
                'dependencies': revision.dependencies,
                'down_revision': revision.down_revision,
                'message': revision.doc,
                'is_head': revision.is_head,
                'is_base': revision.is_base
            })
        
        return history
    
    def verify_schema(self) -> Tuple[bool, List[str]]:
        """
        Verify database schema integrity.
        
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        try:
            with self.engine.connect() as conn:
                # Check core tables exist
                required_tables = [
                    'documents', 'document_versions', 'metadata',
                    'search_index', 'audit_logs'
                ]
                
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )).fetchall()
                
                existing_tables = {row[0] for row in result}
                
                for table in required_tables:
                    if table not in existing_tables:
                        issues.append(f"Missing table: {table}")
                
                # Check alembic version table
                if 'alembic_version' not in existing_tables:
                    issues.append("Migration tracking not initialized")
                
                # Check if migrations are up to date
                if not self.is_up_to_date():
                    issues.append("Database schema is not up to date")
                
                # Check indexes
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )).fetchall()
                
                indexes = {row[0] for row in result}
                required_indexes = [
                    'idx_document_type_status',
                    'idx_document_created',
                    'idx_metadata_key_value'
                ]
                
                for index in required_indexes:
                    if index not in indexes:
                        issues.append(f"Missing index: {index}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Schema verification error: {e}")
            return False, issues
    
    def backup_schema(self, backup_path: Optional[str] = None) -> str:
        """
        Backup database schema to SQL file.
        
        Args:
            backup_path: Optional backup file path
            
        Returns:
            Path to backup file
        """
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"schema_backup_{timestamp}.sql"
        
        with self.engine.connect() as conn:
            # Get schema dump
            result = conn.execute(text(
                "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"
            )).fetchall()
            
            schema_sql = '\n'.join([row[0] for row in result])
            
            # Write to file
            Path(backup_path).write_text(schema_sql)
            logger.info(f"Schema backed up to {backup_path}")
            
            return backup_path
    
    def apply_manual_migration(self, sql_file: str) -> bool:
        """
        Apply a manual SQL migration.
        
        Args:
            sql_file: Path to SQL file
            
        Returns:
            Success status
        """
        try:
            sql_content = Path(sql_file).read_text()
            
            with self.engine.begin() as conn:
                # Split by semicolon and execute each statement
                statements = sql_content.split(';')
                for statement in statements:
                    if statement.strip():
                        conn.execute(text(statement))
            
            logger.info(f"Applied manual migration from {sql_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply manual migration: {e}")
            return False


class SchemaMigration:
    """Helper class for common schema migrations."""
    
    @staticmethod
    def add_column(engine: Engine, table: str, column: str, 
                  column_type: str, default: Any = None) -> bool:
        """
        Add a column to a table.
        
        Args:
            engine: SQLAlchemy engine
            table: Table name
            column: Column name
            column_type: SQL column type
            default: Default value
            
        Returns:
            Success status
        """
        try:
            with engine.begin() as conn:
                # Check if column exists
                result = conn.execute(text(
                    f"PRAGMA table_info({table})"
                )).fetchall()
                
                columns = {row[1] for row in result}
                
                if column not in columns:
                    default_clause = f" DEFAULT {default}" if default is not None else ""
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {column_type}{default_clause}"
                    ))
                    logger.info(f"Added column {column} to {table}")
                    return True
                else:
                    logger.info(f"Column {column} already exists in {table}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to add column: {e}")
            return False
    
    @staticmethod
    def create_index(engine: Engine, index_name: str, table: str,
                    columns: List[str]) -> bool:
        """
        Create an index on a table.
        
        Args:
            engine: SQLAlchemy engine
            index_name: Index name
            table: Table name
            columns: List of columns
            
        Returns:
            Success status
        """
        try:
            with engine.begin() as conn:
                # Check if index exists
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=:name"
                ), {'name': index_name}).fetchone()
                
                if not result:
                    columns_str = ', '.join(columns)
                    conn.execute(text(
                        f"CREATE INDEX {index_name} ON {table} ({columns_str})"
                    ))
                    logger.info(f"Created index {index_name}")
                    return True
                else:
                    logger.info(f"Index {index_name} already exists")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False