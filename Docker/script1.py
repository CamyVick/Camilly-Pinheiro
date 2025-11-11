import requests

print("=== Script 1 ===")
response = requests.get('https://api.github.com')
print(f"Status da API do GitHub: {response.status_code}")