import importlib.util
from pathlib import Path

from ..orm.manager import Manager
from ..statements.create import Create
from ..statements.define import DefineField, DefineTable
from ..statements.delete import Delete
from ..statements.select import Select
from ..statements.transaction import Transaction
from .models import Migration
from .operations import MigrationOperation


class PerformMigrationCommand:
    def __init__(self, session: Manager, base_path: str | Path):
        self.session: Manager = session
        self.base_path: Path = base_path if isinstance(base_path, Path) else Path(base_path)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def upgrade(self, app: str | None = None, migration_number: str = None):
        if migration_number:
            assert app
        await self._ensure_history_table()
        migrations = self.discover_migrations()
        for migration_app, app_migrations in migrations.items():
            if app and app != migration_app:
                continue
            for migration_name, operations in app_migrations:
                migration_file_number, _ = migration_name.split('_', 1)
                if migration_number and migration_number != migration_file_number:
                    continue
                if await self._is_migration_applied(migration_app, migration_name):
                    continue
                query = Transaction().perform(*[operation.query for operation in operations])
                await self.session.query(query.sql())
                await self._record_migration(migration_app, migration_name)

    async def downgrade(self, app: str | None = None, migration_number: str = None):
        if migration_number:
            assert app
        await self._ensure_history_table()
        migrations = self.discover_migrations()
        for migration_app, app_migrations in migrations.items():
            if app and app != migration_app:
                continue
            # Apply downgrades in reverse migration order
            for migration_name, operations in reversed(app_migrations):
                migration_file_number, _ = migration_name.split('_', 1)
                if migration_number and migration_number != migration_file_number:
                    continue
                if not await self._is_migration_applied(migration_app, migration_name):
                    continue
                reverse_ops = [op.reverse for op in operations if op.reverse is not None]
                if reverse_ops:
                    query = Transaction().perform(*reverse_ops)
                    await self.session.query(query.sql())
                await self._remove_migration_record(migration_app, migration_name)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_migrations(self) -> dict[str, list[tuple[str, list[MigrationOperation]]]]:
        migrations_registry = {}
        for root, folders, files in self.base_path.walk(top_down=True):
            folder_name = root.parts[-1]
            if folder_name == 'migrations':
                migration_app_path = root.parent
                relative = migration_app_path.relative_to(self.base_path)
                if len(relative.parts) != 1:
                    continue
                app_name = '.'.join(relative.parts)
                migrations = []
                for file_name in sorted(files):
                    if file_name == '__init__.py':
                        continue
                    file_name_wo_extension = file_name.split('.')[0]
                    module = self._import_module_from_path(root / file_name)
                    operations = getattr(module, 'operations', None)
                    if operations:
                        migrations.append((file_name_wo_extension, operations))
                migrations_registry[app_name] = migrations
        return migrations_registry

    @staticmethod
    def _import_module_from_path(module_path: Path):
        spec = importlib.util.spec_from_file_location('', module_path)
        if spec is None:
            raise ImportError(f'Could not load module from {module_path}')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # ------------------------------------------------------------------
    # Migration history helpers
    # ------------------------------------------------------------------

    async def _ensure_history_table(self):
        """Create migration_history table and fields if they do not exist."""
        query = Transaction().perform(
            DefineTable(Migration).schemafull(True).if_not_exists(True),
            DefineField('app', 'string').on(Migration).if_not_exists(True),
            DefineField('migration', 'string').on(Migration).if_not_exists(True),
            (
                DefineField('applied_at', 'datetime')
                .on(Migration)
                .if_not_exists(True)
                .default('time::now()')
            ),
        )
        await self.session.query(query.sql())

    async def _is_migration_applied(self, app: str, migration_name: str) -> bool:
        """Return True if the given migration is recorded in migration_history."""
        result = await self.session.query(
            Select('id').from_(Migration).where('app = $app AND migration = $migration').limit(1),
            {'app': app, 'migration': migration_name},
        )
        if result is None:
            return False
        if isinstance(result, list):
            return len(result) > 0
        return bool(result)

    async def _record_migration(self, app: str, migration_name: str):
        """Insert a record into migration_history after a successful upgrade."""
        await self.session.query(Create(Migration).set(app=app, migration=migration_name))

    async def _remove_migration_record(self, app: str, migration_name: str):
        """Delete the history record for a migration after a successful downgrade."""
        await self.session.query(
            Delete(Migration).where('app = $app AND migration = $migration'),
            {'app': app, 'migration': migration_name},
        )
