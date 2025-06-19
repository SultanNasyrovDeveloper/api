from itertools import batched
from typing import Type

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import ScalarResult, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from minager.settings import main_db

from .models import Model


class BaseManager[ModelT: Model]:
    id_field_name: str = 'id'
    model_class: Type[ModelT]
    _session_factory: async_sessionmaker[AsyncSession]

    def __init__(
        self,
        session: AsyncSession = None,
        session_factory: async_sessionmaker[AsyncSession] = main_db,
    ):
        self.session = session
        self._session_factory = session_factory

    async def __aenter__(self):
        self.session = self._session_factory()
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
        self.session = None

    async def select_one(self, stmt: select, session: AsyncSession = None) -> ModelT:
        self._check_active_session(session)
        session = self.get_session(session)
        return await session.scalar(stmt)

    async def select(self, stmt: select, session: AsyncSession = None) -> ScalarResult[ModelT]:
        self._check_active_session(session)
        session = self.get_session(session)
        return await session.scalars(stmt)

    def _check_active_session(self, session: AsyncSession | None = None):
        assert session or self.session

    def get_session(self, session: AsyncSession | None) -> AsyncSession:
        return session or self.session

    def get_query(self) -> select:
        return select(self.model_class)


class DatabaseManager[ModelT](BaseManager[ModelT]):
    async def count(self, *positional_query, session: AsyncSession = None, **keyword_query) -> int:
        stmt = select(func.count(getattr(self.model_class, self.id_field_name))).where(
            *positional_query, **keyword_query
        )
        return await self.select_one(stmt, session)

    async def get(self, id_: int | str, session: AsyncSession = None) -> ModelT:
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

    async def create(self, data: dict, session: AsyncSession = None) -> ModelT:
        self._check_active_session(session)
        item = self.model_class(**data)
        session = self.get_session(session)
        try:
            session.add(item)
            await session.commit()
        except IntegrityError as error:
            print(error)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT)
        item_id = getattr(item, self.id_field_name)
        created = await self.get(item_id, session)
        return created

    async def bulk_create(
        self, items: list[dict | BaseModel | ModelT], session: AsyncSession = None, **kwargs
    ) -> list[ModelT]:
        self._check_active_session(session)
        create_data = []
        for item in items:
            create_data.append(
                item.model_dump(mode='json') if isinstance(item, BaseModel) else item
            )
        session = self.get_session(session)
        stmt = insert(self.model_class)
        stmt = stmt.returning(self.model_class)
        async with session.begin():
            created_items = await session.scalars(stmt, create_data)
        return list(created_items)

    async def update(self, id_: int, data: dict, session: AsyncSession = None) -> ModelT:
        self._check_active_session(session)
        stmt = (
            update(self.model_class)
            .where(self.model_class.id.expression == id_)
            .values(**data)
            .returning(self.model_class)
        )
        session = self.get_session(session)
        updated = await session.scalar(stmt)
        await session.commit()
        return updated

    async def bulk_update(
        self, items: list[dict | ModelT], batch_size: int = 1000, session: AsyncSession = None
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

    async def delete(self, id_: int, session: AsyncSession = None) -> None:
        self._check_active_session(session)
        # TODO: Raise not found error if there is no item?
        stmt = delete(self.model_class).where(self.model_class.id.expression == id_)
        session = self.get_session(session)
        await session.execute(stmt)
        await session.commit()

    async def delete_many(self, ids: list[int | str], session: AsyncSession = None):
        pass


class PostgresDatabaseManager[ModelT](DatabaseManager[ModelT]):
    async def bulk_create(
        self,
        items: list[dict | BaseModel | ModelT],
        session: AsyncSession = None,
        fail_silently: bool = False,
    ) -> list[ModelT]:
        self._check_active_session(session)
        create_data = []
        for item in items:
            create_data.append(
                item.model_dump(mode='json') if isinstance(item, BaseModel) else item
            )
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
