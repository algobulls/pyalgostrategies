"""
    Strategy Description:
        The Volatility Trend ATR Intraday strategy uses the Average True Range (ATR) to assess short-term volatility shifts and determine trend strength.
        It enters trades when current volatility exceeds past levels and exits when trend reversals occur.
        This strategy targets intraday positions based on real-time volatility analysis.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/volatility_trent_atr/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

import talib
from pyalgotrading.strategy import StrategyBase


class VolatilityTrendATRIntraday(StrategyBase):
    name = 'Volatility Trend ATR Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timeperiod_atr = self.strategy_parameters['TIMEPERIOD_ATR']
        self.atr_prev_candles_num = self.strategy_parameters['ATR_PREV_CANDLES_NUM']
        self.main_order_map = None
        self.previous_trend = None
        self.current_trend = None
        self.action_constants = {1: 'BUY', -1: 'SELL'}

    def initialize(self):
        self.main_order_map = {}
        self.previous_trend = {}
        self.current_trend = {}

    def get_trend_direction(self, instrument):
        hist_data = self.get_historical_data(instrument)
        atr = talib.ATR(hist_data['high'], hist_data['low'], hist_data['close'], timeperiod=self.timeperiod_atr)
        current_atr = atr.iloc[-1]
        atr_prev_candles_num = atr.iloc[-self.atr_prev_candles_num]
        return 1 if current_atr > atr_prev_candles_num else -1 if current_atr < atr_prev_candles_num else 0

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is None:
                if self.current_trend.get(instrument) in [None, 0]:
                    current_trend = self.current_trend[instrument] = self.get_trend_direction(instrument)
                else:
                    current_trend = self.current_trend[instrument]

                if current_trend in [1, -1]:
                    instruments.append(instrument)
                    meta.append({'action': self.action_constants[current_trend]})
                    self.previous_trend[instrument] = self.current_trend[instrument]

        return instruments, meta

    def strategy_enter_position(self, candle, instrument, meta):
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        instruments, meta = [], []

        for instrument in instruments_bucket:
            if self.main_order_map.get(instrument) is not None:
                current_trend = self.current_trend[instrument] = self.get_trend_direction(instrument)
                self.current_trend[instrument] = current_trend
                if current_trend != 0:
                    if current_trend != self.previous_trend.get(instrument):
                        instruments.append(instrument)
                        meta.append({'action': 'EXIT'})

        return instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        if meta['action'] == 'EXIT':
            self.main_order_map[instrument].exit_position()
            self.main_order_map[instrument] = None
            return True

        return False
