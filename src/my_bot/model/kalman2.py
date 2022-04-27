from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import numpy as np
from pykalman import KalmanFilter

from src.my_bot.basic_tools import (Client, CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager,
                                    get_trading_pairs, get_normalized_close_prices_async ,get_logger)

import logging

logger = get_logger('Kalman2')


class Kalman2:

    def __init__(self, trading_pairs=get_trading_pairs(), state_multiple=1):
        self.kf = None
        self.measurements = None
        self.results_smoothed = None
        self.trading_pairs = trading_pairs
        self.n_dim_obs = len(trading_pairs)
        self.n_dim_state = self.n_dim_obs * state_multiple
        self.kf = KalmanFilter(n_dim_obs=self.n_dim_obs, n_dim_state=self.n_dim_state,
                               em_vars=['transition_covariance', 'observation_covariance'])

    def __repr__(self):
        return f"Kalman2(trading_pairs={self.trading_pairs}, state_multiple={self.state_multiple})"

    def update(self):
        INTERVAL = Client.KLINE_INTERVAL_1HOUR
        logger.info('getting measurements ...')
        self.measurements = np.transpose(asyncio.run(get_normalized_close_prices_async(pairs=self.trading_pairs,
                                                                                       interval=INTERVAL)))

        logger.info('smoothing data ...')
        self.results_smoothed = self.kf.em(self.measurements, n_iter=5).smooth(self.measurements)[0]
        logger.info('smoothing finished...')

    def predict_values(self):
       """
       :param self:
       :param dt:
       :return:
       """
       return self.results_smoothed[-1]

    @property
    def sorted_predictions(self):
       """
       :return:
       """
       return sorted([(self.trading_pairs[i], 100*self.results_smoothed[-1][i]) for i in range(self.n_dim_obs)],
                     key=lambda x: abs(x[1]), reverse=True)

    def dump_sorted(self):
       print('sorted predictions')
       for prediction in self.sorted_predictions:
           print(prediction)
