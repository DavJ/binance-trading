from .model import AbstractModel

class Currency(AbstractModel):
    currency: str = ''

    def __init__(self, **kwargs):
        super().__init__(currency=None, **kwargs)
        self.currency = self.currency

