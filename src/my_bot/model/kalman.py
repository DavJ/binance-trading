from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import numpy as np
from pykalman import KalmanFilter

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager)

class Kalman:

    def __init__(self, time=None, value=None, variation=None, n_dim=3):
        if n_dim != 3:
            raise NotImplementedError('kalman only supports 3 dimensions now')
        self.n_dim = n_dim
        self.state = np.array([[value, 0, 0],
                                [0, 0, 0],
                                [0, 0, 0]])
        self.covariance = np.eye(n_dim)
        self.observation_covariance = np.array([[0.0001, 0, 0],
                                               [0, 0, 0],
                                               [0, 0, 0]])
        self.transition_covariance = np.array([[0.0001, 0.0001, 0.0001],
                                               [0.0001, 0.0001, 0.0001],
                                               [0.0001, 0.0001, 0.0001]])
        self.kf = KalmanFilter(
            transition_covariance=self.transition_covariance,  # H
            observation_covariance=self.observation_covariance,  # Q
        )
        self.previous_value = 0 if value is None else value
        self.previous_variation = 0 if variation is None else variation
        self.previous_time = time.time() if time is None else time

    def __repr__(self):
        return f"Kalman(time={self.previous_time}, value={self.value}, variance={self.variance}, n_dim={self.n_dim})"

    def update(self, time, value):

        dt = (time - self.previous_time).total_seconds()
        #observations = np.array([[value, (value-self.previous_value)/dt]])
        observations = np.array([[value, 0, 0]])

        self.state, self.covariance = self.kf.filter_update(
            self.state,
            self.covariance,
            observations,
            transition_matrix=self.transition_matrix(dt),
            observation_matrix=np.array([[1, 0, 0], [0, 0, 0], [0, 0, 0]]),
            # observation_offset = np.array([, 0, 0])
            # observation_covariance=np.array(0.1*np.eye(1))
        )
        self.previous_time = time
        self.previous_value = value

    def predict_value(self, time):
       """
       :param self:
       :param dt:
       :return:
       """
       tm = self.transition_matrix((time-self.previous_time).total_seconds())
       return np.matmul(self.state, tm)[0][0]

    @property
    def value(self):
        return self.state[0]

    @property
    def variance(self):
        return self.covariance[0]

    def transition_matrix(self, dt):
        return np.array([[1.0, dt, 0.5*dt**2], [0.0, 1.0, dt], [0.0, 0.0, 1.0]])
