import asyncio
import random

# Пример функции, которая будет выполняться с рандомной задержкой
async def random_number():
    await asyncio.sleep(random.uniform(1, 5))
    return random.randint(1, 100)

async def run_all():
    numbers = [random_number() for _ in range(10)]  # Создайте список функций
    done, _ = await asyncio.wait(numbers, return_when=asyncio.FIRST_COMPLETED)
    for task in done:
        result = await task
        print(f"Первый результат: {result}")
        break

asyncio.run(run_all())
