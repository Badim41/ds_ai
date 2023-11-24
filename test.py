import argparse
import asyncio
import random

import g4f

PROXY_LIST = ['http://107.172.217.135:8080', 'http://181.191.226.1:999', 'socks4://94.40.90.49:5678',
              'http://5.255.107.249:8080', 'socks4://200.85.34.174:4153', 'http://200.32.51.179:8080',
              'socks4://136.143.144.187:5678', 'http://80.78.64.70:8080', 'socks4://201.144.8.115:5678',
              'http://195.225.142.169:8080', 'socks5://115.127.31.163:9990', 'http://62.201.217.194:8080',
              'socks4://36.66.36.251:4153', 'http://101.109.176.88:8080', 'http://103.148.232.37:3128',
              'socks4://177.91.76.34:4153', 'socks4://42.62.176.106:4153', 'socks4://45.157.190.58:5566',
              'http://71.14.23.121:8080', 'http://138.117.86.157:999', 'socks4://103.191.58.22:5678',
              'http://176.235.182.99:8080', 'socks5://195.201.173.249:2530', 'http://200.39.138.45:999',
              'http://61.7.157.51:8080', 'socks4://1.4.195.114:4145', 'http://138.204.95.166:8080',
              'http://24.152.50.116:999', 'http://191.6.15.104:8080', 'http://78.188.81.57:8080',
              'socks4://103.154.93.2:1080', 'socks4://169.255.189.105:4145', 'socks4://83.143.24.29:5678',
              'socks4://82.132.19.108:4153', 'http://203.150.172.151:8080', 'socks5://184.95.235.194:1080',
              'http://102.68.128.218:8080', 'socks4://202.40.177.94:5678', 'http://202.146.230.146:8080',
              'socks4://160.19.155.51:5678', 'http://189.240.60.168:9090', 'http://24.152.50.114:999',
              'http://202.51.192.106:8080', 'socks4://45.128.133.153:1080', 'socks4://27.153.148.170:5678',
              'http://122.155.165.191:3128', 'socks4://83.17.222.146:5678', 'http://170.239.207.242:999',
              'http://95.56.254.139:3128', 'http://200.106.184.21:999', 'http://223.241.77.2:8089',
              'http://182.52.229.165:8080', 'http://185.139.56.133:6961', 'socks4://206.201.0.227:4145',
              'socks5://185.231.115.246:7237', 'http://190.107.236.180:999', 'http://179.108.209.63:8080',
              'socks4://185.95.199.103:1099', 'http://103.48.68.108:83', 'socks4://103.78.54.13:4153',
              'socks5://222.223.115.225:7302', 'http://200.215.248.114:999', 'http://189.203.201.146:8080',
              'http://170.83.242.251:999', 'http://190.107.236.181:999', 'http://181.78.19.242:999',
              'http://38.49.138.140:999', 'http://181.78.15.105:999', 'http://175.140.159.244:3128',
              'http://191.96.100.33:3128', 'http://154.73.28.193:8080', 'socks5://119.148.4.51:9990',
              'socks4://103.76.179.122:4153', 'http://34.140.70.242:8080', 'socks4://1.20.95.95:5678',
              'http://92.242.214.133:1400', 'socks4://45.234.100.102:1080', 'http://201.219.247.34:999',
              'http://103.184.180.233:8080', 'socks4://103.76.172.230:4153', 'socks4://187.252.154.90:4153',
              'http://77.238.79.111:8080', 'http://181.10.117.254:999', 'http://190.61.55.138:999',
              'socks4://201.20.79.182:5678', 'http://79.106.33.26:8079', 'http://167.86.97.239:9100',
              'http://185.200.38.199:8080', 'socks4://72.49.49.11:31034', 'socks4://72.195.114.184:4145',
              'socks4://24.249.199.4:4145', 'socks4://24.249.199.12:4145', 'socks4://174.77.111.196:4145',
              'socks4://174.64.199.82:4145', 'socks4://174.77.111.197:4145', 'socks4://174.64.199.79:4145',
              'socks4://72.195.34.58:4145', 'socks4://98.162.25.23:4145', 'socks4://72.206.181.103:4145',
              'socks4://72.217.216.239:4145', 'socks4://98.170.57.231:4145', 'socks4://184.181.217.210:4145',
              'socks4://98.175.31.195:4145', 'socks4://98.188.47.132:4145', 'socks4://72.195.114.169:4145',
              'socks4://98.188.47.150:4145', 'socks4://72.195.34.59:4145', 'socks4://72.195.34.42:4145',
              'socks4://72.210.208.101:4145', 'socks4://192.111.138.29:4145', 'socks4://192.111.137.34:18765',
              'socks4://192.111.139.165:4145', 'socks4://192.111.130.2:4145', 'socks4://98.170.57.249:4145',
              'socks4://72.206.181.97:64943', 'socks4://98.162.25.7:31653', 'socks4://70.166.167.55:57745',
              'socks4://72.195.34.41:4145', 'socks4://184.178.172.23:4145', 'socks4://72.210.252.137:4145',
              'socks4://98.162.25.16:4145', 'socks4://184.178.172.26:4145', 'socks4://72.210.221.197:4145',
              'socks4://72.210.221.223:4145', 'socks4://68.71.254.6:4145', 'socks4://68.71.247.130:4145',
              'socks4://104.37.135.145:4145', 'socks4://68.1.210.163:4145', 'socks4://98.181.137.80:4145',
              'socks4://184.170.245.148:4145', 'socks4://72.37.217.3:4145', 'socks4://72.37.216.68:4145',
              'socks4://206.220.175.2:4145', 'socks4://142.54.228.193:4145', 'socks4://142.54.229.249:4145',
              'socks4://142.54.232.6:4145', 'socks4://192.111.134.10:4145', 'socks4://198.8.84.3:4145',
              'socks4://142.54.235.9:4145', 'socks4://142.54.237.34:4145', 'socks4://107.152.98.5:4145',
              'socks4://104.200.152.30:4145', 'socks4://107.181.168.145:4145', 'socks4://104.200.135.46:4145',
              'socks4://142.54.236.97:4145', 'socks4://199.102.104.70:4145', 'socks4://199.102.105.242:4145',
              'socks4://67.201.59.70:4145', 'socks4://68.1.210.189:4145', 'socks4://199.187.210.54:4145',
              'socks4://72.217.158.202:4145', 'socks4://36.92.81.181:4145', 'socks4://192.252.220.89:4145',
              'socks4://185.72.225.10:44098', 'socks4://212.83.142.114:40959', 'socks5://72.206.181.123:4145',
              'socks5://192.252.220.92:17328', 'socks5://184.181.217.194:4145', 'socks5://192.111.137.37:18762',
              'socks5://192.111.130.5:17002', 'socks5://192.252.208.70:14282', 'socks5://192.111.135.17:18302',
              'socks5://192.111.139.163:19404', 'socks5://72.210.252.134:46164', 'socks5://72.195.34.35:27360',
              'socks5://98.162.25.4:31654', 'socks5://98.162.25.29:31679', 'socks5://174.77.111.198:49547',
              'socks5://98.178.72.21:10919', 'socks5://72.195.34.60:27391', 'socks5://184.178.172.25:15291',
              'socks5://68.71.249.153:48606', 'socks5://98.181.137.83:4145', 'socks5://74.119.144.60:4145',
              'socks5://184.170.248.5:4145', 'socks5://199.58.185.9:4145', 'socks5://199.116.114.11:4145',
              'socks5://199.102.106.94:4145', 'socks5://70.166.167.38:57728', 'socks5://65.169.38.73:26592',
              'socks5://72.206.181.105:64935', 'socks5://198.8.94.174:39078', 'socks5://64.227.108.25:31908',
              'socks5://51.15.135.81:1080', 'socks5://45.132.75.19:19801', 'socks5://37.18.73.60:5566',
              'socks5://37.221.193.221:18181', 'socks5://47.243.239.165:8870', 'socks5://212.83.137.94:12667',
              'socks5://45.91.92.45:32383', 'socks5://64.176.213.57:55566', 'socks5://46.52.135.236:1080',
              'socks5://43.132.226.202:15673', 'socks5://66.29.128.245:65210']

