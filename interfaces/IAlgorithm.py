from abc import ABC, abstractmethod


class IAlgorithm(ABC):

    @abstractmethod
    def ws_open(self, ws):
        pass

    @abstractmethod
    def ws_close(self, ws):
        pass

    @abstractmethod
    def ws_message(self, ws, message):
        pass