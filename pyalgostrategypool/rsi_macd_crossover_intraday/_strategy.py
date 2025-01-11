"""
    Strategy Description:
        The RSI MACD Crossover Intraday strategy combines the MACD and RSI indicators to capture intraday buy and sell opportunities.
        A buy signal occurs when RSI crosses above the oversold level after a MACD crossover, and a sell signal triggers when RSI crosses below the overbought level.
        This strategy focuses on short-term, intraday positions with a focus on momentum shifts.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/rsi_macd_crossover/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.strategy import StrategyBase


class RSIMACDCrossoverIntraday(StrategyBase):
    name = 'RSI MACD Crossover Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timeperiod_fast = self.strategy_parameters['TIMEPERIOD_FAST']
        self.timeperiod_slow = self.strategy_parameters['TIMEPERIOD_SLOW']
        self.timeperiod_signal = self.strategy_parameters['TIMEPERIOD_SIGNAL']
        self.timeperiod_rsi = self.strategy_parameters['TIMEPERIOD_RSI']
        self.oversold_value = self.strategy_parameters['OVERSOLD_VALUE']
        self.overbought_value = self.strategy_parameters['OVERBOUGHT_VALUE']
        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_decision(self, instrument):
        hist_data = self.get_historical_data(instrument)
        macdline, macdsignal, _ = talib.MACD(hist_data['close'], fastperiod=self.timeperiod_fast, slowperiod=self.timeperiod_slow, signalperiod=self.timeperiod_signal)
        rsi_value = talib.RSI(macdsignal, timeperiod=self.timeperiod_rsi)

        oversold_list = [self.oversold_value] * rsi_value.size
        overbought_list = [self.overbought_value] * rsi_value.size

        oversold_crossover_value = self.utils.crossover(rsi_value, oversold_list)
        overbought_crossover_value = self.utils.crossover(rsi_value, overbought_list)

        return oversold_crossover_value, overbought_crossover_value

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is None:
                oversold_crossover_value, overbought_crossover_value = self.get_decision(instrument)
                if oversold_crossover_value == 1:
                    selected_instruments.append(instrument)
                    meta.append({'action': 'BUY'})

                elif overbought_crossover_value == -1:
                    selected_instruments.append(instrument)
                    meta.append({'action': 'SELL'})

        return selected_instruments, meta

    def strategy_enter_position(self, candle, instrument, meta):
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is not None:
                oversold_crossover_value, overbought_crossover_value = self.get_decision(instrument)
                if (oversold_crossover_value == -1) and self.main_order_map[instrument].order_transaction_type.value == 'SELL' or \
                        ((overbought_crossover_value == 1) and self.main_order_map[instrument].order_transaction_type.value == 'BUY'):
                    selected_instruments.append(instrument)
                    meta.append({'action': 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True

        return False
