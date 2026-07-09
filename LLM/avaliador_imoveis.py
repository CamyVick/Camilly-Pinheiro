import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

#Criando os  Dados
'''dados = {"tamanho":[50,70,90,120,150],
         "quartos":[1,2,3,3,4],
         "idade":[15,8,5,2,1],
         "preco":[180000,250000,340000,480000,650000]
         }'''
df = pd.read_csv("d:/Script/Camilly-Pinheiro/LLM/base_imoveis.csv",sep=",")
#print(df.head())

#Separando os dados em variáveis independentes (X) e variável dependente (y)

x = df[["tamanho","quartos","idade"]]
y = df["preco"]

#Separando os dados em conjunto de treino e teste
X_treino,X_teste,y_treino,y_teste = train_test_split(
    x,
    y,
    test_size=0.2,
    random_state=42
)
#Criando o modelo de regressão linear
modelo = LinearRegression()

#Treinando o modelo
modelo.fit(X_treino,y_treino)

previsoes = modelo.predict(X_teste)

#avaliando o modelo

erro = mean_squared_error(y_teste,previsoes)

resultado = X_teste.copy()

resultado["preco_real"] = y_teste.values
resultado["preco_previsto"] = previsoes
resultado["erro"] = resultado["preco_real"] - resultado["preco_previsto"]

print(resultado)