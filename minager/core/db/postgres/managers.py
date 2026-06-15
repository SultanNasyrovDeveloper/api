from itertools import batched

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import (
    ColumnExpressionArgument,
    ScalarResult,
    Select,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from minager import settings as _settings

from .models import Model

type Identifier = int | str


class BaseDatabaseManager[ModelT: Model]:
    id_field_name: str = 'id'
    model_class: type[ModelT]
    _session_factory: async_sessionmaker[AsyncSession]

    def __init__(
        self,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.session = session
        self._session_factory = session_factory

    async def __aenter__(self):
        factory = self._session_factory or _settings.main_db
        self.session = factory()
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.commit()
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
        self.session = None

    async def select(self, stmt: Select, session: AsyncSession = None) -> ScalarResult[ModelT]:
        self._check_active_session(session)
        session = self.get_session(session)
        return await session.scalars(stmt)

    async def select_one(self, stmt: Select, session: AsyncSession = None) -> ModelT:
        self._check_active_session(session)
        session = self.get_session(session)
        return await session.scalar(stmt)

    def _check_active_session(self, session: AsyncSession | None = None):
        assert session or self.session

    def get_session(self, session: AsyncSession | None) -> AsyncSession | None:
        return session or self.session

    def get_query(self) -> Select:
        return select(self.model_class)

    def get_item_id(self, item: ModelT) -> int | str | None:
        return getattr(item, self.id_field_name)


class DatabaseManager[ModelT](BaseDatabaseManager[ModelT]):
    async def count(
        self,
        *positional_query: ColumnExpressionArgument,
        session: AsyncSession | None = None,
        **keyword_query: ColumnExpressionArgument,
    ) -> int:
        return await self.select_one(
            select(func.count(getattr(self.model_class, self.id_field_name))).where(
                *positional_query, **keyword_query
            ),
            session=session,
        )

    async def exists(
        self,
        *positional_query: ColumnExpressionArgument,
        session: AsyncSession | None = None,
        **filters: ColumnExpressionArgument,
    ) -> bool:
        return await self.exists(*positional_query, session=session, **filters) > 0

    async def get(self, id_: Identifier, session: AsyncSession | None = None) -> ModelT:
        id_field = getattr(self.model_class, self.id_field_name)
        return await self.select_one(self.get_query().where(id_field == id_), session)

    async def list_(
        self,
        *positional_query,
        page: int | None = None,
        per_page: int | None = None,
        session: AsyncSession = None,
        **keyword_query,
    ) -> list[ModelT]:
        stmt = self.get_query().where(*positional_query, **keyword_query)
        if page and per_page:
            stmt.limit(per_page).offset(per_page * (page - 1))
        return list(await self.select(stmt, session))

    async def create(self, data: dict | ModelT, session: AsyncSession | None = None) -> ModelT:
        self._check_active_session(session)
        item = data
        if not isinstance(data, self.model_class):
            item = self.model_class(**data)
        session = self.get_session(session)
        try:
            session.add(item)
        except IntegrityError as err:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT) from err
        await session.commit()
        item_id = self.get_item_id(item)
        created = await self.get(item_id, session)
        return created

    async def bulk_create(
        self, items: list[dict | BaseModel | ModelT], session: AsyncSession | None = None, **kwargs
    ) -> list[ModelT]:
        self._check_active_session(session)
        create_data = []
        for item in items:
            create_data.append(item.model_dump(mode='json') if isinstance(item, BaseModel) else item)
        session = self.get_session(session)
        stmt = insert(self.model_class)
        stmt = stmt.returning(self.model_class)
        async with session.begin():
            created_items = await session.scalars(stmt, create_data)
        return list(created_items)

    async def update(self, id_: Identifier, data: dict, session: AsyncSession | None = None) -> ModelT:
        self._check_active_session(session)
        stmt = (
            update(self.model_class)
            .where(self.model_class.id.expression == id_)
            .values(**data)
            .returning(self.model_class)
            .execution_options(populate_existing=True)
        )
        session = self.get_session(session)
        updated = await session.scalar(stmt)
        await session.commit()
        return updated

    async def bulk_update(
        self, items: list[dict | ModelT], batch_size: int = 1000, session: AsyncSession | None = None
    ) -> list[ModelT]:
        if not items:
            return []
        self._check_active_session(session)
        updated: list[ModelT] = []
        for batch in batched(items, batch_size):
            for item in batch:
                if isinstance(item, dict):
                    item = self.model_class.model_validate(item)
                self.session.add(item)
                updated.append(item)
            await self.session.commit()
        return updated

    async def delete(self, id_: Identifier, session: AsyncSession | None = None) -> None:
        self._check_active_session(session)
        # TODO: Raise not found error if there is no item?
        stmt = delete(self.model_class).where(self.model_class.id.expression == id_)
        session = self.get_session(session)
        await session.execute(stmt)
        await session.commit()

    async def delete_many(self, ids: list[int | str], session: AsyncSession | None = None):
        pass


class PostgresDatabaseManager[ModelT](DatabaseManager[ModelT]):
    async def bulk_create(
        self,
        items: list[dict | BaseModel | ModelT],
        session: AsyncSession | None = None,
        fail_silently: bool = False,
    ) -> list[ModelT]:
        self._check_active_session(session)
        create_data = []
        for item in items:
            create_data.append(item.model_dump(mode='json') if isinstance(item, BaseModel) else item)
        session = self.get_session(session)
        stmt = postgres_insert(self.model_class)
        if fail_silently:
            stmt = stmt.on_conflict_do_nothing()
        stmt = stmt.returning(self.model_class)
        async with session:
            result = await session.execute(stmt, create_data)
            created_items = result.scalars().all()
            await session.commit()
        return list(created_items)
