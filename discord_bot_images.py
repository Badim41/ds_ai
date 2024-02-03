from PIL import Image
from moviepy.video.io.VideoFileClip import VideoFileClip

from discord_bot import *
from video_change import video_pipeline


@bot.slash_command(name="change_video",
                   description='Перерисовать и переозвучить видео')
async def __change_video(
        ctx,
        video_path: Option(discord.SlashCommandOptionType.attachment, description='Файл с видео',
                           required=True),
        fps: Option(int, description='Частота кадров (ОЧЕНЬ влияет на время ожидания))', required=True,
                    choices=[30, 15, 10, 6, 5, 3, 2, 1]),
        extension: Option(str, description='Расширение (сильно влияет на время ожидания)', required=True,
                          choices=["144p", "240p", "360p", "480p", "720p"]),
        prompt: Option(str, description='запрос', required=True),
        negative_prompt: Option(str, description='негативный запрос', default="NSFW", required=False),
        steps: Option(int, description='число шагов', required=False,
                      default=30,
                      min_value=1,
                      max_value=500),
        seed: Option(int, description='сид изображения', required=False,
                     default=random.randint(1, 1000000),
                     min_value=1,
                     max_value=1000000),
        strength: Option(float, description='насколько сильны будут изменения', required=False,
                         default=0.15, min_value=0,
                         max_value=1),
        strength_prompt: Option(float,
                                description='ЛУЧШЕ НЕ ТРОГАТЬ! Насколько сильно генерируется положительный промпт',
                                required=False,
                                default=0.85, min_value=0.1,
                                max_value=1),
        strength_negative_prompt: Option(float,
                                         description='ЛУЧШЕ НЕ ТРОГАТЬ! Насколько сильно генерируется отрицательный промпт',
                                         required=False,
                                         default=1, min_value=0.1,
                                         max_value=1),
        voice_name: Option(str, description='Голос для видео', required=False, default="None")
):
    cuda_all = None
    try:
        await ctx.defer()

        # ошибки входных данных
        voices = (await set_get_config_all("Sound", "voices")).replace("\"", "").replace(",", "").split(";")
        if voice_name not in voices:
            await ctx.respond("Выберите голос из списка: " + ';'.join(voices))
            return

        if not image_generators:
            await ctx.respond("модель для картинок не загружена")
            return

        filename = f"{ctx.author.id}.mp4"
        await video_path.save(filename)
        # сколько кадров будет в результате
        video_clip = VideoFileClip(filename)
        total_frames = int((video_clip.fps * video_clip.duration) / (30 / fps))
        max_frames = int(await set_get_config_all("Video", "max_frames", None))
        if max_frames <= total_frames:
            await ctx.send(
                f"Слишком много кадров, снизьте параметр FPS! Максимальное разрешённое количество кадров в видео: {max_frames}. Количество кадров у вас - {total_frames}")
            return

        # используем видеокарты
        cuda_avaible = await cuda_manager.check_cuda_images()
        if cuda_avaible == 0:
            await ctx.respond("Нет свободных видеокарт")
            return
        else:
            await ctx.respond(f"Используется {cuda_avaible} видеокарт для обработки видео")

        cuda_all = []
        for i in range(cuda_avaible):
            cuda_all.append(await cuda_manager.use_cuda_images())

        # run timer
        timer = Time_Count()

        if len(cuda_all) > 1:
            seconds = total_frames * 13 / len(cuda_all)
        else:
            seconds = total_frames * 16
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            remaining_seconds = seconds % 60
            if minutes == 0 and remaining_seconds == 0:
                time_spend = f"{hours} часов"
            elif remaining_seconds == 0:
                time_spend = f"{hours} часов, {minutes} минут"
            elif minutes == 0:
                time_spend = f"{hours} часов, {remaining_seconds} секунд"
            else:
                time_spend = f"{hours} часов, {minutes} минут, {remaining_seconds} секунд"
        elif seconds >= 60:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds == 0:
                time_spend = f"{minutes} минут"
            else:
                time_spend = f"{minutes} минут, {remaining_seconds} секунд"
        else:
            time_spend = f"{seconds} секунд"
        await ctx.send(f"Видео будет обрабатываться ~{time_spend}")
        print("params suc")
        # wait for answer
        video_path = await video_pipeline(video_path=filename, fps_output=fps, video_extension=extension, prompt=prompt,
                                          voice_name=voice_name, video_id=ctx.author.id, cuda_all=cuda_all,
                                          strength_negative_prompt=strength_negative_prompt,
                                          strength_prompt=strength_prompt,
                                          strength=strength, seed=seed, steps=steps, negative_prompt=negative_prompt)

        await ctx.send("Вот как я изменил ваше видео🖌. Потрачено " + timer.count_time())
        await send_file(ctx, video_path)
        # освобождаем видеокарты
        for i in cuda_all:
            await cuda_manager.stop_use_cuda_images(i)
    except Exception as e:
        await ctx.send(f"Ошибка при изменении картинки (с параметрами\
                          {fps, extension, prompt, negative_prompt, steps, seed, strength, strength_prompt, voice_name}\
                          ): {e}")
        if cuda_all:
            for i in range(cuda_avaible):
                await cuda_manager.stop_use_cuda_images(i)

        traceback_str = traceback.format_exc()
        await logger.logging(str(traceback_str), Color.RED)
        raise e


