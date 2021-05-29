from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import numpy as np

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager)
import matplotlib.pyplot as plt

class Chart:

    def __init__(self, time, value):
        self.t0 = time
        x = np.array([(time-self.t0).total_seconds()])
        y = np.array([value])

        #plt.ion()
        self.fig = plt.figure()
        ax = self.fig.add_subplot(111)
        self.line1, = ax.plot(x, y, 'b-')

    def __repr__(self):
        return f"Chart(time={self.t0}, value={self.value})"

    def update(self, time, value):
        self.line1.set_ydata(value)
        self.line1.set_xdata([(time-self.t0).total_seconds()])
        self.fig.canvas.draw()



