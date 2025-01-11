"""
    Strategy Description:
        The Reverse RSI Crossover Intraday strategy leverages the reversal of the RSI indicator to trigger buy and sell signals for intraday trading.
        A buy signal is generated when the RSI crosses below the oversold level, and a sell signal when it crosses above the overbought level.
        The strategy focuses on capturing short-term price reversals within the same trading day.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/reverse_rsi/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.strategy import StrategyBase


class ReverseRSICrossoverIntraday(StrategyBase):
    name = 'Reverse RSI Crossover Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_period = self.strategy_parameters['TIME_PERIOD']
        self.overbought_value = self.strategy_parameters['OVERBOUGHT_VALUE']
        self.oversold_value = self.strategy_parameters['OVERSOLD_VALUE']

        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_crossover_value(self, instrument):
        hist_data = self.get_historical_data(instrument)

        rsi_value = talib.RSI(hist_data['close'], timeperiod=self.time_period)

        oversold_list = [self.oversold_value] * rsi_value.size
        overbought_list = [self.overbought_value] * rsi_value.size

        oversold_crossover_value = self.utils.crossover(rsi_value, oversold_list)
        overbought_crossover_value = self.utils.crossover(rsi_value, overbought_list)

        return oversold_crossover_value, overbought_crossover_value

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is None:
                oversold_crossover_value, overbought_crossover_value = self.get_crossover_value(instrument)

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
                oversold_crossover_value, overbought_crossover_value = self.get_crossover_value(instrument)

                if (oversold_crossover_value == -1 and self.main_order_map[instrument].order_transaction_type.value == 'BUY') or (overbought_crossover_value == 1 and self.main_order_map[instrument].order_transaction_type.value == 'SELL'):
                    selected_instruments.append(instrument)
                    meta.append({'action': 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True

        return False
