input_string = "asdasfd2324sds"

# Используем метод isdigit() для фильтрации только цифровых символов
digits = int(''.join(filter(str.isdigit, input_string)))

print(digits)
