import importlib.util
from pathlib import Path

from .manager import SurrealDBManager
from .query import Expression, Transaction


class MigrationOperation:
    def __init__(self, query: Expression, reverse: Expression | None = None):
        self.query = query
        self.is_atomic: bool = False
        self.reverse = reverse


class PerformMigrationCommand:
    def __init__(self, session: SurrealDBManager, base_path: str | Path):
        self.session: SurrealDBManager = session
        self.base_path: Path = base_path if isinstance(base_path, Path) else Path(base_path)

    async def upgrade(self, app: str | None = None, migration_number: str = None):
        if migration_number:
            assert app
        migrations = self.discover_migrations()
        for migration_app, migrations in migrations.items():
            if app and app != migration_app:
                continue
            for migration_name, operations in migrations:
                migration_file_number, migration_description = migration_name.split('_', 1)
                if migration_number and migration_number != migration_file_number:
                    continue
                query = Transaction().perform(*[operation.query for operation in operations])
                await self.session.query(query.sql())

    async def downgrade(self):
        pass

    def discover_migrations(self) -> dict[str, list[tuple[str, list[MigrationOperation]]]]:
        migrations_registry = {}
        for root, folders, files in self.base_path.walk(top_down=True):
            folder_name = root.parts[-1]
            if folder_name == 'migrations':
                migration_app_path = root.parent
                app_name = '.'.join(migration_app_path.relative_to(self.base_path).parts)
                migrations = []
                for file_name in files:
                    if file_name != '__init__.py':
                        file_name_wo_extension = file_name.split('.')[0]
                        module = self._import_module_from_path(root / file_name)
                        operations = getattr(module, 'operations', None)
                        if operations:
                            migrations.append((file_name_wo_extension, operations))
                migrations_registry[app_name] = migrations
        return migrations_registry

    def _import_module_from_path(self, module_path: Path):
        spec = importlib.util.spec_from_file_location('', module_path)
        if spec is None:
            raise ImportError(f"Could not load module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
