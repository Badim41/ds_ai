import numpy as np

# Пример векторов
vector_a = np.array([-2, -5, -1])
vector_b = np.array([4, 5, 6])

# Вычисление косинусного сходства
cosine_similarity = np.dot(vector_a, vector_b) / (np.linalg.norm(vector_a) * np.linalg.norm(vector_b))

print(f"Косинусное сходство: {cosine_similarity}")