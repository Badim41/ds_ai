import gc
import os

from rvc import Config, load_hubert, get_vc, rvc_infer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')


def get_rvc_model(voice_model):
    rvc_model_filename, rvc_index_filename = None, None
    model_dir = os.path.join(rvc_models_dir, voice_model)
    for file in os.listdir(model_dir):
        ext = os.path.splitext(file)[1]
        if ext == '.pth':
            rvc_model_filename = file
        if ext == '.index':
            rvc_index_filename = file

    if rvc_model_filename is None:
        print(f'No model file exists in {model_dir}.')

    return os.path.join(model_dir, rvc_model_filename), os.path.join(model_dir,
                                                                     rvc_index_filename) if rvc_index_filename else ''


class Voice_Changer:
    def __init__(self, cuda_number:int, voice_model:str, index_rate=0.5, pitch=0, filter_radius=3, rms_mix_rate=0.3, protect=0.33, algo="rmvpe"):
        cuda_number = str(cuda_number)
        os.environ["CUDA_VISIBLE_DEVICES"] = cuda_number
        import torch
        self.torch = torch
        self.voice_model = voice_model
        self.rvc_model_path, self.rvc_index_path = get_rvc_model(voice_model)
        device = 'cuda:0'
        config2 = Config(device, True)
        self.hubert_model = load_hubert(device, config2.is_half, os.path.join(rvc_models_dir, 'hubert_base.pt'))
        self.cpt, self.version, self.net_g, self.tgt_sr, self.vc = get_vc(device, config2.is_half, config2, voice_model)
        self.index_rate = index_rate
        self.pitch = pitch
        self.filter_radius = filter_radius
        self.rms_mix_rate = rms_mix_rate
        self.protect = protect
        if algo.lower() not in ["mangio-crepe", "rmvpe"]:
            raise "Not found algo"
        self.algo = algo

    async def voice_change(self, input_path: str, output_path: str, pitch_change=0):
        rvc_infer(self.rvc_index_path, self.index_rate, input_path, output_path, self.pitch + pitch_change, self.algo, self.cpt,
                  self.version,
                  self.net_g,
                  self.filter_radius, self.tgt_sr, self.rms_mix_rate, self.protect, 128, self.vc, self.hubert_model)
        gc.collect()
        return output_path