@bot.slash_command(name="change_image", description='изменить изображение нейросетью')
async def __image(ctx,
                  image: Option(discord.SlashCommandOptionType.attachment, description='Изображение',
                                required=True),
                  prompt: Option(str, description='запрос', required=True),
                  negative_prompt: Option(str, description='негативный запрос', default="NSFW", required=False),
                  steps: Option(int, description='число шагов', required=False,
                                default=60,
                                min_value=1,
                                max_value=500),
                  seed: Option(int, description='сид изображения', required=False,
                               default=None,
                               min_value=1,
                               max_value=9007199254740991),
                  x: Option(int,
                            description='изменить размер картинки по x',
                            required=False,
                            default=None, min_value=64,
                            max_value=768),
                  y: Option(int,
                            description='изменить размер картинки по y',
                            required=False,
                            default=None, min_value=64,
                            max_value=768),
                  strength: Option(float, description='насколько сильны будут изменения', required=False,
                                   default=0.5, min_value=0,
                                   max_value=1),
                  strength_prompt: Option(float,
                                          description='ЛУЧШЕ НЕ ТРОГАТЬ! Насколько сильно генерируется положительный промпт',
                                          required=False,
                                          default=0.85, min_value=0.1,
                                          max_value=1),
                  strength_negative_prompt: Option(float,
                                                   description='ЛУЧШЕ НЕ ТРОГАТЬ! Насколько сильно генерируется отрицательный промпт',
                                                   required=False,
                                                   default=1, min_value=0.1,
                                                   max_value=1),
                  repeats: Option(int,
                                  description='Количество повторов',
                                  required=False,
                                  default=1, min_value=1,
                                  max_value=16)
                  ):
    async def get_image_dimensions(file_path):
        with Image.open(file_path) as img:
            sizes = img.size
        return str(sizes).replace("(", "").replace(")", "").replace(" ", "").split(",")

    await ctx.defer()
    if not image_generators:
        await ctx.respond("модель для картинок не загружена")
        return

    for i in range(repeats):
        cuda_number = None
        try:
            try:
                cuda_number = await cuda_manager.use_cuda_images()
            except Exception:
                await ctx.respond("Нет свободных видеокарт")
                return

            timer = Time_Count()
            input_image = "images/image" + str(ctx.author.id) + ".png"
            await image.save(input_image)
            # get image size and round to 64
            if x is None or y is None:
                x, y = await get_image_dimensions(input_image)
                x = int(x)
                y = int(y)
                # скэйлинг во избежания ошибок из-за нехватки памяти
                scale_factor = (1000000 / (x * y)) ** 0.5
                x = int(x * scale_factor)
                y = int(y * scale_factor)
            if not x % 64 == 0:
                x = ((x // 64) + 1) * 64
            if not y % 64 == 0:
                y = ((y // 64) + 1) * 64
            print("X:", x, "Y:", y)
            # loading params
            if seed is None or repeats > 1:
                seed_current = random.randint(1, 9007199254740991)
            else:
                seed_current = seed
            image_path = image_generators[cuda_number].generate_image(prompt, negative_prompt, x, y, steps, seed,
                                                                      strength,
                                                                      strength_prompt,
                                                                      strength_negative_prompt, input_image)

            # отправляем
            text = "Вот как я изменил ваше изображение🖌. Потрачено " + timer.count_time() + f"сид:{seed_current}"
            if repeats == 1:
                await ctx.respond(text)
            else:
                await ctx.send(text)

            await send_file(ctx, image_path, delete_file=True)
            # перестаём использовать видеокарту
            await cuda_manager.stop_use_cuda_images(cuda_number)
        except Exception as e:
            traceback_str = traceback.format_exc()
            await logger.logging(str(traceback_str), Color.RED)
            await ctx.send(f"Ошибка при изменении картинки (с параметрами\
                              {prompt, negative_prompt, steps, x, y, strength, strength_prompt, strength_negative_prompt}): {e}")
            # перестаём использовать видеокарту
            if not cuda_number is None:
                await cuda_manager.stop_use_cuda_images(cuda_number)