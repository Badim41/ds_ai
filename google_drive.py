import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload


def authenticate():
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    CREDS = None

    if os.path.exists("token.json"):
        CREDS = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not CREDS or not CREDS.valid:
        if CREDS and CREDS.expired and CREDS.refresh_token:
            CREDS.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            CREDS = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(CREDS.to_json())

    return CREDS


# FOLDER_ID = '1bOZGgoDW2SSW6nZ4WF323mYyCA6RoQ4u'
CREDS = authenticate()
SERVICE = build('drive', 'v3', credentials=CREDS)


# Функция для добавления файлов в папку на Google Диске
def upload_files(service, folder_id, file_paths):
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]  # ID папки на Google Диске
        }
        media = MediaFileUpload(file_path)
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Файл {file_name} успешно загружен в папку application")


# Функция для загрузки файлов и папок в Google Диск
# фильтры для файлов
FILTERS = ["Vocals_Backup", "pro0", "Instrumental"]


def upload_files_and_folders(service, parent_folder_id, local_path):
    print("Upload to google disk")
    for item in os.listdir(local_path):

        item_path = os.path.join(local_path, item)

        print(item_path)
        skip_file = True
        for filter_1 in FILTERS:
            if filter_1 in item_path and "mixed" not in item_path:
                skip_file = False

        if skip_file:
            continue

        if os.path.isfile(item_path):
            file_metadata = {
                'name': item,
                'parents': [parent_folder_id]
            }
            media = MediaFileUpload(item_path)
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"Файл {item} успешно загружен в Google Диск")

        elif os.path.isdir(item_path):
            folder_metadata = {
                'name': item,
                'parents': [parent_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            print(f"Папка {item} успешно создана на Google Диск")

            upload_files_and_folders(service, folder['id'], item_path)


# Функция для скачивания файлов с Google Диска
def download_files(service, folder_id, download_path):
    results = service.files().list(q=f"'{folder_id}' in parents", fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('Нет файлов для скачивания.')
    else:
        for item in items:
            file_id = item['id']
            file_name = item['name']
            request = service.files().get_media(fileId=file_id)
            fh = open(os.path.join(download_path, file_name), 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            print(f"Файл {file_name} успешно скачан в папку google_disk")


def download_folder(service, folder_id, download_path):
    if not os.path.exists(download_path):
        os.mkdir(download_path)

    results = service.files().list(q=f"'{folder_id}' in parents", fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    if not items:
        print('Нет файлов для скачивания.')
    else:
        for item in items:
            file_id = item['id']
            file_name = item['name']
            file_mime_type = item['mimeType']

            if 'application/vnd.google-apps' in file_mime_type:
                print(
                    f"Файл '{file_name}' невозможно скачать напрямую, так как это файл Google Docs или другой тип, который не поддерживает экспорт.")
                continue

            request = service.files().get_media(fileId=file_id)
            file_path = os.path.join(download_path, file_name)
            fh = open(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            print(f"Файл '{file_name}' успешно скачан в папку '{download_path}'")


# download_destination = 'path_to_download_folder'
# download_folder(SERVICE, FOLDER_ID, download_destination)
upload_files_and_folders(SERVICE, "1AYzqrKE-slEQMfxt0rSCkxH1uLbmuZny", "song_output")
