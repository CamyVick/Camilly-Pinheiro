import pandas as pd
from sqlalchemy import create_engine
import logging

logging.basicConfig(level=logging.INFO,filename="log",format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s")



# 1️⃣ Caminho do CSV
caminho_csv = "C:/Users/camil/Documents/EngDados/Pyspark/Arquivos/base_vendedores.csv"
logging.info(f'O caminho localizado foi: {caminho_csv}')

# 2️⃣ Conexão com o MySQL
usuario = "root"
senha = "123456"
host = "localhost"
porta = 3306
banco = "vendas"

# Cria a conexão (usando PyMySQL)
engine = create_engine(f"mysql+pymysql://{usuario}:{senha}@{host}:{porta}/{banco}")
logging.info('Conexao estabelecida')

df = pd.read_csv(caminho_csv, sep=';')
logging.info('Arquivo lido e separado')
print(df.head())

tabela = 'Vendedores'

df.to_sql(tabela,con=engine, if_exists='append',index=False)
logging.info(f'Dados inseridos com sucesso na tabela {tabela}')
