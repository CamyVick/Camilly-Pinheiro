import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import random
import numpy as np


nomes = ['Maria','Pedro','Joao','Ana','Beatriz']
regioes = ['SP','RJ','MA','PA','MG']

dados = {
    'nome': [random.choice(nomes) for _ in range(10)],
    'regioes': [random.choice(regioes) for _ in range(10)],
    'idade': [random.randint(18,50) for _ in range(10)]
}
df = pd.DataFrame(dados)

# Dataset exemplo
sns.set_theme(style="whitegrid")
print(df.head())

# Histograma
sns.histplot(df["idade"], kde=True)
plt.title("Distribuição de Idades")
plt.show()

# Gráfico de barras por região
sns.barplot(x="regiao", y="idade", data=df, estimator="mean", errorbar=None)
plt.title("Média de Idade por Região")
plt.show()

# Gráfico de dispersão
sns.scatterplot(x="idade", y="idade" * 1.5 + np.random.randint(-10, 10, len(df)))
plt.title("Exemplo de Dispersão")
plt.show()
