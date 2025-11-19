import requests
import pandas as pd

url = 'https://pokeapi.co/api/v2/pokemon/ditto'
response = requests.get(url).json()

# ---------------------------
# Tabela principal (dados simples)
# ---------------------------
tabela_principal = pd.DataFrame([{
    "id": response["id"],
    "name": response["name"],
    "height": response["height"],
    "weight": response["weight"],
    "base_experience": response["base_experience"]
}])

print("TABELA PRINCIPAL:")
print(tabela_principal, "\n")


# ---------------------------
# Tabela de habilidades
# ---------------------------
tabela_abilities = pd.json_normalize(
    response["abilities"],
    sep="_"
)

print("TABELA DE ABILIDADES:")
print(tabela_abilities, "\n")


# ---------------------------
# Tabela de stats
# ---------------------------
tabela_stats = pd.json_normalize(response["stats"], sep="_")
print("TABELA DE STATS:")
print(tabela_stats, "\n")


# ---------------------------
# Tabela de tipos
# ---------------------------
tabela_tipos = pd.json_normalize(response["types"], sep="_")
print("TABELA DE TIPOS:")
print(tabela_tipos, "\n")
