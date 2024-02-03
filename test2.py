import asyncio

from use_free_cuda import Use_Cuda
cuda_manager = Use_Cuda()

async def test_use_cuda(cuda_number):
    await asyncio.sleep(cuda_number)
    cuda = await cuda_manager.use_cuda()
    print("use", cuda)
    await asyncio.sleep(10)
    await cuda_manager.stop_use_cuda(cuda)
    print("stop", cuda)
async def stuck_cuda():
    functions = [test_use_cuda(cuda%2) for cuda in range(2)]
    await asyncio.gather(*functions)

asyncio.run(stuck_cuda())