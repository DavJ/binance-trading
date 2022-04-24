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


class Kalman3:

    def __init__(self, trading_pairs=get_trading_pairs(), number_of_derivations=2):
        self.kf = None
        self.measurements = None
        self.measurements_plus_derivations = None
        self.results_smoothed = None
        self.trading_pairs = trading_pairs
        self.number_of_pairs =  len(self.trading_pairs)
        self.n_dim_obs = len(trading_pairs) * (number_of_derivations + 1)
        self.kf = KalmanFilter(n_dim_obs=self.n_dim_obs, n_dim_state=self.n_dim_obs,
                               em_vars=['transition_covariance', 'observation_covariance'])
        self.number_of_derivations = number_of_derivations

    def __repr__(self):
        return f"Kalman2(trading_pairs={self.trading_pairs}, state_multiple={self.state_multiple})"

    def update(self):
        INTERVAL = Client.KLINE_INTERVAL_1HOUR
        logger.info('getting measurements ...')
        self.measurements = np.transpose(asyncio.run(get_normalized_close_prices_async(pairs=self.trading_pairs,
                                                                                       interval=INTERVAL)))

        self.measurements_plus_derivations = np.copy(self.measurements)
        derivative = np.diff(self.measurements)
        for d in range(self.number_of_derivations):
            self.measurements_plus_derivations = np.concatenate(self.measurements_plus_derivations, derivative)
            if d < self.number_of_derivations - 1:
                derivative = np.diff(derivative)

        logger.info('smoothing data ...')
        self.results_smoothed = self.kf.em(self.measurements_plus_derivations, n_iter=5).smooth(self.measurements_plus_derivations)[0]
        logger.info('smoothing finished...')

    def predict_values(self):
       """
       :param self:
       :param dt:
       :return:
       """
       return self.results_smoothed[0]

    @property
    def sorted_predictions(self):
       """
       now first are taken pairs that are far from average price and also first derivative is big in absolute value
       and second derivative is close to 0
       :return:
       """
       return sorted([(self.trading_pairs[i],
                       self.results_smoothed[0][i], #average predicted
                       self.results_smoothed[0][i + self.number_of_pairs],  #first derivative predicted
                       self.results_smoothed[0][i + 2*self.number_of_pairs]  #second derivative predicted
                       ) for i in range(self.n_dim_obs)],
                     key=lambda x: abs(x[1]*x[2]/x[3]), reverse=True)

    def dump_sorted(self):
       print('sorted predictions')
       for prediction in self.sorted_predictions:
           print(prediction)