_providers = [
    # AUTH
    g4f.Provider.Raycast,
    g4f.Provider.Phind,
    g4f.Provider.Liaobots,  # - Doker output
    g4f.Provider.Bing,
    g4f.Provider.Bard,
    g4f.Provider.OpenaiChat,
    g4f.Provider.Theb,

    # good providers
    g4f.Provider.GPTalk,
    g4f.Provider.AiAsk,  # - rate limit
    g4f.Provider.GeekGpt,  # short answer
    g4f.Provider.Vercel,  # cut answer
    g4f.Provider.ChatgptDemo,  # error 403
    g4f.Provider.ChatgptLogin,  # error 403
    g4f.Provider.ChatgptX,  # error
    g4f.Provider.Theb,
    g4f.Provider.ChatgptFree,
    g4f.Provider.AItianhuSpace,
    g4f.Provider.AItianhu,
    g4f.Provider.ChatForAi,

    # bad providers
    g4f.Provider.You,  # dont work
    g4f.Provider.NoowAi,  # normal, but not so good
    g4f.Provider.GptGod,  # error list
    # g4f.Provider.FreeGpt,# wrong language
    g4f.Provider.ChatgptAi,  # - error ID
    g4f.Provider.GptGo,  # error 403
    # g4f.Provider.GptForLove,  # error no module
    g4f.Provider.Opchatgpts,  # bad
    g4f.Provider.Chatgpt4Online,  # - bad
    # g4f.Provider.ChatBase,  # - bad, but you can use it
    # g4f.Provider.Llama2, # no model
]


