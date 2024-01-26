from pathlib import Path
import requests

MDX_DOWNLOAD_LINK = 'https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/'
RVC_DOWNLOAD_LINK = 'https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/'
MDX_NEW_DOWNLOAD_LINK = 'https://huggingface.co/seanghay/uvr_models/resolve/main/'

BASE_DIR = Path(__file__).resolve().parent
mdxnet_models_dir = BASE_DIR / 'mdxnet_models'
rvc_models_dir = BASE_DIR / 'rvc_models'


def dl_model(link, model_name, dir_name):
    with requests.get(f'{link}{model_name}') as r:
        r.raise_for_status()
        with open(dir_name / model_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


if __name__ == '__main__':
    mdx_model_names = ['UVR_MDXNET_KARA_2.onnx', 'Reverb_HQ_By_FoxJoy.onnx'] #'UVR-MDX-NET-Voc_FT.onnx',
    for model in mdx_model_names:
        print(f'Downloading {model}...')
        dl_model(MDX_DOWNLOAD_LINK, model, mdxnet_models_dir)

    new_models = ["Kim_Vocal_2.onnx", "UVR-MDX-NET-Inst_HQ_1.onnx"] # ,
    for model in new_models:
        print(f'Downloading {model}...')
        dl_model(MDX_DOWNLOAD_LINK, model, mdxnet_models_dir)

    rvc_model_names = ['hubert_base.pt', 'rmvpe.pt']
    for model in rvc_model_names:
        print(f'Downloading {model}...')
        dl_model(RVC_DOWNLOAD_LINK, model, rvc_models_dir)

    print('All models downloaded!')
