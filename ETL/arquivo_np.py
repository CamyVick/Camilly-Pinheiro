import numpy as np

# Criando Array
arr = np.array([1, 2, 3, 4, 5])
print(arr)

# Operações Vetorizadas
print('Somar: ', arr + 10)
print('Media: ', np.mean(arr))
print('Desvio: ', np.std(arr))

#Matriz 2D
matriz = np.array([[1,2,3],[4,5,6]])
print('\nMatriz',matriz)
print('\nTranspostas',matriz.T)