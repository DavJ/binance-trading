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

from matplotlib import pyplot as plt
from scipy import optimize
#from scipy.interpolate import spline

import logging

logger = get_logger('Kalman2')

#see also https://github.com/pykalman/pykalman
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
        derivative = np.diff(self.measurements, axis=0, prepend=0)
        for d in range(self.number_of_derivations):
            self.measurements_plus_derivations = np.concatenate((self.measurements_plus_derivations, derivative), axis=1)
            if d < self.number_of_derivations - 1:
                derivative = np.diff(derivative, axis=0, prepend=0)

        logger.info('smoothing data ...')
        self.results_smoothed = self.kf.em(self.measurements_plus_derivations, n_iter=10).smooth(self.measurements_plus_derivations)[0]
        logger.info('smoothing finished...')
        self.plot()

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
       now first are taken pairs that are far from average price and also first derivative is big in absolute value
       and second derivative is close to 0
       :return:
       """
       def sorting_criteria(x):
           try:
               return abs(x[1]*x[2]/x[3])  # bigger the difference from avg, bigger the change (first derivative) and
                                           # smaller the second derivative (close to extreme) => prioritize trade
           except ZeroDivisionError:
               return np.Infinity          #zero second derivative means min or max was reached => prioritize trade

       return sorted([(self.trading_pairs[i],
                       self.results_smoothed[0][i], #average predicted
                       self.results_smoothed[0][i + self.number_of_pairs],  #first derivative predicted
                       self.results_smoothed[0][i + 2*self.number_of_pairs]  #second derivative predicted
                       ) for i in range(self.n_dim_obs)],
                     key=sorting_criteria, reverse=True)

    def dump_sorted(self):
       print('sorted predictions')
       for prediction in self.sorted_predictions:
           print(prediction)

    def plot(self):
        DISPLAYED_DATA = 450
        POLYNOME_ORDER = 9
        plt.title('Kalman filtering and smoothing')
        plt.xlabel('sequence number [15min intervals]')
        plt.xlabel('relative price')
        x = np.arange(0, np.shape(self.measurements)[0])[-DISPLAYED_DATA:]
        xfit = np.arange(0, POLYNOME_ORDER)
        y1 = np.transpose(self.measurements_plus_derivations)[0][-DISPLAYED_DATA:]  #original data
        y2 = np.transpose(self.results_smoothed)[0][-DISPLAYED_DATA:]  #smoothed
        y3 = np.transpose(self.results_smoothed)[0 + self.number_of_pairs][-DISPLAYED_DATA:] # smoothed derivation
        y4 = np.transpose(self.results_smoothed)[0 + 2 * self.number_of_pairs][-DISPLAYED_DATA:]  # smoothed second derivation

        fig, axs = plt.subplots(2, 2)
        fig.suptitle('Kalman filtering')

        axs[0, 0].plot(x, y1, 'tab:blue')
        axs[0, 0].plot(xfit, np.polyfit(x, y1, POLYNOME_ORDER), 'tab:cyan')
        axs[0, 0].set_title('original')

        axs[1, 0].plot(x, y2, 'tab:green')
        axs[1, 0].plot(xfit, np.polyfit(x, y2, POLYNOME_ORDER), 'tab:cyan')
        axs[1, 0].set_title('filtered')

        axs[0, 1].plot(x, y3, 'tab:orange')
        axs[0, 1].plot(xfit, np.polyfit(x, y3, POLYNOME_ORDER), 'tab:cyan')
        axs[0, 1].set_title('filtered derivation')

        axs[1, 1].plot(x, y4, 'tab:red')
        axs[1, 1].plot(xfit, np.polyfit(x, y4, POLYNOME_ORDER), 'tab:cyan')
        axs[1, 1].set_title('filtered second derivation')

        plt.show()
        pass
