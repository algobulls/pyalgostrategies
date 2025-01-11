"""
    Strategy Description:
        The Inverse EMA Scalping Regular Order Intraday strategy leverages inverse EMA crossovers for intraday trading.
        A buy is initiated when the shorter EMA crosses below the longer EMA, and a sell is triggered when the shorter EMA crosses above.
        Positions are exited upon subsequent crossovers, aiming to capitalize on short-term price reversals within the trading session.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/inverse_ema_scalping/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.strategy import StrategyBase


class InverseEMAScalpingRegularOrderIntraday(StrategyBase):
    name = 'Inverse EMA Scalping Regular Order Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.larger_time_period = self.strategy_parameters['LARGER_TIME_PERIOD']
        self.smaller_time_period = self.strategy_parameters['SMALLER_TIME_PERIOD']

        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_crossover_value(self, instrument):
        hist_data = self.get_historical_data(instrument)

        larger_ema = talib.EMA(hist_data['close'], timeperiod=self.larger_time_period)
        smaller_ema = talib.EMA(hist_data['close'], timeperiod=self.smaller_time_period)

        crossover_value = self.utils.crossover(smaller_ema, larger_ema)
        return crossover_value

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            crossover = self.get_crossover_value(instrument)
            action_constants = {-1: 'BUY', 1: 'SELL'}

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
                crossover_value = self.get_crossover_value(instrument)

                if crossover_value in [1, -1]:
                    selected_instruments.append(instrument)
                    meta.append({'action': 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True
        return False
