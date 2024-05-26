import tkinter as tk
import pandas as pd
import re
import requests
import os
import time
import sys
import pytz
from tkinter import filedialog
from collections import defaultdict
from currency_converter import CurrencyConverter
from colorama import init, Fore, Style
from datetime import datetime
from dateutil import parser

# Init colorama
init(autoreset=True)

# Initialize CurrencyConverter without cache
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENCY_DATA_DIR = os.path.join(BASE_DIR, 'currency_converter')
CURRENCY_DATA_PATH = os.path.join(CURRENCY_DATA_DIR, 'eurofxref-hist.zip')
LAST_UPDATE_FILE_PATH = os.path.join(BASE_DIR, 'last_update_time.txt')
# CMC
CMC_API_KEY = "3e5a1c85-1d9c-4a4a-b955-e1d2e827be32" 

def initialize_currency_converter():
    if not os.path.exists(CURRENCY_DATA_DIR):
        os.makedirs(CURRENCY_DATA_DIR)

    if not os.path.exists(CURRENCY_DATA_PATH):
        print("Downloading eurofxref-hist.zip...")
        download_currency_data()

    if os.path.exists(CURRENCY_DATA_PATH):
        last_update_time = load_last_update_time()
        if time.time() - last_update_time > 8 * 3600:
            print("Refreshing currency data...")
            os.remove(CURRENCY_DATA_PATH)
            download_currency_data()

    return CurrencyConverter()

def download_currency_data():
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
    try:
        response = requests.get(url)
        with open(CURRENCY_DATA_PATH, 'wb') as file:
            file.write(response.content)
        save_last_update_time()
    except Exception as e:
        print(f"Error downloading currency data: {e}")

def load_last_update_time():
    try:
        with open(LAST_UPDATE_FILE_PATH, 'r') as file:
            last_update_time = float(file.read())
    except (FileNotFoundError, ValueError):
        last_update_time = 0
    return last_update_time

def save_last_update_time():
    with open(LAST_UPDATE_FILE_PATH, 'w') as file:
        file.write(str(time.time()))

def select_file():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    root.call('wm', 'attributes', '.', '-topmost', True)
    file_path = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    root.update()
    root.destroy()
    return file_path

def extract_amount_and_currency(value):
    match = re.match(r"([-+]?\d*\.?\d+)\s*(\w+)", str(value))
    if match:
        amount = abs(float(match.group(1)))
        currency = match.group(2)
        if currency.endswith('FIAT'):
            currency = currency[:-4]
        return amount, currency
    return 0, ""

def get_price_from_coinmarketcap(symbol):
    if symbol == 'BCD':
        return 1
    elif symbol == 'JB':
        return 0
    elif symbol == 'BCL':
        return 0.1

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    parameters = {"symbol": symbol.upper()}
    headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": CMC_API_KEY}

    response = requests.get(url, params=parameters, headers=headers)
    data = response.json()

    if response.status_code == 200 and data['status']['error_code'] == 0:
        symbol_upper = symbol.upper()
        if symbol_upper in data['data']:
            btc_price = data['data'][symbol_upper]['quote']['USD']['price']
            return btc_price
    return None

def print_currency_totals(totals, converter, unrecognized_currencies):
    total_usd_sum = 0
    for currency, total in totals.items():
        if currency in converter.currencies:
            total_usd = converter.convert(total, currency, 'USD')
            total_usd_sum += total_usd
            print(f"Total for {currency}: {total:.2f} {currency} (converted to {total_usd:.2f} USD)")
        else:
            price_from_coinmarketcap = get_price_from_coinmarketcap(currency)
            if price_from_coinmarketcap is not None:
                total_usd = total * price_from_coinmarketcap
                total_usd_sum += total_usd
                print(f"Total for {currency}: {total:.2f} {currency} (converted to {total_usd:.2f} USD)")
            else:
                unrecognized_currencies.append((currency, total))
                print(f"Total for {currency}: {total:.2f} {currency}")

    print("------------------------------------------------------------------")
    print(Fore.CYAN + f"Total USD value: {total_usd_sum:.2f} USD")
    if unrecognized_currencies:
        print(Fore.RED + "Unrecognized currencies:")
        for currency, total in unrecognized_currencies:
            print(Fore.RED + f"{total} {currency}")
    print("------------------------------------------------------------------")

