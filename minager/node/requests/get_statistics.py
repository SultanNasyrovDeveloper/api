from typing import TypedDict

from minager.core.surorm import (
    Alias,
    Count,
    Equals,
    F,
    Greater,
    Response,
    Select,
    String,
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
                Alias('total_repetitions', F.math.sum('repetitions')),
                Alias('total_size', F.math.sum('size')),
                Alias('outdated', Count(Greater(TimeNow(), 'next_optimal_repetition'))),
                Alias('empty_nodes', Count(Equals('size', '0'))),
            )
            .where(f'owner_id = {String(self._config['owner_id']).sql()}')
            .group(all_=True)
        )
        return await self._db.query(query)
