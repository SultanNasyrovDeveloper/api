from abc import ABCMeta, abstractmethod

from . import utils

type Numeric = int | float


class BaseIndexComponent(metaclass=ABCMeta):
    name: str = 'No name'
    default_weight: int | None = None

    @abstractmethod
    def calculate(self, *args, **kwargs) -> tuple[Numeric, float]:
        score = self.calculate_score(*args, **kwargs)
        weight = self.calculate_weight(score)
        return weight, score

    @abstractmethod
    def calculate_score(self, *args, **kwargs) -> Numeric:
        pass

    @abstractmethod
    def calculate_weight(self, value: float) -> Numeric:
        pass


class BaseIndex(metaclass=ABCMeta):
    name: str = 'No name'
    components: list[BaseIndexComponent]

    def calculate(self, *args, **kwargs):
        weights_and_values = []
        for component in self.components:
            score, weight = component.calculate(*args, **kwargs)
            weights_and_values.append((weight, score))
        return utils.geometric_mean(weights_and_values)