def parse_datetime(input_str, is_end_time=False):
    try:
        # Attempt to parse the input string into a datetime object
        dt = parser.parse(input_str)

        if dt.hour == 0 and dt.minute == 0 and dt.second == 0 and not is_end_time:
            dt = dt.replace(hour=0, minute=0, second=0)
        elif dt.hour == 0 and dt.minute == 0 and dt.second == 0 and is_end_time:
            dt = dt.replace(hour=23, minute=59, second=59)

        return dt
    except parser.ParserError:
        print(f"Error parsing date: {input_str}")

        # Try to automatically convert from other date formats
        try:
            dt = datetime.strptime(input_str, "%m/%d/%Y %H:%M")
            if is_end_time:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            pass

        try:
            dt = datetime.strptime(input_str, "%Y/%m/%d %H:%M")
            if is_end_time:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            pass

        return None
        
def handle_promo_functionality(df, converter, timezone):
    print("Promotion Functionality:")
    if not timezone:
        timezone = "UTC"

    timezone_mapping = {}
    for i in range(-12, 13):
        timezone_mapping[f"UTC+{i}"] = f"Etc/GMT-{i}" if i != 0 else "Etc/GMT"
        timezone_mapping[f"UTC-{i}"] = f"Etc/GMT+{i}" if i != 0 else "Etc/GMT"

    if timezone in timezone_mapping:
        timezone = timezone_mapping[timezone]

    df['Create Date'] = pd.to_datetime(df['Create Date'], errors='coerce')
    if df['Create Date'].dt.tz is None:
        df['Create Date'] = df['Create Date'].dt.tz_localize('UTC')
    if timezone != 'UTC':
        df['Create Date'] = df['Create Date'].dt.tz_convert(timezone)

    game_names = input("Please enter game names to filter: ").strip().split(',')
    filtered_df = df[df['Game Name'].isin(game_names) & df['Description'].isin(['Original Bet', 'Original War', 'Third Party Bet', 'Trade Bet-Contest', 'Trade Bet-Contract', 'Trade Bet-Order', 'Sports Bet', 'Horse Bet', 'Lottery Lotter Purchase'])]

    daily_promo_totals = defaultdict(lambda: defaultdict(float))
    for date, sub_df in filtered_df.groupby(filtered_df['Create Date'].dt.date):
        promo_totals = defaultdict(float)
        for value in sub_df['real money change amount']:
            amount, currency = extract_amount_and_currency(value)
            if currency:
                promo_totals[currency] += amount
        daily_promo_totals[date.strftime('%Y-%m-%d')] = promo_totals

    print("------------------------------------------------------------------")
    print("Daily Promo Totals:")
    for date, totals in daily_promo_totals.items():
        print(f"Date: {date}")
        print_currency_totals(totals, converter, [])


