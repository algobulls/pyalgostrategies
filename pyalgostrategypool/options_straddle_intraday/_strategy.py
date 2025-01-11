"""
    Strategy Description:
        The Options Straddle Intraday strategy involves buying both a call and a put option at the same strike price and expiry, anticipating significant price movement in either direction.
        It is ideal for volatile market conditions where large price swings are expected but the direction is uncertain.
        The strategy profits from sharp moves in the underlying asset, regardless of whether the price rises or falls.

    Strategy Resources:
        - strategy specific docs here : https://algobulls.github.io/pyalgotrading/strategies/options_straddle/
        - generalised docs in detail here : https://algobulls.github.io/pyalgotrading/strategies/strategy_guides/common_strategy_guide/

"""

from pyalgotrading.strategy import StrategyOptionsBase, OptionsStrikeDirection, OptionsInstrumentDirection


class OptionsStraddleIntraday(StrategyOptionsBase):
    name = 'Options Straddle Intraday'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Parameters (currently set with default values, can be overridden from the Parameters Configuration Pane)
        self._leg_one_transaction_type = self.strategy_parameters.get('LEG_ONE_TRANSACTION_TYPE', 2)  # BUY: 1 | SELL: 2
        self._leg_one_tradingsymbol_suffix = self.strategy_parameters.get('LEG_ONE_TRADING_SYMBOL_SUFFIX', 1)  # CE: 1 | PE: 2
        self._leg_one_strike_direction = self.strategy_parameters.get('LEG_ONE_STRIKE_DIRECTION', 1)  # ITM: 0| ATM: 1| OTM: 2
        self._leg_one_number_of_strikes = self.strategy_parameters.get('LEG_ONE_NUMBER_OF_STRIKES', 0)

        self._leg_two_transaction_type = self.strategy_parameters.get('LEG_TWO_TRANSACTION_TYPE', 2)  # BUY: 1 | SELL: 2
        self._leg_two_tradingsymbol_suffix = self.strategy_parameters.get('LEG_TWO_TRADING_SYMBOL_SUFFIX', 2)  # CE: 1 | PE: 2
        self._leg_two_strike_direction = self.strategy_parameters.get('LEG_TWO_STRIKE_DIRECTION', 1)  # ITM: 0| ATM: 1| OTM: 2
        self._leg_two_number_of_strikes = self.strategy_parameters.get('LEG_TWO_NUMBER_OF_STRIKES', 0)

        # Maps
        self.transaction_type_map = {1: "BUY", 2: "SELL"}
        self.tradingsymbol_suffix_map = {1: "CE", 2: "PE"}
        self.strike_direction_map = {0: OptionsStrikeDirection.ITM, 1: OptionsStrikeDirection.ATM, 2: OptionsStrikeDirection.OTM}

        # Variables
        self.number_of_allowed_expiry_dates = 1
        self.instruments_done_for_the_day = None

    def initialize(self):
        super().initialize()
        self.instruments_done_for_the_day = []

    def get_child_instrument_details(self, base_instrument, tradingsymbol_suffix, strike_direction, no_of_strikes):
        expiry_date = self.get_allowed_expiry_dates()[0]
        child_instrument = self.get_options_instrument_with_strike_direction(base_instrument, expiry_date, tradingsymbol_suffix, strike_direction, no_of_strikes)
        return child_instrument

    def options_instruments_set_up_local(self, base_instrument, tradingsymbol_suffix, current_close, direction=OptionsInstrumentDirection.EXACT):
        expiry_dates = self.get_allowed_expiry_dates()
        for expiry_date in expiry_dates:
            self.options_instruments_set_up(base_instrument, direction, expiry_date, tradingsymbol_suffix, current_close)

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        selected_instruments, meta = [], []

        for instrument in instruments_bucket:
            if instrument not in self.instruments_done_for_the_day:
                self.instruments_done_for_the_day.append(instrument)

                ltp = self.broker.get_ltp(instrument)

                # setup child instruments
                self.options_instruments_set_up_local(instrument, "CE", ltp)
                self.options_instruments_set_up_local(instrument, "PE", ltp)

                leg_wise_list = [('LEG_ONE', self._leg_one_tradingsymbol_suffix, self._leg_one_strike_direction, self._leg_one_number_of_strikes, self._leg_one_transaction_type),
                                 ('LEG_TWO', self._leg_two_tradingsymbol_suffix, self._leg_two_strike_direction, self._leg_two_number_of_strikes, self._leg_two_transaction_type)]

                for leg_number, tradingingsymbol_suffix, strike_direction, number_of_strikes, transaction_type in leg_wise_list:
                    self.logger.info(f'Processing {leg_number}...')
                    child_instrument = self.get_child_instrument_details(instrument, self.tradingsymbol_suffix_map[tradingingsymbol_suffix], self.strike_direction_map[strike_direction], number_of_strikes)
                    selected_instruments.append(child_instrument)
                    meta.append({'base_instrument': instrument, 'action': self.transaction_type_map[transaction_type]})

        return selected_instruments, meta

    def strategy_enter_position(self, candle, instrument, meta):
        _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        return [], []

    def strategy_exit_position(self, candle, instrument, meta):
        return False
