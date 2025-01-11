"""
    Strategy Description:
        The VWAP Crossover Delivery strategy uses the Volume-Weighted Average Price (VWAP) to determine entry and exit points based on price crossovers.
        Trades are initiated when the price crosses above or below the VWAP, signaling potential trends.
        The strategy exits positions when the crossover condition is met again, aiming to capitalize on trend reversals.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/vwap_crossover/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/
"""

from pyalgotrading.constants import *
from pyalgotrading.indicator.vwap import VWAP
from pyalgotrading.strategy import StrategyBase


class VWAPCrossoverDelivery(StrategyBase):
    name = 'VWAP Crossover Delivery'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        vwap = VWAP(hist_data)
        crossover_value = self.utils.crossover(hist_data['close'], vwap)
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
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size, order_code=BrokerOrderCodeConstants.DELIVERY)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            main_order = self.main_order_map.get(instrument)
            if main_order is not None and main_order.get_order_status() is BrokerOrderStatusConstants.COMPLETE:
                crossover = self.get_crossover_value(instrument)

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
