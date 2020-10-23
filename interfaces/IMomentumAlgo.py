from abc import ABC, abstractmethod

class IMomentumAlgo(ABC):
    '''Interface for Momentum Algorithms '''

    @abstractmethod
    def display_header(self):
        pass

    @abstractmethod
    def input_data(self):
        pass

    @abstractmethod
    def visualize_data(self, data):
        pass

    @abstractmethod
    def execute(self):
        pass
