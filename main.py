import multiprocessing
import os
import argparse
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
import torch
import gc
import hashlib
import json
import shlex
import subprocess
from contextlib import suppress
from urllib.parse import urlparse, parse_qs
from IPython.display import FileLink
import zipfile
import shutil

import librosa
import numpy as np
import soundfile as sf
import sox
import yt_dlp
from pedalboard import Pedalboard, Reverb, Compressor, HighpassFilter
from pedalboard.io import AudioFile
from pydub import AudioSegment
import configparser

config = configparser.ConfigParser()

from rvc import Config, load_hubert, get_vc, rvc_infer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

mdxnet_models_dir = os.path.join(BASE_DIR, 'mdxnet_models')
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')
output_dir = os.path.join(BASE_DIR, 'song_output')


def get_youtube_video_id(url, ignore_playlist=True):
    """
    Examples:
    http://youtu.be/SA2iWivDJiE
    http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    http://www.youtube.com/embed/SA2iWivDJiE
    http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    """
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        if query.path[1:] == 'watch':
            return query.query[2:]
        return query.path[1:]

    if query.hostname in {'www.youtube.com', 'youtube.com', 'music.youtube.com'}:
        if not ignore_playlist:
            # use case: get playlist id not current video in playlist
            with suppress(KeyError):
                return parse_qs(query.query)['list'][0]
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/watch/':
            return query.path.split('/')[1]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]

    # returns None for invalid YouTube url
    return None


def yt_download(link):
    import datetime
    current_datetime = datetime.datetime.now()
    current_time = current_datetime.time()
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': '%(title)s',
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'quiet': True,
        'extractaudio': True,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(link, download=True)
        download_path = ydl.prepare_filename(result, outtmpl='%(title)s.mp3')

    current_datetime = datetime.datetime.now()
    current_time = current_datetime.time()
    return download_path


def get_rvc_model(voice_model, is_webui):
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


def get_audio_paths(song_dir):
    orig_song_path = None
    instrumentals_path = None
    main_vocals_dereverb_path = None
    backup_vocals_path = None

    for file in os.listdir(song_dir):
        if file.endswith('_Instrumental.wav'):
            instrumentals_path = os.path.join(song_dir, file)
            orig_song_path = instrumentals_path.replace('_Instrumental', '')

        elif file.endswith('_Vocals_Main_DeReverb.wav'):
            main_vocals_dereverb_path = os.path.join(song_dir, file)

        elif file.endswith('_Vocals_Backup.wav'):
            backup_vocals_path = os.path.join(song_dir, file)

    return orig_song_path, instrumentals_path, main_vocals_dereverb_path, backup_vocals_path


def convert_to_stereo(audio_path):
    wave, sr = librosa.load(audio_path, mono=False, sr=44100)

    # check if mono
    if type(wave[0]) != np.ndarray:
        stereo_path = f'{os.path.splitext(audio_path)[0]}_stereo.wav'
        command = shlex.split(f'ffmpeg -y -loglevel error -i "{audio_path}" -ac 2 -f wav "{stereo_path}"')
        subprocess.run(command)
        return stereo_path
    else:
        return audio_path


def pitch_shift(audio_path, pitch_change):
    output_path = f'{os.path.splitext(audio_path)[0]}_p{pitch_change}.wav'
    if not os.path.exists(output_path):
        y, sr = sf.read(audio_path)
        tfm = sox.Transformer()
        tfm.pitch(pitch_change)
        y_shifted = tfm.build_array(input_array=y, sample_rate_in=sr)
        sf.write(output_path, y_shifted, sr)

    return output_path


def get_hash(filepath):
    with open(filepath, 'rb') as f:
        file_hash = hashlib.blake2b()
        while chunk := f.read(8192):
            file_hash.update(chunk)

    return file_hash.hexdigest()[:11]


def display_progress(message):
    print(message)


