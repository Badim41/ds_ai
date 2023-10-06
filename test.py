import asyncio
import threading


# Функция для запуска асинхронных функций в потоке
def run_async_function(ctx):
    from recognizer import record
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(record(ctx))


    thread = threading.Thread(target=run_async_function, args=(ctx,))
    thread.start()
    thread.join()
