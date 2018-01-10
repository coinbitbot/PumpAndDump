import json
import logging
import smtplib
import time
import datetime

from poloniex import Poloniex
from creds_vm import POLONIEX_API_KEY, POLONIEX_SECRET_KEY, GMAIL_USER, GMAIL_PASSWORD

PAIRS = ['BTC_ETH', 'BTC_XRP', 'BTC_XEM', 'BTC_LTC', 'BTC_STR', 'BTC_BCN', 'BTC_DGB', 'BTC_ETC', 'BTC_SC', 'BTC_DOGE',
         'BTC_BTS', 'BTC_GNT', 'BTC_XMR', 'BTC_DASH', 'BTC_ARDR', 'BTC_STEEM', 'BTC_NXT', 'BTC_ZEC',
         'BTC_STRAT', 'BTC_DCR', 'BTC_NMC', 'BTC_MAID', 'BTC_BURST', 'BTC_GAME', 'BTC_FCT', 'BTC_LSK', 'BTC_FLO',
         'BTC_CLAM', 'BTC_SYS', 'BTC_GNO', 'BTC_REP', 'BTC_RIC', 'BTC_XCP', 'BTC_PPC', 'BTC_AMP', 'BTC_SJCX', 'BTC_LBC',
         'BTC_EXP', 'BTC_VTC', 'BTC_GRC', 'BTC_NAV', 'BTC_FLDC', 'BTC_POT', 'BTC_RADS', 'BTC_BELA', 'BTC_NAUT',
         'BTC_BTCD', 'BTC_XPM', 'BTC_NOTE', 'BTC_NXC', 'BTC_PINK', 'BTC_OMNI', 'BTC_VIA', 'BTC_XBC', 'BTC_NEOS',
         'BTC_PASC', 'BTC_BTM', 'BTC_SBD', 'BTC_VRC', 'BTC_BLK', 'BTC_BCY', 'BTC_XVC', 'BTC_HUC', 'BTC_BCH', 'BTC_ZRX']

BUY_ENSURE_COEF = 1.5
CANDLE_4H_PERIOD = 14400
CANDLE_2H_PERIOD = 7200
PERIOD_MOD = 3
CANDLES_NUM = 4 * PERIOD_MOD
HIGHER_COEF = 1.55
LOWER_COEF = 3.7
VOL_COEF = 1.9
MAX_VOL_COEF = 5.5
NUM_OF_PAIRS = 9
MIN_PAIRS = 1
TRADE_AMOUNT = 0.1
DEPTH_OF_SELLING_GLASS = 200
STOP_LOSS = 0.75
TAKE_PROFIT = 1.7
COEF_ALL_CANDLE_MIN = 2
COEF_ALL_CANDLE_MID = 3.2
COEF_ALL_CANDLE_MAX = 5.5
COEF_HIGH_LOW_MIN = 0.5
COEF_HIGH_LOW_MAX = 2
MIN_VOLUME_TO_TRADE = 500
SWORD_MULTIPLIER = 2
HUMMER_MULTIPLIER = 2


class Gmail(object):
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.server = 'smtp.gmail.com'
        self.port = 587
        session = smtplib.SMTP(self.server, self.port)
        session.ehlo()
        session.starttls()
        session.ehlo
        session.login(self.email, self.password)
        self.session = session

    def send_message(self, subject, body):
        """ This must be removed """
        headers = [
            "From: " + self.email,
            "Subject: " + subject,
            "To: " + self.email,
            "MIME-Version: 1.0",
            "Content-Type: text/html"]
        headers = "\r\n".join(headers)
        self.session.sendmail(
            self.email,
            self.email,
            headers + "\r\n\r\n" + body)


def create_poloniex_connection():
    polo = Poloniex()
    polo.key = POLONIEX_API_KEY
    polo.secret = POLONIEX_SECRET_KEY
    return polo


def is_green(candle):
    return True if candle['close'] >= candle['open'] else False


def is_dodge(candle):
    if (candle['high'] - candle['low']) / (
                abs(candle['close'] - candle['open']) + 0.0001) > COEF_ALL_CANDLE_MAX and COEF_HIGH_LOW_MIN < (
                candle['high'] - max([candle['close'], candle['open']])) / (
                    min([candle['close'], candle['open']]) - candle['low'] + 0.0001) < COEF_HIGH_LOW_MAX:
        return True
    else:
        return False


def is_hummer(candle):
    higth_part = candle['high'] - max([candle['open'], candle['close']])
    middle = candle['open'] - candle['close']
    low_part = min([candle['open'], candle['close']]) - candle['low']

    return True if (higth_part + (abs(middle) * HUMMER_MULTIPLIER)) < low_part else False