def preprocess_song(cuda_number, song_input, mdx_model_params, song_id, input_type=None):
    try:
        if cuda_number == 0:
            from mdx_cuda0 import run_mdx
        else:
            from mdx_cuda1 import run_mdx

        keep_orig = False
        if input_type == 'yt':
            display_progress('[~] Downloading song...')
            song_link = song_input.split('&')[0]
            orig_song_path = yt_download(song_link)
            print("downloaded")
        elif input_type == 'local':
            orig_song_path = song_input
            # keep_orig = True
        else:
            orig_song_path = None
        song_output_dir = os.path.join(output_dir, song_id)
        orig_song_path = convert_to_stereo(orig_song_path)
        display_progress('[~] Separating Vocals from Instrumental...')
        vocals_path, instrumentals_path = run_mdx(mdx_model_params, song_output_dir,
                                                  os.path.join(mdxnet_models_dir, 'UVR-MDX-NET-Voc_FT.onnx'),
                                                  orig_song_path, denoise=True, keep_orig=keep_orig)
        display_progress('[~] Separating Main Vocals from Backup Vocals...')
        backup_vocals_path, main_vocals_path = run_mdx(mdx_model_params, song_output_dir,
                                                       os.path.join(mdxnet_models_dir, 'UVR_MDXNET_KARA_2.onnx'),
                                                       vocals_path, suffix='Backup', invert_suffix='Main', denoise=True)
        display_progress('[~] Applying DeReverb to Vocals...')
        _, main_vocals_dereverb_path = run_mdx(mdx_model_params, song_output_dir,
                                               os.path.join(mdxnet_models_dir, 'Reverb_HQ_By_FoxJoy.onnx'),
                                               main_vocals_path, invert_suffix='DeReverb', exclude_main=True,
                                               denoise=True)
        return orig_song_path, vocals_path, instrumentals_path, main_vocals_path, backup_vocals_path, main_vocals_dereverb_path
    except Exception as e:
        raise e


def download_video_or_use_file(song_input, input_type):
    keep_orig = False
    if input_type == 'yt':
        display_progress('[~] Downloading song...')
        song_link = song_input.split('&')[0]
        print(song_link)
        orig_song_path = yt_download(song_link)
    elif input_type == 'local':
        orig_song_path = song_input
        # keep_orig = True
    else:
        orig_song_path = None
    return orig_song_path, keep_orig


def voice_change(cuda_number, voice_model, vocals_path, output_path, pitch_change, f0_method, index_rate, filter_radius,
                 rms_mix_rate, protect, crepe_hop_length, is_webui):
    rvc_model_path, rvc_index_path = get_rvc_model(voice_model, is_webui)
    # os.environ["CUDA_VISIBLE_DEVICES"] = str(cuda_number)
    print("voice_change")
    device = 'cuda:0'
    config2 = Config(device, True)
    print("DIR-RVC-MODELS:", os.path.join(rvc_models_dir, 'hubert_base.pt'))
    hubert_model = load_hubert(device, config2.is_half, os.path.join(rvc_models_dir, 'hubert_base.pt'))
    cpt, version, net_g, tgt_sr, vc = get_vc(device, config2.is_half, config2, rvc_model_path)

    # convert main vocals
    rvc_infer(rvc_index_path, index_rate, vocals_path, output_path, pitch_change, f0_method, cpt, version, net_g,
              filter_radius, tgt_sr, rms_mix_rate, protect, crepe_hop_length, vc, hubert_model)
    del hubert_model, cpt
    gc.collect()


def add_audio_effects(audio_path, reverb_rm_size, reverb_wet, reverb_dry, reverb_damping):
    output_path = f'{os.path.splitext(audio_path)[0]}_mixed.wav'

    # Initialize audio effects plugins
    board = Pedalboard(
        [
            HighpassFilter(),
            Compressor(ratio=4, threshold_db=-15),
            Reverb(room_size=reverb_rm_size, dry_level=reverb_dry, wet_level=reverb_wet, damping=reverb_damping)
        ]
    )

    with AudioFile(audio_path) as f:
        with AudioFile(output_path, 'w', f.samplerate, f.num_channels) as o:
            # Read one second of audio at a time, until the file is empty:
            while f.tell() < f.frames:
                chunk = f.read(int(f.samplerate))
                effected = board(chunk, f.samplerate, reset=False)
                o.write(effected)

    return output_path


