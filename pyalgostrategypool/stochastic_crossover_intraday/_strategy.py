"""
    Strategy Description:
        The Stochastic Crossover Intraday strategy utilizes the Stochastic Oscillator to detect short-term overbought and oversold conditions.
        A buy signal is generated when the fast Stochastic line crosses above the slow line, and a sell signal occurs when it crosses below.
        This strategy targets intraday trades, aiming to capitalize on short-term price movements.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/stochastic_crossover/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.constants import *
from pyalgotrading.strategy import StrategyBase


class StochasticCrossoverIntraday(StrategyBase):
    name = 'Stochastic Crossover Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fastk_period = self.strategy_parameters.get('FASTK_PERIOD') or self.strategy_parameters.get('PERIOD')
        self.slowk_period = self.strategy_parameters.get('SLOWK_PERIOD') or self.strategy_parameters.get('SMOOTH_K_PERIOD')
        self.slowd_period = self.strategy_parameters.get('SLOWD_PERIOD') or self.strategy_parameters.get('SMOOTH_D_PERIOD')

        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_crossover_value(self, instrument):
        hist_data = self.get_historical_data(instrument)
        slowk, slowd = talib.STOCH(hist_data['high'], hist_data['low'], hist_data['close'], fastk_period=self.fastk_period,
                                   slowk_period=self.slowk_period, slowk_matype=0, slowd_period=self.slowd_period, slowd_matype=0)
        crossover_value = self.utils.crossover(slowk, slowd)
        return crossover_value

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is None:
                crossover = self.get_crossover_value(instrument)
                action_constants = {1: 'BUY', -1: 'SELL'}

                if crossover in [-1, 1]:
                    selected_instruments.append(instrument)
                    meta.append({'action': action_constants[crossover]})

        return selected_instruments, meta

    def strategy_enter_position(self, candle, instrument, meta):
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            main_order = self.main_order_map.get(instrument)

            if main_order is not None and main_order.get_order_status() is BrokerOrderStatusConstants.COMPLETE:
                crossover = self.get_crossover_value(instrument)

                if crossover in [1, -1]:
                    selected_instruments.append(instrument)
                    meta.append({'action': "EXIT"})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True

        return False
