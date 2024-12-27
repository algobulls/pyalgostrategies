"""
    checkout:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/obv_breakout/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/
"""

import talib
from pyalgotrading.constants import *
from pyalgotrading.strategy import StrategyBase


class OBVBreakout(StrategyBase):
    name = 'OBV Breakout'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timeperiod = self.strategy_parameters.get('TIME_PERIOD',10)
        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_obv_value(self, instrument):
        hist_data = self.get_historical_data(instrument)
        obv = talib.OBV(hist_data['close'], hist_data['volume'])
        smoothed_obv = talib.SMA(obv, timeperiod=self.timeperiod)
        crossover_value = self.utils.crossover(obv, smoothed_obv)
        return crossover_value

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is None:
                crossover = self.get_obv_value(instrument)
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
                crossover = self.get_obv_value(instrument)

                if crossover in [1, -1]:
                    selected_instruments.append(instrument)
                    meta.append({"action": 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True

        return False