from pyalgotrading.constants import *
from pyalgotrading.strategy import StrategyBase


class OpenRangeBreakoutCrossoverBracket(StrategyBase):

    def __init__(self, *args, **kwargs):
        """
       Accept and sanitize all your parameters here.
       Setup the variables you will need here.
       If you are running the strategy for multiple days, then this method will be called only once at the start of the strategy.
       """

        super().__init__(*args, **kwargs)

        # Open Range Breakout parameters
        self.start_time_hours = self.strategy_parameters['START_TIME_HOURS']
        self.start_time_minutes = self.strategy_parameters['START_TIME_MINUTES']
        self.stoploss = self.strategy_parameters['STOPLOSS_TRIGGER']
        self.target = self.strategy_parameters['TARGET_TRIGGER']
        self.trailing_stoploss = self.strategy_parameters['TRAILING_STOPLOSS_TRIGGER']

        # Strategy start time
        try:
            self.candle_start_time = time(hour=self.start_time_hours, minute=self.start_time_minutes)
        except ValueError:
            self.logger.fatal('Error converting hours and minutes... EXITING')
            raise SystemExit

        # Sanity
        assert (0 < self.stoploss < 1), f"Strategy parameter STOPLOSS_TRIGGER should be a positive fraction between 0 and 1. Received: {self.stoploss}"
        assert (0 < self.target < 1), f"Strategy parameter TARGET_TRIGGER should be a positive fraction between 0 and 1. Received: {self.target}"
        assert (0 < self.trailing_stoploss), f"Strategy parameter TRAILING_STOPLOSS_TRIGGER should be a positive number. Received: {self.trailing_stoploss}"

        # Variables
        self.main_order = None
        self.current_order_count = None
        self.allowed_order_count = None

    def initialize(self):
        """
        If you are running the strategy for multiple days, then this method will be called only once at the start of every day.
        Use this to initialize and re-initialize your variables.
        """

        self.main_order = {}

        # To keep a count of the number of orders for each instrument
        self.current_order_count = {}

        # Count of number of orders should not exceed the below count
        self.allowed_order_count = 2

    @staticmethod
    def name():
        """
        Name of your strategy.
        """

        return 'Open Range Breakout Crossover Bracket'

    @staticmethod
    def versions_supported():
        """
        Strategy should always support the latest engine version.
        Current version is 3.3.0
        """

        return AlgoBullsEngineVersion.VERSION_3_3_0

    def get_decision(self, instrument, decision):
        """
        This method returns the entry/exit action based on the crossover value
        """

        crossover_value = 0

        # Get OHLC historical data for the instrument
        hist_data = self.get_historical_data(instrument)

        # Get latest timestamp
        timestamp_str = str(hist_data['timestamp'].iloc[-1].to_pydatetime().time())

        # Get string value of strategy start time
        udc_candle_str = str(self.candle_start_time)

        latest_close = hist_data['close'].iloc[-1]

        # Get crossover value if decision is ENTRY_POSITION and latest timestamp is equal to strategy start time or decision is EXIT_POSITION
        if (decision is DecisionConstants.ENTRY_POSITION and timestamp_str > udc_candle_str) or decision is DecisionConstants.EXIT_POSITION:
            crossover_value = self.get_crossover_value(hist_data, latest_close)

        # Return action as BUY if crossover is Upwards and decision is Entry, else SELL if decision is EXIT
        if crossover_value == 1:
            action = ActionConstants.ENTRY_BUY if decision is DecisionConstants.ENTRY_POSITION else ActionConstants.EXIT_SELL

        # Return action as SELL if crossover is Downwards and decision is Entry, else BUY if decision is EXIT
        elif crossover_value == -1:
            action = ActionConstants.ENTRY_SELL if decision is DecisionConstants.ENTRY_POSITION else ActionConstants.EXIT_BUY

        # Return action as NO_ACTION if there is no crossover
        else:
            action = ActionConstants.NO_ACTION
        return action

    def get_crossover_value(self, hist_data, latest_close):
        """
        This method calculates the crossover using the hist data of the instrument along with the required indicator and returns the crossover value.
        """

        crossover = 0

        # Calculate crossover for the OHLC columns with
        columns = ['open', 'high', 'low', 'close']
        val_data = [latest_close] * len(hist_data)
        for column in columns:
            crossover = self.utils.crossover(hist_data[column], val_data)
            if crossover in [1, -1]:
                # If crossover is upwards or downwards, stop computing the crossovers
                break

        # Return the crossover values
        return crossover

    def strategy_select_instruments_for_entry(self, candle, instruments_bucket):
        """
        This method is called once every candle time.
        If you set the candle at 5 minutes, then this method will be called every 5 minutes (09:15, 09:20, 09:25 and so on).
        In a candle, the exit method is called first, then the entry method is called.
        So once a candle starts, strategy_select_instruments_for_exit gets called first
        and then this method strategy_select_instruments_for_entry gets called.
        """

        # Add instrument in this bucket if you want to place an order for it
        # We decide whether to place an instrument in this bucket or not based on the decision making process given below in the loop
        selected_instruments_bucket = []

        # Add accompanying info in this bucket for that particular instrument in the bucket above
        sideband_info_bucket = []

        # If current time is equal to greater than strategy start time, then take entry decision
        if clock.CLOCK.now().time() >= self.candle_start_time:

            # Looping over all instruments given by you in the bucket (we can give multiple instruments in the configuration)
            for instrument in instruments_bucket:

                # Initiate the count
                if self.current_order_count.get(instrument) is None:
                    self.current_order_count[instrument] = 0

                # Compute various things and get the decision to place an order only if no current order is going on (main order is empty / none) and the number of order counts is less than the count
                if self.main_order.get(instrument) is None and self.current_order_count.get(instrument) < self.allowed_order_count:

                    # Get entry decision
                    action = self.get_decision(instrument, DecisionConstants.ENTRY_POSITION)

                    if action is ActionConstants.ENTRY_BUY or (action is ActionConstants.ENTRY_SELL and self.strategy_mode is StrategyMode.INTRADAY):
                        # Add instrument to the bucket
                        selected_instruments_bucket.append(instrument)

                        # Add additional info for the instrument
                        sideband_info_bucket.append({'action': action})

        # Return the buckets to the core engine
        # Engine will now call strategy_enter_position with each instrument and its additional info one by one
        return selected_instruments_bucket, sideband_info_bucket

    def strategy_enter_position(self, candle, instrument, sideband_info):
        """
        This method is called once for each instrument from the bucket in this candle.
        Place an order here and return it to the core.
        """

        # Quantity formula (number of lots comes from the config)
        qty = self.number_of_lots * instrument.lot_size

        # Last traded price of the instrument
        ltp = self.broker.get_ltp(instrument)

        # Place buy order
        if sideband_info['action'] is ActionConstants.ENTRY_BUY:
            self.main_order[instrument] = self.broker.BuyOrderBracket(instrument=instrument, order_code=BrokerOrderCodeConstants.INTRADAY, order_variety=BrokerOrderVarietyConstants.LIMIT, quantity=qty, price=ltp,
                                                                      stoploss_trigger=ltp - (ltp * self.stoploss), target_trigger=ltp + (ltp * self.target), trailing_stoploss_trigger=ltp * self.trailing_stoploss)

        # Place sell order
        elif sideband_info['action'] is ActionConstants.ENTRY_SELL:
            self.main_order[instrument] = self.broker.SellOrderBracket(instrument=instrument, order_code=BrokerOrderCodeConstants.INTRADAY, order_variety=BrokerOrderVarietyConstants.LIMIT, quantity=qty, price=ltp,
                                                                       stoploss_trigger=ltp + (ltp * self.stoploss), target_trigger=ltp - (ltp * self.target), trailing_stoploss_trigger=ltp * self.trailing_stoploss)

        # Sanity
        else:
            raise SystemExit(f'Got invalid sideband_info value: {sideband_info}')

        # Return the order to the core engine for management
        return self.main_order[instrument]

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        """
        This method is called once every candle time.
        If you set the candle at 5 minutes, then this method will be called every 5 minutes (09:15, 09:20, 09:25 and so on).
        In a candle, the exit method is called first, then the entry method is called.
        So once a candle starts, this method strategy_select_instruments_for_exit gets called first
        and then strategy_select_instruments_for_entry gets called.
        """

        # Add instrument in this bucket if you want to place an (exit) order for it
        # We decide whether to place an instrument in this bucket or not based on the decision making process given below in the loop
        selected_instruments_bucket = []

        # Add accompanying info in this bucket for that particular instrument in the bucket above
        sideband_info_bucket = []

        for instrument in instruments_bucket:
            main_order = self.main_order.get(instrument)

            # Compute various things and get the decision to place an (exit) order only if there is a current order is going on (main order is not empty / none)
            # Also check if order status is complete
            if main_order is not None and main_order.get_order_status() is BrokerOrderStatusConstants.COMPLETE:

                # Check for action (decision making process)
                action = self.get_decision(instrument, DecisionConstants.EXIT_POSITION)

                # For this strategy, we take the decision as:
                # If order transaction type is buy and current action is sell or order transaction type is sell and current action is buy, then exit the order
                if (action is ActionConstants.EXIT_SELL and main_order.order_transaction_type is BrokerOrderTransactionTypeConstants.SELL) or \
                        (action is ActionConstants.EXIT_BUY and main_order.order_transaction_type is BrokerOrderTransactionTypeConstants.BUY):
                    # Increment the count if the order is exited
                    self.current_order_count[instrument] += 1

                    # Add instrument to the bucket
                    selected_instruments_bucket.append(instrument)

                    # Add additional info for the instrument
                    sideband_info_bucket.append({'action': action})

        # Return the buckets to the core engine
        # Engine will now call strategy_exit_position with each instrument and its additional info one by one
        return selected_instruments_bucket, sideband_info_bucket

    def strategy_exit_position(self, candle, instrument, sideband_info):
        """
        This method is called once for each instrument from the bucket in this candle.
        Exit an order here and return the instrument status to the core.
        """

        if sideband_info['action'] in [ActionConstants.EXIT_BUY, ActionConstants.EXIT_SELL]:
            # Exit the main order
            self.main_order[instrument].exit_position()

            # Set it to none so that entry decision can be taken properly
            self.main_order[instrument] = None

            # Return true so that the core engine knows that this instrument has exited completely
            return True

        # Return false in all other cases
        return False
