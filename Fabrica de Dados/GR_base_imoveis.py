import pandas as pd
import numpy as np

np.random.seed(42)

dados = []

for _ in range(100000):

    tamanho = np.random.randint(40, 300)          # m²
    quartos = np.random.randint(1, 6)
    banheiros = np.random.randint(1, 5)
    garagem = np.random.randint(0, 4)
    idade = np.random.randint(0, 40)
    piscina = np.random.choice([0,1], p=[0.8,0.2])

    bairro = np.random.choice(
        ["Popular","Médio","Nobre"],
        p=[0.4,0.4,0.2]
    )

    fator_bairro = {
        "Popular":1.0,
        "Médio":1.3,
        "Nobre":1.8
    }[bairro]

    preco = (
        tamanho * 4500 +
        quartos * 25000 +
        banheiros * 18000 +
        garagem * 12000 +
        piscina * 80000 -
        idade * 2500
    )

    preco *= fator_bairro

    # Ruído de ±20 mil
    preco += np.random.normal(0, 20000)

    dados.append([
        tamanho,
        quartos,
        banheiros,
        garagem,
        idade,
        piscina,
        bairro,
        round(preco)
    ])

df = pd.DataFrame(
    dados,
    columns=[
        "tamanho",
        "quartos",
        "banheiros",
        "garagem",
        "idade",
        "piscina",
        "bairro",
        "preco"
    ]
)

#print(df.head())

write_path = "Camilly-Pinheiro/Fabrica de Dados/base_imoveis.csv"
df.to_csv(write_path, index=False)