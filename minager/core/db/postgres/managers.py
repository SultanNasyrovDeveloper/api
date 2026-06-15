from typing import Any

from pydantic import BaseModel
from sqlalchemy import (
    ColumnExpressionArgument,
    ScalarResult,
    Select,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Model

type Identifier = int | str


class BaseDatabaseManager[ModelT: Model]:
    id_field_name: str = 'id'
    model_class: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def select(self, stmt: Select) -> ScalarResult[ModelT]:
        return await self.session.scalars(stmt)

    async def select_one(self, stmt: Select) -> ModelT | None:
        return await self.session.scalar(stmt)

    def get_query(self) -> Select:
        return select(self.model_class)

    def get_item_id(self, item: ModelT) -> int | str:
        return getattr(item, self.id_field_name)


class DatabaseManager[ModelT](BaseDatabaseManager[ModelT]):
    async def get(self, id_: Identifier) -> ModelT:
        id_field = getattr(self.model_class, self.id_field_name)
        return await self.select_one(self.get_query().where(id_field == id_))

    async def list_(
        self,
        *positional_query: ColumnExpressionArgument[Any],
        page: int = 1,
        per_page: int = 10,
    ) -> list[ModelT]:
        stmt = self.get_query().where(*positional_query)
        if page and per_page:
            stmt = stmt.limit(per_page).offset(per_page * (page - 1))
        return list(await self.select(stmt))

    async def create(self, data: dict | ModelT) -> ModelT:
        item = data
        if not isinstance(data, self.model_class):
            item = self.model_class(**data)
        self.session.add(item)
        await self.session.flush()
        item_id = self.get_item_id(item)
        created = await self.get(item_id)
        return created

    async def bulk_create(self, items: list[dict | BaseModel | ModelT], **kwargs) -> list[ModelT]:
        create_data = []
        for item in items:
            create_data.append(item.model_dump(mode='json') if isinstance(item, BaseModel) else item)
        stmt = insert(self.model_class).values(create_data).returning(self.model_class)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id_: Identifier, data: dict) -> ModelT:
        stmt = (
            update(self.model_class)
            .where(self.model_class.id.expression == id_)
            .values(**data)
            .returning(self.model_class)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is None:
            raise ValueError(f'{self.model_class.__name__}({id_}) not found')
        return updated

    async def delete(self, id_: Identifier) -> None:
        stmt = delete(self.model_class).where(self.model_class.id.expression == id_)
        await self.session.execute(stmt)

    async def delete_many(self, ids: list[int | str], session: AsyncSession | None = None):
        pass


class PostgresDatabaseManager[ModelT](DatabaseManager[ModelT]):
    async def bulk_create(
        self,
        items: list[dict | BaseModel | ModelT],
        fail_silently: bool = False,
    ) -> list[ModelT]:
        create_data = [
            item.model_dump(mode='json') if isinstance(item, BaseModel) else item for item in items
        ]
        stmt = postgres_insert(self.model_class)
        if fail_silently:
            stmt = stmt.on_conflict_do_nothing()
        stmt = stmt.returning(self.model_class)
        result = await self.session.execute(stmt, create_data)
        return list(result.scalars().all())
