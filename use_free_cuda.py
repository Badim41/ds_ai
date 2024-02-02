import asyncio
import time


class Use_Cuda:
    def __init__(self):
        import torch
        gpu_count = torch.cuda.device_count()

        self.cuda_is_busy = []
        self.cuda_is_busy_images = []
        for _ in gpu_count:
            self.cuda_is_busy.append(False)
            self.cuda_is_busy_images.append(False)

    async def use_cuda(self, index=None):
        if not index is None:
            if self.cuda_is_busy[index]:
                raise "Cuda is not using right now"
            else:
                self.cuda_is_busy[index] = True
            return
        while True:
            for i in range(len(self.cuda_is_busy)):
                if not self.cuda_is_busy[i]:
                    return i
            await asyncio.sleep(0.25)

    async def stop_use_cuda(self, index):
        if not self.cuda_is_busy[index]:
            raise "Cuda is not using right now"
        else:
            self.cuda_is_busy[index] = False

    async def use_cuda_images(self, index=None):
        if not index is None:
            if self.cuda_is_busy_images[index]:
                raise "Cuda is not using right now"
            else:
                self.cuda_is_busy_images[index] = True
            return
        while True:
            for i in range(len(self.cuda_is_busy_images)):
                if not self.cuda_is_busy_images[i]:
                    return i
            await asyncio.sleep(0.25)

    async def stop_use_cuda_images(self, index):
        if not self.cuda_is_busy_images[index]:
            raise "Cuda is not using right now"
        else:
            self.cuda_is_busy_images[index] = False


    async def check_cuda(self):
        found = 0
        for cuda in self.cuda_is_busy:
            if cuda:
                found += 1

        return found