def combine_audio(audio_paths, output_path, main_gain, backup_gain, inst_gain, output_format):
    main_vocal_audio = AudioSegment.from_wav(audio_paths[0]) - 4 + main_gain
    backup_vocal_audio = AudioSegment.from_wav(audio_paths[1]) - 6 + backup_gain
    instrumental_audio = AudioSegment.from_wav(audio_paths[2]) - 7 + inst_gain
    combined_audio = main_vocal_audio.overlay(backup_vocal_audio).overlay(instrumental_audio)
    combined_audio.export(output_path, format=output_format)


def song_cover_pipeline(song_input, voice_model, pitch_change, keep_files,
                        is_webui=0, main_gain=0, backup_gain=0, inst_gain=0, index_rate=0.5, filter_radius=3,
                        rms_mix_rate=0.25, f0_method='rmvpe', crepe_hop_length=128, protect=0.33, pitch_change_all=0,
                        reverb_rm_size=0.15, reverb_wet=0.2, reverb_dry=0.8, reverb_damping=0.7, output_format='mp3',
                        cuda_number=0):
    try:
        if not song_input or not voice_model:
            print('Ensure that the song input field and voice model field is filled.', is_webui)

        display_progress('\n[~] Starting AI Cover Generation Pipeline...')

        with open(os.path.join(mdxnet_models_dir, 'model_data.json')) as infile:
            mdx_model_params = json.load(infile)

        # if youtube url
        if urlparse(song_input).scheme == 'https':
            input_type = 'yt'
            song_id = get_youtube_video_id(song_input)
            if song_id is None:
                error_msg = 'Invalid YouTube url.'
                print(error_msg, is_webui)

        # local audio file
        else:
            input_type = 'local'
            song_input = song_input.strip('\"')
            if os.path.exists(song_input):
                song_id = get_hash(song_input)
            else:
                error_msg = f'{song_input} does not exist.'
                song_id = None
                print(error_msg, is_webui)
        song_dir = os.path.join(output_dir, song_id)

        if not os.path.exists(song_dir):
            os.makedirs(song_dir)
            orig_song_path, vocals_path, instrumentals_path, main_vocals_path, backup_vocals_path, main_vocals_dereverb_path = preprocess_song(
                cuda_number, song_input, mdx_model_params, song_id, input_type)

        else:
            vocals_path, main_vocals_path = None, None
            paths = get_audio_paths(song_dir)

            # if any of the audio files aren't available or keep intermediate files, rerun preprocess
            if any(path is None for path in paths) or keep_files:
                orig_song_path, vocals_path, instrumentals_path, main_vocals_path, backup_vocals_path, main_vocals_dereverb_path = preprocess_song(
                    cuda_number, song_input, mdx_model_params, song_id, input_type)
            else:
                orig_song_path, instrumentals_path, main_vocals_dereverb_path, backup_vocals_path = paths

        pitch_change = pitch_change * 12 + pitch_change_all
        ai_vocals_path = os.path.join(song_dir,
                                      f'{os.path.splitext(os.path.basename(orig_song_path))[0]}_{voice_model}_p{pitch_change}_i{index_rate}_fr{filter_radius}_rms{rms_mix_rate}_pro{protect}_{f0_method}{"" if f0_method != "mangio-crepe" else f"_{crepe_hop_length}"}.wav')
        ai_cover_path = os.path.join(song_dir,
                                     f'{os.path.splitext(os.path.basename(orig_song_path))[0]} ({voice_model} Ver).{output_format}')

        if not os.path.exists(ai_vocals_path):
            display_progress('[~] Converting voice using RVC...')
            voice_change(cuda_number, voice_model, main_vocals_dereverb_path, ai_vocals_path, pitch_change, f0_method,
                         index_rate,
                         filter_radius, rms_mix_rate, protect, crepe_hop_length, is_webui)

        display_progress('[~] Applying audio effects to Vocals...')
        ai_vocals_mixed_path = add_audio_effects(ai_vocals_path, reverb_rm_size, reverb_wet, reverb_dry, reverb_damping)

        if pitch_change_all != 0:
            display_progress('[~] Applying overall pitch change')
            instrumentals_path = pitch_shift(instrumentals_path, pitch_change_all)
            backup_vocals_path = pitch_shift(backup_vocals_path, pitch_change_all)
        # BACK VOCAL CHANGE
        if not os.path.exists(backup_vocals_path):
            voice_change(cuda_number, voice_model, main_vocals_dereverb_path, backup_vocals_path, pitch_change, f0_method,
                         index_rate,
                         filter_radius, rms_mix_rate, protect, crepe_hop_length, is_webui)
        display_progress('[~] Combining AI Vocals and Instrumentals...')
        combine_audio([ai_vocals_mixed_path, backup_vocals_path, instrumentals_path], ai_cover_path, main_gain,
                      backup_gain, inst_gain, output_format)

        # if not keep_files:
        #     display_progress('[~] Removing intermediate audio files...')
        #     intermediate_files = [vocals_path, main_vocals_path, ai_vocals_mixed_path]
        #     if pitch_change_all != 0:
        #         intermediate_files += [instrumentals_path, backup_vocals_path]
        #     for file in intermediate_files:
        #         if file and os.path.exists(file):
        #             os.remove(file)

        return ai_cover_path

    except Exception as e:
        print(str(e), is_webui)


