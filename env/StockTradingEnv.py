import random
import json
import gym
from gym import spaces
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from datetime import datetime

MAX_ACCOUNT_BALANCE = 2147483647
MAX_NUM_SHARES = 2147483647
MAX_SHARE_PRICE = 5000
MAX_OPEN_POSITIONS = 5
MAX_STEPS = 20000

INITIAL_ACCOUNT_BALANCE = 10000


class StockTradingEnv(gym.Env):
    """A stock trading environment for OpenAI gym"""
    metadata = {'render.modes': ['human']}

    def __init__(self, df, frame_bound):
        super(StockTradingEnv, self).__init__()
        self.df = df[frame_bound[0]:frame_bound[1]]
        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.reward_range = (0, MAX_ACCOUNT_BALANCE)

        # Actions of the format Buy x%, Sell x%, Hold, etc.
        self.action_space = spaces.Box(
            low=np.array([0, 0]), high=np.array([3, 1]), dtype=np.float16)

        # Prices contains the OHCL values for the last five prices
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(6, 6), dtype=np.float16)

        self._position_history = []
        self.frame_bound = frame_bound
        self._prices = []
        self._dates = []
        self.current_step = 6

    def _next_observation(self):
        # Get the stock data points for the last 5 days and scale to between 0-1
        # print("self.current_step: ",self.current_step)
        frame = np.array([
            np.array(self.df['Open'][self.current_step-6 : self.current_step] / MAX_SHARE_PRICE),
            np.array(self.df['High'][self.current_step-6 : self.current_step] / MAX_SHARE_PRICE),
            np.array(self.df['Low'][self.current_step-6 : self.current_step] / MAX_SHARE_PRICE),
            np.array(self.df['Close'][self.current_step-6 : self.current_step] / MAX_SHARE_PRICE),
            np.array(self.df['Volume'][self.current_step-6 : self.current_step] / MAX_NUM_SHARES),
        ])
        # print("sample: ",np.array(self.df['Open'][self.current_step-6 : self.current_step] / MAX_SHARE_PRICE))
        # print("frame: ",frame)
        # Append additional data and scale each value to between 0-1
        obs = np.append(frame, [[
            self.balance / MAX_ACCOUNT_BALANCE,
            self.max_net_worth / MAX_ACCOUNT_BALANCE,
            self.shares_held / MAX_NUM_SHARES,
            self.cost_basis / MAX_SHARE_PRICE,
            self.total_shares_sold / MAX_NUM_SHARES,
            self.total_sales_value / (MAX_NUM_SHARES * MAX_SHARE_PRICE),
        ]], axis=0)

        return obs

    def _take_action(self, action):
        # Set the current price to a random price within the time step
        current_price = random.uniform(
            float(self.df["Open"][self.current_step:self.current_step+1]), float(self.df["Close"][self.current_step:self.current_step+1]))

        action_type = action[0]
        amount = action[1]

        if action_type < 1:
            # Buy amount % of balance in shares
            total_possible = int(self.balance / current_price)
            shares_bought = int(total_possible * amount)
            prev_cost = self.cost_basis * self.shares_held
            additional_cost = shares_bought * current_price

            self.balance -= additional_cost
            try:
                self.cost_basis = (
                    prev_cost + additional_cost) / (self.shares_held + shares_bought)
            except:
                self.cost_basis = 0
            self.shares_held += shares_bought
            self._position_history.append(0)

        elif action_type < 2:
            # Sell amount % of shares held
            shares_sold = int(self.shares_held * amount)
            self.balance += shares_sold * current_price
            self.shares_held -= shares_sold
            self.total_shares_sold += shares_sold
            self.total_sales_value += shares_sold * current_price
            self._position_history.append(1)
        else:
            self._position_history.append(2)

        self._prices.append(float(self.df["Close"][self.current_step:self.current_step+1]))
        # self._dates.append(datetime.strptime(str(self.df["Date"][self.current_step:self.current_step+1].values[0]),'%d-%m-%Y').date())
        self._dates.append(str(self.df["Date"][self.current_step:self.current_step+1].values[0]))
        self.net_worth = self.balance + self.shares_held * current_price

        if self.net_worth > self.max_net_worth:
            self.max_net_worth = self.net_worth

        if self.shares_held == 0:
            self.cost_basis = 0

    def step(self, action):
        # Execute one time step within the environment
        self._take_action(action)

        self.current_step += 1
        done = False
        # print(f"self.current_step: {self.current_step}, len(df): {len(self.df)}")
        if self.current_step >= len(self.df):
            # print("STOP HERE")
            # self._position_history = []
            # self._prices = []
            # self._dates = []
            done = True
            self.current_step = 6

        delay_modifier = (self.current_step / MAX_STEPS)

        reward = self.balance * delay_modifier
        # done = self.net_worth <= 0

        obs = self._next_observation()
        # print(f"observation : {obs}, reward : {reward}, done: {done}")

        return obs, reward, done, {}

    def reset(self):
        # Reset the state of the environment to an initial state
        self.balance = INITIAL_ACCOUNT_BALANCE
        self.net_worth = INITIAL_ACCOUNT_BALANCE
        self.max_net_worth = INITIAL_ACCOUNT_BALANCE
        self.shares_held = 0
        self.cost_basis = 0
        self.total_shares_sold = 0
        self.total_sales_value = 0

        # Set the current step to a random point within the data frame
        # self.current_step = random.randint(
        #     0, len(self.df.loc[:, 'Open'].values) - 6)
        # self.current_step =len(self.df) - self.frame_bound - 6
        self.current_step = 6

        return self._next_observation()

    def render(self, mode='human', close=False):
        # Render the environment to the screen
        profit = self.net_worth - INITIAL_ACCOUNT_BALANCE

        print(f'Step: {self.current_step}')
        print(f'Balance: {self.balance}')
        print(
            f'Shares held: {self.shares_held} (Total sold: {self.total_shares_sold})')
        print(
            f'Avg cost for held shares: {self.cost_basis} (Total sales value: {self.total_sales_value})')
        print(
            f'Net worth: {self.net_worth} (Max net worth: {self.max_net_worth})')
        print(f'Profit: {profit}')

    def render_all(self):
        buy_signals, sell_signals, hold_signals = [], [], []
        buy_prices, sell_prices, hold_prices = [], [], []
        # print("_position_history: ",self._position_history)
        # print("_prices: ",self._prices)
        # print("_dates: ",self._dates)
        for i in range(len(self._position_history)):
            signal = self._position_history[i]
            price = self._prices[i]
            if signal == 0:
                buy_signals.append(i)
                buy_prices.append(price)
            elif signal == 1:
                sell_signals.append(i)
                sell_prices.append(price)
            else:
                hold_signals.append(i)
                hold_prices.append(price)
        # plt.plot_date(self.df['Date'][6:6+len(self._prices)],self._prices)
        # plt.plot_date(self.df['Date'][6:6+len(self._prices)],[i for i in range(len(self._dates))])
        plt.plot(self._dates,self._prices)
        plt.scatter(buy_signals, buy_prices,color='green', label='Buy signal')
        plt.scatter(sell_signals, sell_prices,color='red', label='Sell signal')
        plt.scatter(hold_signals, hold_prices,color='grey', label='Hold signal')
        plt.gcf().autofmt_xdate()
        plt.legend()
        plt.show()
