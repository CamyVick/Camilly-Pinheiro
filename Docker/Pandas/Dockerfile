# Usar a imagem do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as bibliotecas
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os scripts Python
COPY main.py .


# Executa os dois scripts em sequência
CMD ["python", "main.py"]