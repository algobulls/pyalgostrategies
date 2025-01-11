"""
    Strategy Description:
        The Bollinger Bands Intraday strategy leverages Bollinger Bands to identify intraday trading opportunities, entering buy positions when the price rebounds from the lower band or sell positions when it reverses from the upper band.
        It dynamically exits positions when price action signals a trend reversal. This strategy is designed for short-term trades, focusing on quick entries and exits within a single trading session.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/bollinger_bands/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/
"""

import talib
from pyalgotrading.constants import *
from pyalgotrading.strategy import StrategyBase


class BollingerBandsIntraday(StrategyBase):
    name = 'Bollinger Bands Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.time_period = self.strategy_parameters['TIME_PERIOD']
        self.std_deviations = self.strategy_parameters['STANDARD_DEVIATIONS']

        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def get_decision(self, instrument):
        hist_data = self.get_historical_data(instrument)

        upper_band, _, lower_band = talib.BBANDS(hist_data['close'], timeperiod=self.time_period, nbdevup=self.std_deviations, nbdevdn=self.std_deviations, matype=0)
        upper_band_value = upper_band.iloc[-1]
        lower_band_value = lower_band.iloc[-1]

        latest_candle = hist_data.iloc[-1]
        previous_candle = hist_data.iloc[-2]

        if (previous_candle['open'] <= lower_band_value or previous_candle['high'] <= lower_band_value or previous_candle['low'] <= lower_band_value or previous_candle['close'] <= lower_band_value) and \
                (latest_candle['close'] > previous_candle['close']):
            action = 'BUY'
        elif (previous_candle['open'] >= upper_band_value or previous_candle['high'] >= upper_band_value or previous_candle['low'] >= upper_band_value or previous_candle['close'] >= upper_band_value) and \
                (latest_candle['close'] < previous_candle['close']):
            action = 'SELL'
        else:
            action = None

        return action

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:

            if self.main_order_map.get(instrument) is None:
                action = self.get_decision(instrument)

                if action is not None:
                    selected_instruments.append(instrument)
                    meta.append({'action': action})

        return selected_instruments, meta

    def strategy_enter_position(self, candle, instrument, meta):
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            main_order = self.main_order_map.get(instrument)

            if main_order is not None and main_order.get_order_status() is BrokerOrderStatusConstants.COMPLETE:
                action = self.get_decision(instrument)

                if (action == 'SELL' and main_order.order_transaction_type is BrokerOrderTransactionTypeConstants.BUY) or (action == 'BUY' and main_order.order_transaction_type is BrokerOrderTransactionTypeConstants.SELL):
                    selected_instruments.append(instrument)
                    meta.append({'action': 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True
        return False