# def path_exist(song_dir):
#     try:
#         with open("songs_exist_list.txt", 'r') as reader:
#             lines = reader.readlines()
#             for line in lines:
#                 if line == song_dir:
#                     return True
#     except IOError as e:
#         print(e)
#     return False

def run_ai_cover_gen(song_input, rvc_dirname, pitch, index_rate=0.5, filter_radius=3, rms_mix_rate=0.25,
        pitch_detection_algo='rmvpe', crepe_hop_length=128, protect=0.33, main_vol=0, backup_vol=0, inst_vol=0,
        pitch_change_all=0, reverb_size=0.15, reverb_wetness=0.2, reverb_dryness=0.8, reverb_damping=0.7,
        output_format='mp3', start='0', time='-1', write_in_queue=True, cuda_number=0, output='None'):

    if not os.path.exists(os.path.join(rvc_models_dir, rvc_dirname)):
        raise Exception(f'The folder {os.path.join(rvc_models_dir, rvc_dirname)} does not exist.')
    cover_path = song_cover_pipeline(song_input, rvc_dirname, pitch, False,
                                     main_gain=main_vol, backup_gain=backup_vol, inst_gain=inst_vol,
                                     index_rate=index_rate, filter_radius=filter_radius,
                                     rms_mix_rate=rms_mix_rate, f0_method=pitch_detection_algo,
                                     crepe_hop_length=crepe_hop_length, protect=protect,
                                     pitch_change_all=pitch_change_all,
                                     reverb_rm_size=reverb_size, reverb_wet=reverb_wetness,
                                     reverb_dry=reverb_dryness, reverb_damping=reverb_damping,
                                     output_format=output_format, cuda_number=cuda_number)
    print(f'[+] Cover generated at {cover_path}')
    # ошибка при генерации
    if cover_path is None:
        # if youtube url
        if urlparse(song_input).scheme == 'https':
            song_id = get_youtube_video_id(song_input)
            if song_id is None:
                error_msg = 'Invalid YouTube url.'
                print(error_msg)

        # local audio file
        else:
            song_input = song_input.strip('\"')
            if os.path.exists(song_input):
                song_id = get_hash(song_input)
            else:
                error_msg = f'{song_input} does not exist.'
                song_id = None
                print(error_msg)
        print("DEV_TEMP: REMOVING " + os.path.join(output_dir, song_id))
        shutil.rmtree(os.path.join(output_dir, song_id))
        print("DEV_TEMP: REMOVED")
    else:
        if not write_in_queue:
            config.read('config.ini')
            config.set('voice', 'generated_path', cover_path)
            # Сохранение
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
        else:
            try:
                # Записываем путь файла в очередь
                with open(os.path.join(BASE_DIR, "caversAI/queue.txt"), "r", encoding='utf-8') as reader:
                    lines = reader.readlines()
                with open(os.path.join(BASE_DIR, "caversAI/queue.txt"), "w", encoding='utf-8') as writer:
                    writer.writelines(lines)
                    writer.write(f"{cover_path} -time {time} -start {start} -output {output}\n")
            except IOError as e:
                print(e)


