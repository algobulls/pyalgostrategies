"""
    Strategy Description:
        The EMA Regular Order Intraday strategy leverages the crossover of two Exponential Moving Averages (EMAs) to identify short-term trading opportunities during the trading day.
        A buy position is entered when the shorter EMA crosses above the longer EMA, while a sell position is triggered when the shorter EMA crosses below.
        Positions are exited on intraday trend reversals indicated by another EMA crossover.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/ema_crossover/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.strategy import StrategyBase


class EMARegularOrderIntraday(StrategyBase):
    name = 'EMA Regular Order Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timeperiod1 = self.strategy_parameters['TIMEPERIOD1']
        self.timeperiod2 = self.strategy_parameters['TIMEPERIOD2']

        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_crossover_value(self, instrument):
        hist_data = self.get_historical_data(instrument)

        ema_x = talib.EMA(hist_data['close'], timeperiod=self.timeperiod1)
        ema_y = talib.EMA(hist_data['close'], timeperiod=self.timeperiod2)

        crossover_value = self.utils.crossover(ema_x, ema_y)
        return crossover_value

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
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
            if self.main_order_map.get(instrument) is not None:
                crossover = self.get_crossover_value(instrument)

                if crossover in [1, -1]:
                    selected_instruments.append(instrument)
                    meta.append({'action': 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True
        return False
