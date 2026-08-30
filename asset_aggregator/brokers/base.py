from __future__ import annotations

from abc import ABC, abstractmethod

from asset_aggregator.models import BrokerAssets


class BrokerClient(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> BrokerAssets:
        raise NotImplementedError
