import requests

def get_price(symbol):
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

    if response.status_code == 200:
        if data['status']['error_code'] == 0:
            btc_price = data['data'][symbol.upper()]['quote']['USD']['price']
            return btc_price
        else:
            print("Error:", data['status']['error_message'])
    else:
        print("Error:", response.status_code)

# Example usage
btc_price = get_price("BTC")
print("BTC Price:", btc_price)
