import pandas as pd
from sqlalchemy import create_engine
from pandasgui import show

usuario = 'root'
senha = '123456'
host = 'localhost'
porta = 3306
banco = 'Vendas'

engine = create_engine(f'mysql+pymysql://{usuario}:{senha}@{host}:{porta}/{banco}')

df_Antigo = pd.read_sql('select * from vendedores', con=engine)
df = pd.read_sql('select * from vendedores', con=engine)


def padronizar_datas(valor):
    if pd.isna(valor):
        return pd.NaT
    valor = str(valor).strip().replace('-', '/')
    partes = valor.split('/')
    
    if len(partes) != 3:
        return pd.NaT
    
    # Detecta se começa com ano (yyyy-mm-dd)
    if len(partes[0]) == 4:
        ano, mes, dia = partes
    else:
        dia, mes, ano = partes
        if len(ano) == 2:
            ano = '20' + ano  # corrige ano curto
    
    try:
        return pd.to_datetime(f'{ano}-{mes.zfill(2)}-{dia.zfill(2)}', errors='coerce')
    except:
        return pd.NaT





def limpar_id(v):
    if pd.isna(v):
        return None
    v = str(v).replace('VENDA-','').replace('vnd','')
    return "vnd_" + v

def telefone(n):
    if pd.isna(n):
        return None
    n = str(n).replace('+55 ','').replace('(0','').replace(')','').replace('-','').replace(' ','')
    return "+55 " + n.strip()
def nomes(nome):
    if pd.isna(nome):
        return None
    nome = str(nome).replace('Sr. ','').replace('Srta. ','').replace('Dr. ','').replace('Dra. ','').replace('Sra. ','')
    return nome.title().strip()
def valores(valor):
    if pd.isna(valor):
        return None
    valor = str(valor).replace('R$','').replace(',','.').replace(' ','')
    try:
        return float(valor)
    except:
        return None

def percentual(valor):
    if pd.isna(valor):
        return None
    valor = str(valor).replace('%','')
    return valor
def cpf(documento):
    if pd.isna(documento):
        return None
    documento = str(documento).replace('.','').replace('-','')
    return documento

df['ID_Venda'] = df['ID_Venda'].apply(limpar_id)
df['Data_Venda'] = df['Data_Venda'].apply(padronizar_datas)
df['Telefone'] = df['Telefone'].apply(telefone)
df['Vendedor'] = df['Vendedor'].apply(nomes)
df['Cidade'] = df['Cidade'].apply(nomes)
df['UF'] = df['UF'].str.upper()
df[['Produto','Canal_Venda','Categoria']] = df[['Produto','Canal_Venda','Categoria']].apply(lambda x: x.str.upper())
df['Qtd_Vendas'] = df['Qtd_Vendas'].convert_dtypes(int)
df[['Valor_Vendas','Salario','Meta_Mensal']] = df[['Valor_Vendas','Salario','Meta_Mensal']].applymap(valores)
df['Cliente'] = df['Cliente'].apply(nomes)
df['Percentual_Cumprimento'] = df['Percentual_Cumprimento'].apply(percentual)
df['CPF'] = df['CPF'].apply(cpf)

gui = show(df)
#gui = show(df_Antigo)

df.to_csv('C:/Users/camil/Documents/EngDados/Projetos/Vendas/Vendas_depois.csv', index=True, sep=';')
df_Antigo.to_csv('C:/Users/camil/Documents/EngDados/Projetos/Vendas/Vendas_antes.csv', index=True, sep=';')