def is_sword(candle):
    higth_part = candle['high'] - max([candle['open'], candle['close']])
    middle = candle['open'] - candle['close']
    low_part = min([candle['open'], candle['close']]) - candle['low']

    return True if (abs(middle) + (low_part * SWORD_MULTIPLIER)) < higth_part else False


def is_simple(candle):
    return True if not is_dodge(candle) and not is_hummer(candle) and not is_sword(candle) else False


def is_fat(candle):
    if COEF_ALL_CANDLE_MID > (candle['high'] - candle['low']) / (
                abs(candle['close'] - candle['open']) + 0.0001) > COEF_ALL_CANDLE_MIN and COEF_HIGH_LOW_MIN < (
                candle['high'] - max([candle['close'], candle['open']])) / (
                    min([candle['close'], candle['open']]) - candle['low'] + 0.0001) < COEF_HIGH_LOW_MAX:
        return True
    else:
        return False


def is_raise_vol(candle1, candle2):
    return True if candle2['volume'] > candle1['volume'] else False


def candle_12h_creator(candles_data):
    for i in range(len(candles_data)):
        if candles_data[0]['date'] % 43200 != 0:
            candles_data = candles_data[1:]
        else:
            break
    if len(candles_data) % 3 == 1:
        candles_data = candles_data[:-1]
    elif len(candles_data) % 3 == 2:
        candles_data = candles_data[:-2]
    elif len(candles_data) % 3 == 0:
        candles_data = candles_data[:-3]
    candles_12h_data = []
    candle_3na4 = []
    for candle in candles_data:
        candle_3na4.append(candle)
        if len(candle_3na4) == 3:
            candle_12h = {'high': (
                max([float(candle_3na4[0]['high']), float(candle_3na4[1]['high']), float(candle_3na4[2]['high'])])),
                'low': (min([float(candle_3na4[0]['low']), float(candle_3na4[1]['low']),
                             float(candle_3na4[2]['low'])])),
                'volume': (sum([float(candle_3na4[0]['volume']), float(candle_3na4[1]['volume']),
                                float(candle_3na4[2]['volume'])])),
                'close': float(candle_3na4[2]['close']), 'open': float(candle_3na4[0]['open']),
                'date': int(candle_3na4[0]['date'])}
            candle_3na4 = []
            candles_12h_data.append(candle_12h)

    return candles_12h_data


def check_hard_condition(candle):
    candle_close = candle['close']
    candle_open = candle['open']
    candle_high = candle['high']
    candle_low = candle['low']

    if candle_close > candle_open:
        close_open = candle_close - candle_open
        high_candle = candle_high - candle_close
        candle_low = candle_open - candle_low if \
            candle_open != candle_low else 0.0001
    elif candle_close < candle_open:
        close_open = candle_open - candle_close
        high_candle = candle_high - candle_open
        candle_low = candle_close - candle_low if \
            candle_close != candle_low else 0.0001
    else:
        close_open = 0.0001
        candle_low = candle_close - candle_low if \
            candle_close != candle_low else 0.0001
        high_candle = candle_high - candle_open
    if high_candle / close_open > HIGHER_COEF \
            and high_candle / candle_low > LOWER_COEF:
        return False
    else:
        return True


