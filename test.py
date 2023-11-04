import xml.etree.ElementTree as ET
import random
import xml.dom.minidom


# Укажите путь к вашему XML-файлу
xml_file = "C:/Users/as280/Pictures/китайский майн/CraftingRecipesOld.xml"

# Разбор исходного XML-документа из файла
tree = ET.parse(xml_file)
root = tree.getroot()

# Итерация по всем группам
for group in root:
    # Создаем список для хранения значений Result в данной группе
    result_values = []

    # Итерация по элементам внутри группы
    for recipe in group:
        result = recipe.get("Result")
        result_values.append(result)

    # Перемешиваем значения в Result
    random.shuffle(result_values)

    # Присваиваем перемешанные значения обратно элементам внутри группы
    for i, recipe in enumerate(group):
        recipe.set("Result", result_values[i])

# Вывод измененных XML-данных
new_xml_data = ET.tostring(root, encoding="unicode")

# Запись в файл
with open("C:/Users/as280/Pictures/китайский майн/CraftingRecipes.xml", "w") as file:
    file.write(new_xml_data)