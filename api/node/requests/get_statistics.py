from typing import TypedDict

from api.surorm import Response
from api.surorm.query import (
    Alias,
    Count,
    Equals,
    Greater,
    MathSum,
    Select,
    String,
    TimeNow,
)

from .abstract import AbstractRequest


class GetOverallStatisticsConfig(TypedDict):
    owner_id: str


class GetOverallStatisticsRequest(AbstractRequest[GetOverallStatisticsConfig]):
    async def perform(self) -> Response | None:
        query = (
            Select('node')
            .columns(
                Alias('total_nodes', Count()),
                Alias('total_repetitions', MathSum('repetitions')),
                Alias('total_size', MathSum('size')),
                Alias('outdated', Count(Greater(TimeNow(), 'next_optimal_repetition'))),
                Alias('empty_nodes', Count(Equals('size', '0'))),
            )
            .where(f'owner_id = {String(self._config['owner_id']).sql()}')
            .group(all_=True)
        )
        return await self._db.query(query.sql())
