import json, websocket
from config import *
from abc import ABC, abstractmethod


class IWebSocket(ABC):

    @abstractmethod
    def on_open(ws):
        pass

    @abstractmethod
    def on_close(ws):
        pass

    @abstractmethod
    def on_message(ws, message):
        pass