def main():
    file_path = select_file()
    if file_path:
        df = pd.read_excel(file_path)
        df['Create Date'] = pd.to_datetime(df['Create Date'], errors='coerce')

        if 'Create Date' in df.columns:
            min_logs_date = df['Create Date'].min()
            max_logs_date = df['Create Date'].max()

            if all(col in df.columns for col in ['real money change amount', 'Description', 'UID', 'Create Date']):
                uids = df['UID'].unique()
                if len(uids) == 1:
                    uid_value = uids[0]
                    filtered_df = df[df['Description'].isin(['Original Bet', 'Original War', 'Third Party Bet', 'Trade Bet-Contest', 'Trade Bet-Contract', 'Trade Bet-Order', 'Sports Bet', 'Horse Bet', 'Lottery Lotter Purchase'])]

                    min_transaction_date = filtered_df['Create Date'].min()
                    max_transaction_date = filtered_df['Create Date'].max()

                    totals = defaultdict(float)
                    for value in filtered_df['real money change amount']:
                        amount, currency = extract_amount_and_currency(value)
                        if currency:
                            totals[currency] += amount

                    print("******************************************************************")
                    print(f"File successfully read: {file_path}")
                    print("******************************************************************")
                    print(Fore.GREEN + f"UID: {uid_value}")
                    print("------------------------------------------------------------------")
                    print(f"Time frame (Overall): {min_logs_date} - {max_logs_date}")
                    print(f"Time frame (Filtered): {min_transaction_date} - {max_transaction_date}")
                    print("------------------------------------------------------------------")

                    unrecognized_currencies = []

                    converter = initialize_currency_converter()
                    # Process Third Party Win
                    third_party_wins_df = df[df['Description'] == 'Third Party Win']
                    third_party_totals = defaultdict(float)
                    for value in third_party_wins_df['real money change amount']:
                        amount, currency = extract_amount_and_currency(value)
                        if currency:
                            third_party_totals[currency] += amount

                    print("Third Party Win:\n")
                    print_currency_totals(third_party_totals, converter, unrecognized_currencies)
                    print("Total Wagering:\n")
                    print_currency_totals(totals, converter, unrecognized_currencies)

                    while True:
                        choice = input("Manually calculate the timeframe, recalculate, or promotion (y/n/r/p)? ")

                        if choice.lower() in ['y', 'ㄗ']:
                            print("------------------------------------------------------------------")
                            start_time_input = input("Please enter start time (YYYY-MM-DD): ")
                            end_time_input = input("Please enter end time (YYYY-MM-DD): ")
                            try:
                                start_time = parse_datetime(start_time_input)
                                end_time = parse_datetime(end_time_input, is_end_time=True)
                                if start_time and end_time:
                                    filtered_df = df[(df['Create Date'] >= start_time) & (df['Create Date'] <= end_time) & df['Description'].isin(['Original Bet', 'Original War', 'Third Party Bet', 'Trade Bet-Contest', 'Trade Bet-Contract', 'Trade Bet-Order', 'Sports Bet', 'Horse Bet', 'Lottery Lotter Purchase'])]

                                    totals = defaultdict(float)
                                    for value in filtered_df['real money change amount']:
                                        amount, currency = extract_amount_and_currency(value)
                                        if currency:
                                            totals[currency] += amount

                                    # Process Third Party Win
                                    third_party_wins_df = df[(df['Create Date'] >= start_time) & (df['Create Date'] <= end_time) & (df['Description'] == 'Third Party Win')]
                                    third_party_totals = defaultdict(float)
                                    for value in third_party_wins_df['real money change amount']:
                                        amount, currency = extract_amount_and_currency(value)
                                        if currency:
                                            third_party_totals[currency] += amount

                                    unrecognized_currencies.clear()  # Clear unrecognized currencies list for each new calculation
                                    print("------------------------------------------------------------------")
                                    print("Third Party Win:\n")
                                    print_currency_totals(third_party_totals, converter, unrecognized_currencies)
                                    print("Total Wagering:\n")
                                    print_currency_totals(totals, converter, unrecognized_currencies)


                            except Exception as e:
                                print(f"Error parsing dates: {e}")
                        elif choice.lower() in ['n', 'ㄙ']:
                            print("Exiting...")
                            sys.exit()
                        elif choice.lower() in ['r', 'ㄐ']:
                            main()  # Restart the process
                            return
                        elif choice.lower() in ['p', 'ㄣ']:
                            original_create_date = df['Create Date'].copy()  # Save the original 'Create Date'
                            timezone = input("Please enter the desired timezone (default is UTC): ").strip()
                            handle_promo_functionality(df, converter, timezone)
                            df['Create Date'] = original_create_date  # Restore the original 'Create Date'
                        else:
                            print(Fore.RED + "Invalid choice, please enter y/n/r/p.")
                else:
                    print("Multiple UIDs found, expected only one UID.")
            else:
                print("Columns 'real money change amount', 'Description', 'UID', or 'Create Date' not found")
        else:
            print("Column 'Create Date' not found")
    else:
        print("No file selected")

if __name__ == "__main__":
    main()