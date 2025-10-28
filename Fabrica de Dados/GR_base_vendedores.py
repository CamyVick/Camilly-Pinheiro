import pandas as pd
import numpy as np
import random
from faker import Faker

# Gerador de dados falsos
fake = Faker('pt_BR')

# Quantidade de linhas
n = 150  # pode mudar pra 100, 200 etc.

# Listas auxiliares
cidades = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Salvador", "Fortaleza", "Brasília", "Recife"]
ufs = ["SP", "RJ", "MG", "PR", "BA", "CE", "DF", "PE"]
categorias = ["Eletrônico", "Móveis", "Roupas", "Beleza", "Brinquedos", "Esporte", "Automotivo"]
canais = ["Loja", "Online", "Telefone", "WhatsApp", "APP"]
produtos = ["Notebook", "Sofá", "Camisa", "Perfume", "Bicicleta", "Boneca", "Capacete", "TV", "Relógio"]

# Função para gerar erros aleatórios
def bagunca_texto(texto):
    if random.random() < 0.1:
        return texto.lower()
    elif random.random() < 0.15:
        return texto.upper()
    elif random.random() < 0.05:
        return texto.replace("o", "0").replace("a", "@")
    elif random.random() < 0.05:
        return texto + " "
    return texto

# Criação dos dados com erros e inconsistências
dados = []
for i in range(n):
    vendedor = fake.name() if random.random() > 0.05 else None
    cpf = fake.cpf() if random.random() > 0.2 else fake.cpf().replace(".", "").replace("-", "")
    cidade = random.choice(cidades)
    uf = random.choice(ufs)
    produto = bagunca_texto(random.choice(produtos))
    categoria = bagunca_texto(random.choice(categorias))
    canal = bagunca_texto(random.choice(canais))
    cliente = fake.name() if random.random() > 0.1 else fake.first_name().upper()
    email = fake.email() if random.random() > 0.15 else fake.email().replace("@", "@@")
    telefone = fake.phone_number() if random.random() > 0.1 else str(random.randint(99999999, 9999999999))
    
    salario = random.choice([
        round(random.uniform(1500, 8000), 2),
        f"R${round(random.uniform(1500, 8000), 2)}"
    ])
    qtd_vendas = random.choice([random.randint(0, 50), None])
    valor_vendas = random.choice([
        round(random.uniform(100, 50000), 2),
        f"R${round(random.uniform(100, 50000), 2)}"
    ])
    meta = random.choice([
        round(random.uniform(20000, 80000), 2),
        f"R$ {round(random.uniform(20000, 80000), 2)}",
        None
    ])
    percentual = random.choice([
        f"{round(random.uniform(50, 120), 1)}%",
        round(random.uniform(0.5, 1.2), 2)
    ])
    data_venda = random.choice([
        fake.date_between(start_date='-3y', end_date='today'),
        fake.date(),
        fake.date_time_this_year().strftime("%d/%m/%Y")
    ])
    data_cadastro = random.choice([
        fake.date_between(start_date='-5y', end_date='today'),
        None,
        fake.date_time_this_decade().strftime("%Y-%m-%d")
    ])
    id_venda = random.choice([
        f"VENDA-{random.randint(1000, 9999)}",
        f"vnd{random.randint(1000, 9999)}",
        f"{random.randint(1000, 9999)}"
    ])

    dados.append({
        "ID_Venda": id_venda,
        "Data_Venda": data_venda,
        "Vendedor": vendedor,
        "CPF": cpf,
        "Cidade": cidade if random.random() > 0.1 else cidade.lower(),
        "UF": uf if random.random() > 0.2 else uf.lower(),
        "Produto": produto,
        "Categoria": categoria,
        "Canal_Venda": canal,
        "Qtd_Vendas": qtd_vendas,
        "Valor_Vendas": valor_vendas,
        "Salario": salario,
        "Meta_Mensal": meta,
        "Percentual_Cumprimento": percentual,
        "Cliente": cliente,
        "Email_Cliente": email,
        "Telefone": telefone,
        "Data_Cadastro": data_cadastro
    })

# Criação do DataFrame
df = pd.DataFrame(dados)

# Embaralhar linhas
df = df.sample(frac=1).reset_index(drop=True)

# Salvar o arquivo
caminho_arquivo = "C:/Users/camil/Documents/EngDados/Pyspark/Arquivos/base_vendedores.csv"
df.to_csv(caminho_arquivo, sep=";", index=False, encoding="utf-8")

print(f"Base gerada com sucesso! Linhas: {len(df)}")
print(f"Arquivo salvo como: {caminho_arquivo}")
