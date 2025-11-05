import pandas as pd
from sqlalchemy import create_engine

usuario = 'root'
senha = '123456'
host = 'localhost'
porta = 3306
banco = 'Vendas'

engine = create_engine(f'mysql+pymysql://{usuario}:{senha}@{host}:{porta}/{banco}')

df = pd.read_sql('select * from vendedores', con=engine)
def padronizar_datas(serie):
    """
    Recebe uma lista ou Series com datas em formatos mistos (dd/mm/aaaa ou aaaa-mm-dd)
    e retorna todas padronizadas no formato aaaa-mm-dd (datetime64[ns]).
    Ignora valores inválidos.
    """
    # Converte para string (caso tenha números, None, etc.)
    serie = serie.astype(str)

    # Primeira tentativa: formato brasileiro (dia primeiro)
    datas = pd.to_datetime(serie, dayfirst=True, errors='coerce')

    # Segunda tentativa: formato ISO (ano primeiro), onde a primeira falhou
    mascaras_nulas = datas.isna()
    if mascaras_nulas.any():
        datas.loc[mascaras_nulas] = pd.to_datetime(
            serie[mascaras_nulas], dayfirst=False, errors='coerce'
        )

    return datas.dt.strftime('%Y-%m-%d')  # Retorna tudo padronizado como string


def limpar_id(v):
    if pd.isna(v):
        return None
    v = str(v).replace('VENDA-','')
    v = str(v).replace('vnd','')
    return "vnd_" + v

df['ID_Venda'] = df['ID_Venda'].apply(limpar_id)


df['Data_Venda'] = padronizar_datas(df['Data_Venda'])


print(df)