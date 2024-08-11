"""
    checkout:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/aroon_crossover/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/
"""
from pyalgotrading.strategy import *
import talib

class On_Balace_Volume(StrategyBase):
    name = 'On-balance Volume'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_period = self.strategy_parameters['TIME_PERIOD']
        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_crossover_value(self, instrument):
        hist_data = self.get_historical_data(instrument)
        obv = talib.OBV(hist_data['close'], hist_data['volume'])
        obv_ema = talib.EMA(obv,timeperiod=self.time_period)
        crossover_value = self.utils.crossover(obv, obv_ema)
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
                    meta.append({"action": 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True

        return False
