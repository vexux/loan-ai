from abc import ABC, abstractmethod

from contracts.component.component_metadata import ComponentMetadata


class ComponentContract(ABC):

    @abstractmethod
    async def get_metadata(self) -> ComponentMetadata:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass