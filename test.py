import torch

def get_available_gpus():
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        available_gpus = [torch.cuda.get_device_name(i) for i in range(gpu_count)]
        return available_gpus
    else:
        return []

available_gpus = get_available_gpus()
if available_gpus:
    print("Доступные GPU:")
    for gpu in available_gpus:
        print(gpu)
else:
    print("GPU не найдены.")