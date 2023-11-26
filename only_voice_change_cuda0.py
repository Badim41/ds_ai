import argparse
import gc
import os
import time
import traceback

cuda_number = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = cuda_number
import torch

from rvc import Config, load_hubert, get_vc, rvc_infer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')
from set_get_config import set_get_config_all_not_async


def voice_change0():
    rvc_index_path, hubert_model, cpt, version, net_g, tgt_sr, vc, voice_model = None, None, None, None, None, None, None, ""
    while True:
        try:
            new_voice_model = set_get_config_all_not_async(f"rvc{cuda_number}", "dir")

            # не выставлена модель
            if new_voice_model == "None":
                time.sleep(1)
                continue

            if not voice_model == new_voice_model:
                print("reload voice", new_voice_model)
                if hubert_model and cpt:
                    del hubert_model, cpt
                voice_model = new_voice_model
                rvc_model_path, rvc_index_path = get_rvc_model(voice_model)
                device = 'cuda:0'
                config2 = Config(device, True)
                hubert_model = load_hubert(device, config2.is_half, os.path.join(rvc_models_dir, 'hubert_base.pt'))
                cpt, version, net_g, tgt_sr, vc = get_vc(device, config2.is_half, config2, rvc_model_path)
            input_path = set_get_config_all_not_async(f"rvc{cuda_number}", "input")
            if not input_path == "None":
                print("run RVC temp2")
                set_get_config_all_not_async(f"rvc{cuda_number}", "input", "None")
                # получем значения
                index_rate = float(set_get_config_all_not_async(f"rvc{cuda_number}", "index_rate"))
                output_path = set_get_config_all_not_async(f"rvc{cuda_number}", "output")
                pitch_change = int(set_get_config_all_not_async(f"rvc{cuda_number}", "pitch_change"))
                filter_radius = int(set_get_config_all_not_async(f"rvc{cuda_number}", "filter_radius"))
                rms_mix_rate = float(set_get_config_all_not_async(f"rvc{cuda_number}", "rms_mix_rate"))
                protect = float(set_get_config_all_not_async(f"rvc{cuda_number}", "protect"))

                rvc_infer(rvc_index_path, index_rate, input_path, output_path, pitch_change, "rmvpe", cpt, version,
                          net_g,
                          filter_radius, tgt_sr, rms_mix_rate, protect, 128, vc, hubert_model)
                gc.collect()

                set_get_config_all_not_async(f"rvc{cuda_number}", "input", "None")
                set_get_config_all_not_async(f"rvc{cuda_number}", "result", output_path)
            else:
                time.sleep(0.5)
        except Exception as e:
            traceback_str = traceback.format_exc()
            raise f"Произошла ошибка (ID:vc1): {str(e)}\n{str(traceback_str)}"


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
        exit(1)

    return os.path.join(model_dir, rvc_model_filename), os.path.join(model_dir,
                                                                     rvc_index_filename) if rvc_index_filename else ''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a AI cover song in the song_output/id directory.',
                                     add_help=True)
    parser.add_argument('-i', '--input', type=str, required=True,
                        help='Link to a YouTube video or the filepath to a local mp3/wav file to create an AI cover of')
    parser.add_argument('-o', '--output', type=str, required=True,
                        help='Link to a YouTube video or the filepath to a local mp3/wav file to create an AI cover of')
    parser.add_argument('-dir', '--rvc-dirname', type=str, required=True,
                        help='Name of the folder in the rvc_models directory containing the RVC model file and optional index file to use')
    parser.add_argument('-p', '--pitch-change', type=int, required=True,
                        help='Change the pitch of AI Vocals only. Generally, use 1 for male to female and -1 for vice-versa. (Octaves)')
    parser.add_argument('-ir', '--index-rate', type=float, default=0.5,
                        help='A decimal number e.g. 0.5, used to reduce/resolve the timbre leakage problem. If set to 1, more biased towards the timbre quality of the training dataset')
    parser.add_argument('-fr', '--filter-radius', type=int, default=3,
                        help='A number between 0 and 7. If >=3: apply median filtering to the harvested pitch results. The value represents the filter radius and can reduce breathiness.')
    parser.add_argument('-rms', '--rms-mix-rate', type=float, default=0.25,
                        help="A decimal number e.g. 0.25. Control how much to use the original vocal's loudness (0) or a fixed loudness (1).")
    parser.add_argument('-pro', '--protect', type=float, default=0.33,
                        help='A decimal number e.g. 0.33. Protect voiceless consonants and breath sounds to prevent artifacts such as tearing in electronic music. Set to 0.5 to disable. Decrease the value to increase protection, but it may reduce indexing accuracy.')
    parser.add_argument('-slow', '--slow', action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    protect = float(args.protect)
    rms_mix_rate = float(args.rms_mix_rate)
    filter_radius = int(args.filter_radius)
    index_rate = float(args.index_rate)
    pitch_change = int(args.pitch_change)
    output = args.output
    rvc_dirname = args.rvc_dirname
    input = args.input

    if not os.path.exists(os.path.join(rvc_models_dir, rvc_dirname)):
        raise Exception(f'The folder {os.path.join(rvc_models_dir, rvc_dirname)} does not exist.')
    if not args.slow:
        set_get_config_all_not_async(f"rvc{cuda_number}", "protect", protect)
        set_get_config_all_not_async(f"rvc{cuda_number}", "rms_mix_rate", rms_mix_rate)
        set_get_config_all_not_async(f"rvc{cuda_number}", "filter_radius", filter_radius)
        set_get_config_all_not_async(f"rvc{cuda_number}", "index_rate", index_rate)
        set_get_config_all_not_async(f"rvc{cuda_number}", "pitch_change", pitch_change)
        set_get_config_all_not_async(f"rvc{cuda_number}", "output", output)
        set_get_config_all_not_async(f"rvc{cuda_number}", "dir", rvc_dirname)
        set_get_config_all_not_async(f"rvc{cuda_number}", "input", input)
        while True:
            if not set_get_config_all_not_async(f"rvc{cuda_number}", "result") == "None":
                set_get_config_all_not_async(f"rvc{cuda_number}", "result", "None")
                break
    else:
        try:
            rvc_model_path, rvc_index_path = get_rvc_model(rvc_dirname)
            device = 'cuda:0'
            config2 = Config(device, True)
            hubert_model = load_hubert(device, config2.is_half, os.path.join(rvc_models_dir, 'hubert_base.pt'))
            cpt, version, net_g, tgt_sr, vc = get_vc(device, config2.is_half, config2, rvc_model_path)
            # "rmvpe" "mangio-crepe"
            rvc_infer(rvc_index_path, index_rate, input, output, pitch_change, "rmvpe", cpt,
                      version,
                      net_g,
                      filter_radius, tgt_sr, rms_mix_rate, protect, 256, vc, hubert_model)
            del hubert_model, cpt
            gc.collect()
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(str(traceback_str))
