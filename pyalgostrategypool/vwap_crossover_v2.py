from indicator.vwap import VWAP
from pyalgotrading.constants import *
from pyalgotrading.strategy.strategy_base import StrategyBase


class VWAPCrossover(StrategyBase):
    name = 'VWAP Crossover v2'

    def __init__(self, *args, **kwargs):

        """
        Accept and sanitize all your parameters here.
        Setup the variables ou will need here.
        If you are running the strategy for multiple days, then this method will be called only once at the start of the strategy.
        """

        super().__init__(*args, **kwargs)

        # Variables
        self.main_order_map = None

    def initialize(self):
        """
        If you are running the strategy for multiple days, then this method will be called only once at the start of every day.
        Use this to initialize and re-initialize your variables.
        """

        self.main_order_map = {}

    def get_crossover_value(self, instrument):
        """
        This method calculates the crossover using the hist data of the instrument along with the required indicator.
        """

        # Get OHLC historical data for the instrument
        hist_data = self.get_historical_data(instrument)

        # Calculate the VWAP values
        vwap = VWAP(hist_data)

        # Get the crossover value
        crossover_value = self.utils.crossover(hist_data['close'], vwap)

        return crossover_value

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
        selected_instruments = []

        # Add accompanying info in this bucket for that particular instrument in the bucket above
        meta = []

        # Looping over all instruments given by you in the bucket (we can give multiple instruments in the configuration)
        for instrument in instruments_bucket:

            # Compute various things and get the decision to place an order only if no current order is going on (main order is empty / none)
            if self.main_order_map.get(instrument) is None:

                # Check for crossover (decision-making process)
                crossover = self.get_crossover_value(instrument)

                # define key values for action
                action_constants = {1: 'BUY', -1: 'SELL'}

                if crossover in [-1, 1]:
                    # Add instrument to the bucket
                    selected_instruments.append(instrument)
                    # Add additional info for the instrument
                    meta.append({'action': action_constants[crossover]})

        # Return the buckets to the core engine.
        # Engine will now call strategy_enter_position with each instrument and its additional info one by one
        return selected_instruments, meta

    def strategy_enter_position(self, candle, instrument, meta):
        """
        This method is called once for each instrument from the bucket in this candle.
        Place an order here and return it to the core.
        """

        # Place buy order
        self.main_order_map[instrument] = _ = self.broker.OrderRegular(instrument, meta['action'], quantity=self.number_of_lots * instrument.lot_size)
        return _

    def strategy_select_instruments_for_exit(self, candle, instruments_bucket):
        """
        This method is called once every candle time.
        If you set the candle at 5 minutes, then this method will be called every 5 minutes (09:15, 09:20, 09:25 and so on).
        In a candle, the exit method is called first, then the entry method is called
        So once a candle starts, this method strategy_select_instruments_for_exit gets called first
        and then strategy_select_instruments_for_entry gets called.
        """

        # Add instrument in this bucket if you want to place an (exit) order for it
        # We decide whether to place an instrument in this bucket or not based on the decision making process given below in the loop
        selected_instruments = []

        # Add accompanying info in this bucket for that particular instrument in the bucket above
        meta = []

        for instrument in instruments_bucket:
            main_order = self.main_order_map.get(instrument)

            # Compute various things and get the decision to place an (exit) order only if there is a current order is going on (main order is not empty / none)
            # Also check if order status is complete
            if main_order is not None and main_order.get_order_status() is BrokerOrderStatusConstants.COMPLETE:

                # Check for crossover (decision-making process)
                crossover = self.get_crossover_value(instrument)

                # For this strategy, we take the decision as:
                # If order transaction type is buy and crossover is downwards or order transaction type is sell and crossover is upwards, then exit the order
                if (crossover == 1 and self.main_order_map[instrument].order_transaction_type.value == 'SELL') or (crossover == -1 and self.main_order_map[instrument].order_transaction_type.value == 'BUY'):
                    # Add instrument to the bucket
                    selected_instruments.append(instrument)
                    # Add additional info for the instrument
                    meta.append({"action": 'EXIT'})

        # Return the buckets to the core engine
        # Engine will now call strategy_exit_position with each instrument and its additional info one by one
        return selected_instruments, meta

    def strategy_exit_position(self, candle, instrument, meta):
        """
        This method is called once for each instrument from the bucket in this candle.
        Exit an order here and return the instrument status to the core.
        """

        if meta['action'] == 'EXIT':
            # Exit the main order
            self.main_order_map[instrument].exit_position()

            # Set it to none so that entry decision can be taken properly
            self.main_order_map[instrument] = None

            # Return true so that the core engine knows that this instrument has exited completely
            return True

        # Return false in all other cases
        return False