if __name__ == '__main__':
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
    parser.add_argument('-start', '--start', type=str, default='0',
                        help='Здесь не используется. Время начала')
    parser.add_argument('-time', '--time', type=str, default='-1',
                        help='Здесь не используется. Длительность файла')
    parser.add_argument('-write', '--write-in-queue', type=bool, default=True,
                        help='нужно ли записать в файл queue')
    parser.add_argument('-cuda', '--cuda-number', type=int, default=0,
                        help='номер видеокарты')
    parser.add_argument('-output', '--output', type=str, default="None",
                        help='Здесь не используется. Отправка файла')
    args = parser.parse_args()

    rvc_dirname = args.rvc_dirname
    if not os.path.exists(os.path.join(rvc_models_dir, rvc_dirname)):
        raise Exception(f'The folder {os.path.join(rvc_models_dir, rvc_dirname)} does not exist.')
    cover_path = song_cover_pipeline(args.song_input, rvc_dirname, args.pitch_change, args.keep_files,
                                     main_gain=args.main_vol, backup_gain=args.backup_vol, inst_gain=args.inst_vol,
                                     index_rate=args.index_rate, filter_radius=args.filter_radius,
                                     rms_mix_rate=args.rms_mix_rate, f0_method=args.pitch_detection_algo,
                                     crepe_hop_length=args.crepe_hop_length, protect=args.protect,
                                     pitch_change_all=args.pitch_change_all,
                                     reverb_rm_size=args.reverb_size, reverb_wet=args.reverb_wetness,
                                     reverb_dry=args.reverb_dryness, reverb_damping=args.reverb_damping,
                                     output_format="mp3", cuda_number=args.cuda_number)
    print(f'[+] Cover generated at {cover_path}')
    # ошибка при генерации
    if cover_path is None:
        # if youtube url
        if urlparse(args.song_input).scheme == 'https':
            song_id = get_youtube_video_id(args.song_input)
            if song_id is None:
                error_msg = 'Invalid YouTube url.'
                print(error_msg)

        # local audio file
        else:
            song_input = args.song_input.strip('\"')
            if os.path.exists(song_input):
                song_id = get_hash(song_input)
            else:
                error_msg = f'{song_input} does not exist.'
                song_id = None
                print(error_msg)
        print("DEV_TEMP: REMOVING " + os.path.join(output_dir, song_id))
        shutil.rmtree(os.path.join(output_dir, song_id))
        print("DEV_TEMP: REMOVED")
    else:
        if not args.write_in_queue:
            config.read('config.ini')
            config.set('voice', 'generated_path', cover_path)
            # Сохранение
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
        else:
            try:
                # Записываем путь файла в очередь
                with open(os.path.join(BASE_DIR, "caversAI/queue.txt"), "r", encoding='utf-8') as reader:
                    lines = reader.readlines()
                with open(os.path.join(BASE_DIR, "caversAI/queue.txt"), "w", encoding='utf-8') as writer:
                    writer.writelines(lines)
                    writer.write(f"{cover_path} -time {args.time} -start {args.start} -output {args.output}\n")
            except IOError as e:
                print(e)
