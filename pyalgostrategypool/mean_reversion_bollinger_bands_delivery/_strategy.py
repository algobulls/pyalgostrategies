"""
    Strategy Description:
        The Mean Reversion Bollinger Bands Delivery strategy uses Bollinger Bands to identify price reversals near the upper or lower bands.
        A buy signal is generated when the price rebounds from the lower band, while a sell signal occurs on reversals from the upper band.
        This strategy is tailored for delivery mode, focusing on capturing mean reversion opportunities.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/mean_reversion_bollinger_bands/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.constants import *
from pyalgotrading.strategy import StrategyBase


class MeanReversionBollingerBandsDelivery(StrategyBase):
    name = 'Mean Reversion Bollinger Bands Delivery'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timeperiod = self.strategy_parameters['TIMEPERIOD']
        self.std_deviation = self.strategy_parameters['STD_DEVIATION']
        self.main_order_map = None

    def initialize(self):
        self.main_order_map = {}

    def initialize_instrument(self, instrument):

        # Initialize the instrument for delivery mode by storing the first order in the main order map.
        if instrument.orders:
            # This assumes that there is only one order associated with the instrument, which is usually the case.
            # (If there are multiple orders, this method will only store the first one, which may not work as expected.)
            self.main_order_map[instrument] = instrument.orders[0]

    def get_decision(self, instrument):
        hist_data = self.get_historical_data(instrument)
        upper_band, _, lower_band = talib.BBANDS(hist_data['close'], timeperiod=self.timeperiod, nbdevup=self.std_deviation, nbdevdn=self.std_deviation, matype=0)
        upper_band_value = upper_band.iloc[-1]
        lower_band_value = lower_band.iloc[-1]
        latest_candle = hist_data.iloc[-1]
        previous_candle = hist_data.iloc[-2]

        if (previous_candle['open'] <= lower_band_value or previous_candle['low'] <= lower_band_value) and (latest_candle['close'] > previous_candle['close']):
            action = 'BUY'
        elif (previous_candle['open'] >= upper_band_value or previous_candle['close'] >= upper_band_value) and (latest_candle['close'] < previous_candle['close']):
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
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size, order_code=BrokerOrderCodeConstants.DELIVERY)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is not None:
                action = self.get_decision(instrument)
                action = None
                if action is not None:
                    selected_instruments.append(instrument)
                    meta.append({'action': 'EXIT'})

        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True

        return False
