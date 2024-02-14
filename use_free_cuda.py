import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def cuda_lock():
    lock = asyncio.Lock()
    async with lock:
        yield lock

class Use_Cuda:
    def __init__(self):
        import torch
        gpu_count = torch.cuda.device_count()

        self.cuda_is_busy = []
        self.cuda_is_busy_images = []
        for _ in range(gpu_count):
            self.cuda_is_busy.append(False)
            self.cuda_is_busy_images.append(False)

    async def use_cuda(self, index=None):
        async with cuda_lock():
            if not index is None:
                if self.cuda_is_busy[index]:
                    raise "Cuda is using right now"
                else:
                    self.cuda_is_busy[index] = True
                return
            for _ in range(14400):
                for i in range(len(self.cuda_is_busy)):
                    if not self.cuda_is_busy[i]:
                        self.cuda_is_busy[i] = True
                        return i
                await asyncio.sleep(0.25)
            raise "No avaible cuda"

    async def stop_use_cuda(self, index):
        if not self.cuda_is_busy[index]:
            raise "Cuda is not using right now"
        else:
            self.cuda_is_busy[index] = False

    async def use_cuda_images(self, index=None):
        from discord_bot import image_generators
        async with cuda_lock():
            if not index is None:
                if self.cuda_is_busy_images[index]:
                    raise "Cuda is not using right now"
                else:
                    self.cuda_is_busy_images[index] = True
                    self.cuda_is_busy[index] = True
                return
            for i in range(240):
                for generator in image_generators:
                    number = int(generator.cuda_number)
                    if not self.cuda_is_busy_images[number]:
                        self.cuda_is_busy_images[number] = True
                        self.cuda_is_busy[number] = True
                        return number
                await asyncio.sleep(0.25)
            raise "No avaible cuda"

    async def stop_use_cuda_images(self, index):
        if not self.cuda_is_busy_images[index]:
            raise "Cuda is not using right now"
        else:
            self.cuda_is_busy_images[index] = False
            self.cuda_is_busy[index] = False

    async def check_cuda(self):
        found = 0
        for cuda in self.cuda_is_busy:
            if cuda:
                found += 1

        return found

    async def check_cuda_images(self):
        from discord_bot import image_generators
        found = 0
        for i, cuda in enumerate(self.cuda_is_busy):
            if cuda and i <= len(image_generators):
                found += 1

        return found