def main():
    polo = create_poloniex_connection()
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        filename='{}log/logger{}.log'.format(PROJECT_PATH,
                                                             time.strftime('%Y_%m_%d', datetime.datetime.now(
                                                             ).timetuple())))
    with open(PROJECT_PATH + 'bot_daily_btc_pairs.json') as data_file:
        pairs_bought = json.load(data_file)
    with open(PROJECT_PATH + 'bot_daily_btc_date.json') as data_file:
        last_bought_date = json.load(data_file)
    if pairs_bought != '':
        if pairs_bought != 'no pairs':
            balances = polo.returnBalances()
            null_balances_pairs = 0
            for pair in pairs_bought:
                altcoin_amount = float(balances[pair['name'].split('_')[-1]])
                if altcoin_amount > 0:
                    current_buy_glass = polo.returnOrderBook(pair['name'], depth=DEPTH_OF_SELLING_GLASS)['bids']
                    sum_previous = 0
                    sell_price = 0
                    for order in current_buy_glass:
                        sum_previous += float(order[1])
                        if float(sum_previous) >= BUY_ENSURE_COEF * altcoin_amount:
                            while True:
                                sell_price = float(order[0])
                                if sell_price != 0:
                                    break
                                else:
                                    logging.info('Sell price of {} = 0'.format(pair['name']))
                            break
                    two_h_data = polo.returnChartData(
                        pair['name'], period=CANDLE_2H_PERIOD, start=last_bought_date - CANDLE_2H_PERIOD)[:-1]
                    candles_2h_data = [
                        {'high': float(candle['high']), 'low': float(candle['low']), 'volume': float(candle['volume']),
                         'close': float(candle['close']), 'open': float(candle['open'])}
                        for candle in two_h_data
                    ]
                    first_candle_condition = True if len(candles_2h_data) == 1 and is_green(
                        candles_2h_data[0]) and is_hummer(candles_2h_data[0]) else False
                    second_candle_condition = False
                    if len(candles_2h_data) == 2 and ((is_green(candles_2h_data[0]) and is_green(
                            candles_2h_data[1]) and ((is_simple(candles_2h_data[0]) and is_simple(
                        candles_2h_data[1]) and not is_raise_vol(candles_2h_data[0], candles_2h_data[1])) or (
                                    is_simple(candles_2h_data[0]) and is_dodge(candles_2h_data[1])) or (
                                        is_sword(candles_2h_data[0]) and is_hummer(
                                        candles_2h_data[1])))) or (not is_green(candles_2h_data[0]) and is_green(
                        candles_2h_data[1]) and ((is_simple(candles_2h_data[0]) and is_hummer(
                        candles_2h_data[1]) and not is_raise_vol(candles_2h_data[0], candles_2h_data[1])) or (
                                    is_hummer(candles_2h_data[0]) and is_simple(
                                    candles_2h_data[1]) and not is_raise_vol(
                                candles_2h_data[0], candles_2h_data[1])))) or (
                                        not is_green(candles_2h_data[0]) and not is_green(
                                        candles_2h_data[1]) and is_sword(candles_2h_data[0]) and is_simple(
                                candles_2h_data[1])) or (is_green(candles_2h_data[0]) and not is_green(
                                            candles_2h_data[1]) and is_hummer(candles_2h_data[0]) and is_simple(
                                    candles_2h_data[0]) and not is_raise_vol(candles_2h_data[0], candles_2h_data[1]))):
                        second_candle_condition = True
                    third_candle_condition = False
                    if len(candles_2h_data) == 3 and ((is_green(candles_2h_data[0]) and not is_green(
                            candles_2h_data[1]) and not is_green(candles_2h_data[2]) and is_simple(
                        candles_2h_data[1]) and ((is_hummer(candles_2h_data[0]) and is_simple(candles_2h_data[2])) or (
                                is_sword(candles_2h_data[0]) and is_sword(candles_2h_data[2])))) or (
                                                is_green(candles_2h_data[0]) and not is_green(
                                                candles_2h_data[1]) and is_green(candles_2h_data[2]) and is_simple(
                                        candles_2h_data[0]) and is_simple(candles_2h_data[1]) and is_sword(
                                candles_2h_data[2])) or (
                                                is_green(candles_2h_data[0]) and is_green(
                                                candles_2h_data[1]) and is_green(candles_2h_data[2]) and is_simple(
                                        candles_2h_data[0]) and is_hummer(
                                    candles_2h_data[1]) and is_simple(candles_2h_data[2]))):
                        third_candle_condition = True
                    fourth_candle_condition = False
                    if len(candles_2h_data) == 4 and ((is_green(candles_2h_data[0]) and is_green(
                            candles_2h_data[1]) and is_green(candles_2h_data[2]) and is_green(
                        candles_2h_data[3]) and is_simple(candles_2h_data[0]) and is_simple(
                        candles_2h_data[1]) and is_hummer(candles_2h_data[2]) and is_sword(candles_2h_data[3])) or (
                                                is_green(candles_2h_data[0]) and is_green(
                                                candles_2h_data[1]) and is_green(
                                            candles_2h_data[2]) and not is_green(
                                        candles_2h_data[3]) and is_simple(candles_2h_data[0]) and is_simple(
                                        candles_2h_data[1]) and is_simple(candles_2h_data[2]) and is_sword(
                                candles_2h_data[3])) or (is_green(candles_2h_data[0]) and is_green(
                        candles_2h_data[1]) and not is_green(
                        candles_2h_data[2]) and not is_green(
                        candles_2h_data[3]) and is_simple(candles_2h_data[0]) and is_simple(
                        candles_2h_data[1]) and is_simple(candles_2h_data[2]) and is_simple(candles_2h_data[3]))):
                        fourth_candle_condition = True

                    if (time.time() - last_bought_date >= (CANDLE_4H_PERIOD * PERIOD_MOD) or sell_price < STOP_LOSS *
                                pair['price'] or sell_price > TAKE_PROFIT * pair['price']) or first_candle_condition or\
                            second_candle_condition or third_candle_condition or fourth_candle_condition:
                        polo.sell(pair['name'], sell_price, altcoin_amount)
                        logging.info(
                            'Selling {} {}. Price: {}'.format(altcoin_amount, pair['name'].split('_')[-1], sell_price))

                        gm = Gmail(GMAIL_USER, GMAIL_PASSWORD)
                        gm.send_message('SELL_DAILY', 'Selling {} {}. Price: {}. Time: {}'.format(
                            altcoin_amount, pair['name'].split('_')[-1], sell_price, datetime.datetime.now()))
                    if float(polo.returnBalances()[pair['name'].split('_')[-1]]) > 0:
                        null_balances_pairs += 1

            if (time.time() - float(last_bought_date)) >= (CANDLE_4H_PERIOD * PERIOD_MOD) and null_balances_pairs == 0:
                with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                    json.dump('', f)
        else:
            if (time.time() - float(last_bought_date)) >= (CANDLE_4H_PERIOD * PERIOD_MOD):
                with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                    json.dump('', f)
    with open(PROJECT_PATH + 'bot_daily_btc_pairs.json') as data_file:
        pairs_bought = json.load(data_file)
    if pairs_bought == '':
        pairs_info = []
        currencies_info = polo.returnCurrencies()
        for pair in PAIRS:
            if currencies_info[pair.split('_')[-1]]['frozen'] == 1 or \
                            currencies_info[pair.split('_')[-1]]['delisted'] == 1:
                continue
            candles_data = polo.returnChartData(
                pair, period=CANDLE_4H_PERIOD, start=int(time.time()) - CANDLE_4H_PERIOD * CANDLES_NUM)
            data = [
                {'high': float(candle['high']), 'low': float(candle['low']), 'volume': float(candle['volume']),
                 'close': float(candle['close']), 'open': float(candle['open']), 'date': float(candle['date'])}
                for candle in candles_data
            ]
            data_12h_candles = candle_12h_creator(data)
            print(pair)
            if data_12h_candles[2]['volume'] > MIN_VOLUME_TO_TRADE and data_12h_candles[1][
                'volume'] > MIN_VOLUME_TO_TRADE and (
                            data_12h_candles[1]['close'] > data_12h_candles[1]['open'] or data_12h_candles[2]['close'
                    ] > data_12h_candles[2]['open']) and ((check_hard_condition(data_12h_candles[2]) and MAX_VOL_COEF >
                    data_12h_candles[2]['volume'] / data_12h_candles[1]['volume'] > VOL_COEF) or (
                        (check_hard_condition(data_12h_candles[1]) and MAX_VOL_COEF > data_12h_candles[1][
                            'volume'] / data_12h_candles[0][
                            'volume'] > VOL_COEF) and (is_dodge(data_12h_candles[2]) or is_fat(data_12h_candles[2])))):
                pairs_info.append({
                    'name': pair,
                    'coef': data_12h_candles[1]['volume'] / data_12h_candles[0]['volume']
                })
        logging.info('Number of pairs: {}'.format(len(pairs_info)))
        pairs_info = sorted(pairs_info, key=lambda k: k['coef'], reverse=True)[:NUM_OF_PAIRS] if len(
            pairs_info) >= MIN_PAIRS else []
        balances = polo.returnBalances()
        current_btc = float(balances['BTC'])
        if len(pairs_info) > 0:
            buy_amount = TRADE_AMOUNT / len(pairs_info) if current_btc > TRADE_AMOUNT else current_btc / len(
                pairs_info)
            for pair_info in pairs_info:
                current_sell_glass = [
                    [float(order[0]), float(order[1]), float(order[0]) * float(order[1])]
                    for order in polo.returnOrderBook(pair_info['name'], depth=DEPTH_OF_SELLING_GLASS)['asks']
                ]
                sum_previous = 0
                order_price = 0
                for order in current_sell_glass:
                    sum_previous += order[2]
                    if sum_previous >= BUY_ENSURE_COEF * buy_amount:
                        order_price = order[0]
                        break
                if order_price:
                    polo.buy(pair_info['name'], order_price, buy_amount / order_price)
                    logging.info('Buying {} for {} BTC'.format(pair_info['name'].split('_')[-1], buy_amount))
                    pair_info['price'] = order_price

                    gm = Gmail(GMAIL_USER, GMAIL_PASSWORD)
                    gm.send_message(
                        'BUY_DAILY', 'Buying {}{} for {} BTC with rate {} at {}'.format(
                            buy_amount / order_price, pair_info['name'].split(
                                '_')[-1], buy_amount, order_price, datetime.datetime.now()))
            with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                json.dump([{'name': p['name'], 'price': p['price']} for p in pairs_info], f)
        else:
            with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                json.dump('no pairs', f)
        with open(PROJECT_PATH + 'bot_daily_btc_date.json', 'w') as f:
            json.dump((int(time.time())//CANDLE_2H_PERIOD) * CANDLE_2H_PERIOD + 60, f)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.exception('message')
