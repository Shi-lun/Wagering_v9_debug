import tkinter as tk
from tkinter import filedialog
import pandas as pd
import re
from collections import defaultdict
import requests

def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    return file_path

def extract_amount_and_currency(value):
    match = re.match(r"([-+]?\d*\.?\d+)\s*(\w+)", str(value))
    if match:
        amount = abs(float(match.group(1)))
        currency = match.group(2)
        return amount, currency
    return 0, ""

def get_price(symbol):
    if symbol == 'BCD':
        return 1
    elif symbol == 'JB':
        return 0

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    parameters = {
        "symbol": symbol.upper()  # Ensure symbol is uppercase
    }
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": "3e5a1c85-1d9c-4a4a-b955-e1d2e827be32"  # Replace 'Your_API_Key' with your actual API key
    }

    response = requests.get(url, params=parameters, headers=headers)
    data = response.json()

    if response.status_code == 200 and data['status']['error_code'] == 0:
        symbol_upper = symbol.upper()
        if symbol_upper in data['data']:
            btc_price = data['data'][symbol_upper]['quote']['USD']['price']
            return btc_price
    return None

def main():
    file_path = select_file()
    if file_path:
        df = pd.read_excel(file_path)
        if 'Create Date' in df.columns:
            min_logs_date = df['Create Date'].min()  # Get the first log date
            max_logs_date = df['Create Date'].max()  # Get the last log date

            if 'real money change amount' in df.columns and 'Description' in df.columns and 'UID' in df.columns and 'Create Date' in df.columns:
                uids = df['UID'].unique()  # Get unique UID values
                if len(uids) == 1:  # Check if there is only one UID value
                    uid_value = uids[0]  # Get the unique UID value
                    filtered_df = df[df['Description'].isin(['Original Bet', 'Original War', 'Third Party Bet'])]

                    # Get the first and last transaction dates of filtered data
                    min_transaction_date = filtered_df['Create Date'].min()
                    max_transaction_date = filtered_df['Create Date'].max()

                    totals = defaultdict(float)
                    for value in filtered_df['real money change amount']:
                        amount, currency = extract_amount_and_currency(value)
                        if currency:
                            totals[currency] += amount

                    print(f"File successfully read: {file_path}")
                    print()  # Add two empty lines after printing the success message
                    print("-------------------------------------------------")
                    print(f"UID: {uid_value}")  # Add UID value after two empty lines
                    print("-------------------------------------------------")
                    print(f"Time frame (Overall): {min_logs_date} - {max_logs_date}")  # Add Logs Time frame
                    print(f"Time frame (Filtered): {min_transaction_date} - {max_transaction_date}")  # Update Time frame format
                    print("-------------------------------------------------")

                    total_usd_sum = 0
                    unrecognized_currencies = []

                    for currency, total in totals.items():
                        price = get_price(currency)
                        if price is not None:
                            total_usd = total * price
                            total_usd_sum += total_usd
                            print(f"Total for {currency}: {total_usd:.2f} USD")
                        else:
                            unrecognized_currencies.append((currency, total))
                            print(f"Total for {currency}: {total} {currency}")

                    print("-------------------------------------------------")
                    print(f"Total USD value: {total_usd_sum:.2f} USD")
                    
                    if unrecognized_currencies:
                        print("Unrecognized currencies:")
                        for currency, total in unrecognized_currencies:
                            print(f"{total} {currency}")
                    print("-------------------------------------------------")  # Add one empty line at the end

            else:
                print("Columns 'real money change amount', 'Description', 'UID', or 'Create Date' not found")
        else:
            print("Column 'Create Date' not found")
    else:
        print("No file selected")

if __name__ == "__main__":
    main()
