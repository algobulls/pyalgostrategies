import talib

from pyalgotrading.constants import *
from pyalgotrading.strategy.strategy_base import StrategyBase


class StrategyMACDBracketOrder(StrategyBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fastMA_period = self.strategy_parameters['FASTMA_PERIOD']
        self.slowMA_period = self.strategy_parameters['SLOWMA_PERIOD']
        self.signal_period = self.strategy_parameters['SIGNAL_PERIOD']
        self.stoploss = self.strategy_parameters['STOPLOSS_TRIGGER']
        self.target = self.strategy_parameters['TARGET_TRIGGER']
        self.trailing_stoploss = self.strategy_parameters['TRAILING_STOPLOSS_TRIGGER']

        assert (0 < self.fastMA_period == int(self.fastMA_period)), f"Strategy parameter FASTMA_PERIOD should be a positive integer. Received: {self.fastMA_period}"
        assert (0 < self.slowMA_period == int(self.slowMA_period)), f"Strategy parameter SLOWMA_PERIOD should be a positive integer. Received: {self.slowMA_period}"
        assert (0 < self.signal_period == int(self.signal_period)), f"Strategy parameter SIGNAL_PERIOD should be a positive integer. Received: {self.signal_period}"
        assert (0 < self.stoploss < 1), f"Strategy parameter STOPLOSS_TRIGGER should be a positive fraction between 0 and 1. Received: {self.stoploss}"
        assert (0 < self.target < 1), f"Strategy parameter TARGET_TRIGGER should be a positive fraction between 0 and 1. Received: {self.target}"
        assert (0 < self.trailing_stoploss), f"Strategy parameter TRAILING_STOPLOSS_TRIGGER should be a positive number. Received: {self.trailing_stoploss}"

        self.main_order = None

    def initialize(self):
        self.main_order = {}

    @staticmethod
    def name():
        return 'MACD Bracket Order Strategy'

    @staticmethod
    def versions_supported():
        return [AlgoBullsEngineVersion.VERSION_3_3_0]

    def get_crossover_value(self, instrument):
        hist_data = self.get_historical_data(instrument)
        macdline, macdsignal, _ = talib.MACD(hist_data['close'],
                                             fastperiod=self.fastMA_period,
                                             slowperiod=self.slowMA_period,
                                             signalperiod=self.signal_period)
        return self.utils.crossover(macdline, macdsignal)

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):

        selected_instruments_bucket = []
        sideband_info_bucket = []

        for instrument in instruments_bucket:
            crossover_value = self.get_crossover_value(instrument)
            if crossover_value == 1:
                selected_instruments_bucket.append(instrument)
                sideband_info_bucket.append({'action': 'BUY'})
            elif crossover_value == -1:
                if self.strategy_mode is StrategyMode.INTRADAY:
                    selected_instruments_bucket.append(instrument)
                    sideband_info_bucket.append({'action': 'SELL'})

        return selected_instruments_bucket, sideband_info_bucket

    def strategy_enter_position(self, candle, instrument, sideband_info):
        if sideband_info['action'] == BrokerOrderTransactionTypeConstants.BUY:
            qty = self.number_of_lots * instrument.lot_size
            ltp = self.broker.get_ltp(instrument)
            self.main_order[instrument] = \
                self.broker.place_order(instrument=instrument,
                                        order_transaction_type=BrokerOrderTransactionTypeConstants.BUY,
                                        order_type=BrokerOrderTypeConstants.BRACKET,
                                        order_code=BrokerOrderCodeConstants.INTRADAY,
                                        order_variety=BrokerOrderVarietyConstants.LIMIT,
                                        quantity=qty,
                                        price=ltp,
                                        stoploss_trigger=ltp -
                                        (ltp * self.stoploss),
                                        target_trigger=ltp +
                                        (ltp * self.target),
                                        trailing_stoploss_trigger=ltp * self.trailing_stoploss)

        elif sideband_info['action'] == BrokerOrderTransactionTypeConstants.SELL:
            qty = self.number_of_lots * instrument.lot_size
            ltp = self.broker.get_ltp(instrument)
            self.main_order[instrument] = \
                self.broker.place_order(instrument=instrument,
                                        order_transaction_type=BrokerOrderTransactionTypeConstants.SELL,
                                        order_type=BrokerOrderTypeConstants.BRACKET,
                                        order_code=BrokerOrderCodeConstants.INTRADAY,
                                        order_variety=BrokerOrderVarietyConstants.LIMIT,
                                        quantity=qty,
                                        price=ltp,
                                        stoploss_trigger=ltp +
                                        (ltp * self.stoploss),
                                        target_trigger=ltp -
                                        (ltp * self.target),
                                        trailing_stoploss_trigger=ltp * self.trailing_stoploss)
        else:
            raise SystemExit(
                f'Got invalid sideband_info value: {sideband_info}')

        return self.main_order[instrument]

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        selected_instruments_bucket = []
        sideband_info_bucket = []

        for instrument in instruments_bucket:
            if self.main_order.get(instrument) is not None:
                crossover_value = self.get_crossover_value(instrument)
                if crossover_value in [1, -1]:
                    selected_instruments_bucket.append(instrument)
                    sideband_info_bucket.append({'action': 'EXIT'})
        return selected_instruments_bucket, sideband_info_bucket

    def strategy_exit_position(self, candle, instrument, sideband_info):
        if sideband_info['action'] == 'EXIT':
            self.main_order[instrument].exit_position()
            self.main_order[instrument] = None
            return True
        return False
