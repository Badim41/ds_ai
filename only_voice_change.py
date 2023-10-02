import argparse
import gc
import os

from src.rvc import Config, load_hubert, get_vc, rvc_infer
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')

def voice_change(voice_model, vocals_path, output_path, pitch_change, f0_method, index_rate, filter_radius,
                 rms_mix_rate, protect, crepe_hop_length):
    rvc_model_path, rvc_index_path = get_rvc_model(voice_model)
    # os.environ["CUDA_VISIBLE_DEVICES"] = str(cuda_number)
    print("voice_change")
    device = 'cuda:0'
    config2 = Config(device, True)
    hubert_model = load_hubert(device, config2.is_half, os.path.join(rvc_models_dir, 'hubert_base.pt'))
    cpt, version, net_g, tgt_sr, vc = get_vc(device, config2.is_half, config2, rvc_model_path)

    # convert main vocals
    rvc_infer(rvc_index_path, index_rate, vocals_path, output_path, pitch_change, f0_method, cpt, version, net_g,
              filter_radius, tgt_sr, rms_mix_rate, protect, crepe_hop_length, vc, hubert_model)
    del hubert_model, cpt
    gc.collect()

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

......................................................................if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a AI cover song in the song_output/id directory.',
                                     add_help=True)
    parser.add_argument('-i', '--song-input', type=str, required=True,
                        help='Link to a YouTube video or the filepath to a local mp3/wav file to create an AI cover of')
    parser.add_argument('-dir', '--rvc-dirname', type=str, required=True,
                        help='Name of the folder in the rvc_models directory containing the RVC model file and optional index file to use')
    parser.add_argument('-p', '--pitch-change', type=int, required=True,
                        help='Change the pitch of AI Vocals only. Generally, use 1 for male to female and -1 for vice-versa. (Octaves)')
    parser.add_argument('-k', '--keep-files', action=argparse.BooleanOptionalAction,
                        help='Whether to keep all intermediate audio files generated in the song_output/id directory, e.g. Isolated Vocals/Instrumentals')
    parser.add_argument('-ir', '--index-rate', type=float, default=0.5,
                        help='A decimal number e.g. 0.5, used to reduce/resolve the timbre leakage problem. If set to 1, more biased towards the timbre quality of the training dataset')
    parser.add_argument('-fr', '--filter-radius', type=int, default=3,
                        help='A number between 0 and 7. If >=3: apply median filtering to the harvested pitch results. The value represents the filter radius and can reduce breathiness.')
    parser.add_argument('-rms', '--rms-mix-rate', type=float, default=0.25,
                        help="A decimal number e.g. 0.25. Control how much to use the original vocal's loudness (0) or a fixed loudness (1).")
    parser.add_argument('-palgo', '--pitch-detection-algo', type=str, default='rmvpe',
                        help='Best option is rmvpe (clarity in vocals), then mangio-crepe (smoother vocals).')
    parser.add_argument('-hop', '--crepe-hop-length', type=int, default=128,
                        help='If pitch detection algo is mangio-crepe, controls how often it checks for pitch changes in milliseconds. The higher the value, the faster the conversion and less risk of voice cracks, but there is less pitch accuracy. Recommended: 128.')
    parser.add_argument('-pro', '--protect', type=float, default=0.33,
                        help='A decimal number e.g. 0.33. Protect voiceless consonants and breath sounds to prevent artifacts such as tearing in electronic music. Set to 0.5 to disable. Decrease the value to increase protection, but it may reduce indexing accuracy.')
    parser.add_argument('-mv', '--main-vol', type=int, default=0,
                        help='Volume change for AI main vocals in decibels. Use -3 to decrease by 3 decibels and 3 to increase by 3 decibels')
    parser.add_argument('-bv', '--backup-vol', type=int, default=0, help='Volume change for backup vocals in decibels')
    parser.add_argument('-iv', '--inst-vol', type=int, default=0, help='Volume change for instrumentals in decibels')
    parser.add_argument('-pall', '--pitch-change-all', type=int, default=0,
                        help='Change the pitch/key of vocals and instrumentals. Changing this slightly reduces sound quality')
    parser.add_argument('-rsize', '--reverb-size', type=float, default=0.15, help='Reverb room size between 0 and 1')
    parser.add_argument('-rwet', '--reverb-wetness', type=float, default=0.2, help='Reverb wet level between 0 and 1')
    parser.add_argument('-rdry', '--reverb-dryness', type=float, default=0.8, help='Reverb dry level between 0 and 1')
    parser.add_argument('-rdamp', '--reverb-damping', type=float, default=0.7, help='Reverb damping between 0 and 1')
    parser.add_argument('-oformat', '--output-format', type=str, default='mp3',
                        help='Output format of audio file. mp3 for smaller file size, wav for best quality')
    parser.add_argument('-cuda', '--cuda-number', type=str, default='0',
                        help='GPU index')
    args = parser.parse_args()