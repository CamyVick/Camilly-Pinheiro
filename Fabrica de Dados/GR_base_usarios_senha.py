from faker import Faker
import pandas as pd
import random

fake = Faker("pt_BR")

quantidade = 100

dados = []

for i in range(1, quantidade + 1):
    dados.append({
        "id": i,
        "nome": fake.name(),
        "email": fake.unique.email(),
        "senha": fake.password(length=12),
        "telefone": fake.cellphone_number(),
        "ativo": random.choice([True, False]),
        "criado_em": fake.date_time_between(
            start_date="-2y",
            end_date="now"
        )
    })

df = pd.DataFrame(dados)

df.to_csv(
    "tb_cliente.csv",
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

print("CSV criado com sucesso!")