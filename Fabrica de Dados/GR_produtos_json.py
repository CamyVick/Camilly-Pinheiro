import json
import random

def gerar_json(qtd_itens, nome_arquivo="produtos.json"):
    lista = []

    for i in range(1, qtd_itens + 1):
        item = {
            "nome": f"Produto {i}",
            "id": i,
            "id_produto": random.randint(1000, 9999),
            "estoque": random.randint(0, 150),
            "meta_estoque": random.randint(50, 250)
        }
        lista.append(item)

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(lista, f, indent=4, ensure_ascii=False)

    print(f"Arquivo '{nome_arquivo}' criado com {qtd_itens} itens!")


# ------------ EXECUTAR ------------
gerar_json(10, "C:/Users/camil/Documents/Camilly/Camilly-Pinheiro/Projetos/Produtos/Data/produtos.json")

