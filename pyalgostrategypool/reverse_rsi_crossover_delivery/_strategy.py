"""
    Strategy Description:
        The Reverse RSI Crossover Delivery strategy involves trading based on the reversal of the RSI indicator, entering positions when the RSI crosses over the overbought or oversold levels.
        A buy signal is triggered when RSI crosses below the oversold level, and a sell signal when it crosses above the overbought level.
        The strategy aims to capture price reversals during extreme market conditions for delivery mode trading.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/reverse_rsi/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.constants import *
from pyalgotrading.strategy import StrategyBase


class ReverseRSICrossoverDelivery(StrategyBase):
    name = 'Reverse RSI Crossover Delivery'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_period = self.strategy_parameters['TIME_PERIOD']
        self.overbought_value = self.strategy_parameters['OVERBOUGHT_VALUE']
        self.oversold_value = self.strategy_parameters['OVERSOLD_VALUE']

        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def initialize_instrument(self, instrument):

        # Initialize the instrument for delivery mode by storing the first order in the main order map.
        if instrument.orders:
            # This assumes that there is only one order associated with the instrument, which is usually the case.
            # (If there are multiple orders, this method will only store the first one, which may not work as expected.)
            self.main_order_map[instrument] = instrument.orders[0]

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
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size, order_code=BrokerOrderCodeConstants.DELIVERY)
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
