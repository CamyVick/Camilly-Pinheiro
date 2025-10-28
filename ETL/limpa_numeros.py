import pandas as pd
import re
from word2number import w2n
from googletrans import Translator
#<<<<<<< staging
import logging

logging.basicConfig(level=logging.INFO,filename="log",format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s")

# cria o tradutor uma vez só
translator = Translator()
 
#=======

# cria o tradutor uma vez só
translator = Translator()

#>>>>>>> master
df = pd.DataFrame(
    {
        "Valor1":["2.000","1.500","3.250"],
        "Valor2":["R$ 2.000","R$ 1.500","R$ 3.250"],
        "Valor3":["2k","1.5k","3.25k"],
        "Valor4":["dois mil","mil e quinhentos","três mil duzentos e cinquenta"]
    }
)

#<<<<<<< staging
logging.info(f'Os valores foram inseridos')

#=======
#>>>>>>> master
def normalizar_numeros(v):
    if pd.isna(v):
        return None
    v = str(v).strip().lower()

    # Remove símbolos de moedas
    v = v.replace('r$', '').replace('reais', '').strip()

    # Substitui pontos de milhar e vírgulas
    v = v.replace('.', '').replace(',', '.')

    # Trata sufixos K e M
    if v.endswith('k'):
        return float(v.replace('k', '')) * 1000
    if v.endswith('m'):
        return float(v.replace('m', '')) * 1000000

    # Traduz e tenta converter por extenso
    try:
        traducao = translator.translate(v, src='pt', dest='en').text
        return w2n.word_to_num(traducao)
    except:
        pass

    # Tenta converter direto
    try:
        return float(v)
    except:
        return None


for col in df.columns:
    df[col + '_num'] = df[col].apply(normalizar_numeros)

pd.set_option('display.max_columns', None)
print(df)