async def remove_last_format_simbols(text, format="```"):
    parts = text.split(format)
    if len(parts) == 4:
        corrected_text = format.join(parts[:3]) + parts[3]
        return corrected_text
    return text


async def run_all_gpt(prompt, proxy, mode):
    if mode == "fast":
        functions = [one_gpt_run(provider, proxy, prompt, 120) for provider in _providers]  # список функций
        functions += [one_gpt_run(g4f.Provider.Vercel, proxy, prompt, 120, gpt_model=gpt_model) for gpt_model in
                      ["gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "text-davinci-003"]]
        functions += [one_gpt_run(g4f.Provider.Vercel, proxy, prompt, 120, gpt_model=gpt_model) for gpt_model in
                      ["gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "text-davinci-003"]]
        done, _ = await asyncio.wait(functions, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = await task
            return result
    if mode == "all":
        functions = [one_gpt_run(provider, proxy, prompt, 1) for provider in _providers]  # список функций
        functions += [one_gpt_run(g4f.Provider.Vercel, proxy, prompt, 1, gpt_model=gpt_model) for gpt_model in
                      ["gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "text-davinci-003"]]
        functions += [one_gpt_run(providers, proxy, prompt, 1, gpt_model="gpt-4") for providers in
                      [g4f.Provider.GeekGpt, g4f.Provider.Liaobots, g4f.Provider.Raycast]]
        results = await asyncio.gather(*functions)  # результаты всех функций
        new_results = []
        for i, result in enumerate(results):
            if not result is None and not result.replace("\n", "").replace(" ", "") == "" or result == "None":
                new_results.append(result)
        return '\n\n\n'.join(new_results)
    else:
        functions = [one_gpt_run(provider, proxy, prompt, 1, provider_name=mode) for provider in
                     _providers]  # список функций
        results = await asyncio.gather(*functions)  # результаты всех функций
        new_results = []
        for i, result in enumerate(results):
            if not result is None and not result.replace("\n", "").replace(" ", "") == "":
                new_results.append(result)
        return '\n\n\n'.join(new_results)


async def chatgpt_get_result(prompt, gpt_mode):
    # 5 плохих прокси
    random.shuffle(PROXY_LIST)
    proxy_array_temp = PROXY_LIST[:4]
    # без прокси
    proxy_array_temp.append(None)
    functions = [run_all_gpt(prompt, proxy, gpt_mode) for proxy in proxy_array_temp]
    done, pending = await asyncio.wait(functions, return_when=asyncio.FIRST_COMPLETED)

    # Принудительное завершение оставшихся функций
    for task in pending:
        task.cancel()

    # Получение результата выполненной функции
    for task in done:
        result = await task
        if result.strip():
            return result
        else:
            return await chatgpt_get_result(prompt, gpt_mode)


async def one_gpt_run(provider, proxy, prompt, delay_for_gpt, provider_name=".", gpt_model="gpt-3.5-turbo"):
    if provider_name not in str(provider):
        return None
    try:
        if "Bing" in str(provider):
            gpt_model = "gpt-4"
        if "Phind" in str(provider):
            gpt_model = "gpt-4"
            # print(os.path.ab
        if proxy:
            result = await g4f.ChatCompletion.create_async(
                model=gpt_model,
                provider=provider,
                messages=[{"role": "user", "content": prompt}],
                auth=True,
                proxy=proxy,
                timeout=60
            )
        else:
            result = await g4f.ChatCompletion.create_async(
                model=gpt_model,
                provider=provider,
                messages=[{"role": "user", "content": prompt}],
                auth=True,
                timeout=60
            )
        if "!DOCTYPE" in str(result):
            # делаем задержку
            await asyncio.sleep(delay_for_gpt)
            return

        if result is None or result.replace("\n", "").replace(" ", "") == "" or result == "None":
            # делаем задержку, чтобы не вывелся пустой результат
            await asyncio.sleep(delay_for_gpt)
            return

        # если больше 3 "```" (форматов)
        result = await remove_last_format_simbols(result)

        # добавляем имя провайдера
        # provider = str(provider)
        # provider = provider[provider.find("'") + 1:]
        # provider = provider[:provider.find("'")]
        # return result + f"\n||Провайдер: {provider}, Модель: {gpt_model}||"

        return result
    except Exception:
        await asyncio.sleep(delay_for_gpt)
        return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('-prompt', '--prompt', type=str, required=True,
                        help='Запрос для GPT')
    parser.add_argument('-mode', '--mode', type=str, required=False, default="fast",
                        help='Мод GPT')

    args = parser.parse_args()

    asyncio.run(chatgpt_get_result(args.prompt, args.mode))
