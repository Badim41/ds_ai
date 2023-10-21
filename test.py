import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')

print("DIR-RVC-MODELS:", os.path.join(rvc_models_dir, 'hubert_base.pt'))
print("DIR-RVC-MODELS:", os.path.join(BASE_DIR, "rvc_models", 'hubert_base.pt'))