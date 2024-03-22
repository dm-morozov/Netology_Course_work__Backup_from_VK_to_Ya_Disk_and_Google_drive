import os
import json
import requests
from datetime import datetime
from pprint import pprint
from tqdm import tqdm
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


class VkApiClient:

    """Класс для работы с VK API."""

    API_BASE_URL = 'https://api.vk.com/method/'


    def __init__(self, token, photo_type='z') -> None:

        """
        Инициализация класса.

        Args:
            token: Токен доступа к VK API.
            user_id: ID пользователя VK.
            photo_type: Размер фотографий (например, 'z' самый большой размер фото).
        """

        self.token = token
        self.photo_type = photo_type


    def get_common_params(self):

        """
        Получение общих параметров для запросов к VK API.

        Returns:
            Словарь с общими параметрами.
        """

        return {
            'access_token': self.token,
            'v': '5.131'
        }


    def status_info(self, user_id):

        """
        Получение информации о пользователе.
        
        Args:
            user_id: ID пользователя VK.

        Returns:
            {"Имя Фамилия": ID пользователя.}
        """

        params = {**self.get_common_params(), 'user_ids': user_id}
        url = self.API_BASE_URL + 'users.get'
        response = requests.get(url, params=params).json()
        first_name = response.get('response', [])[0].get('first_name')
        last_name = response.get('response', [])[0].get('last_name')
        user_id_info = response.get('response', [])[0].get('id')
        return {f"{first_name} {last_name}": user_id_info}


    def get_status(self, user_id):

        """
        Получение статуса пользователя.

        Args:
            user_id: ID пользователя VK.

        Returns:
            Строка с текстом статуса пользователя.
        """

        params = self.get_common_params()
        params.update({'user_ids': user_id})
        url = self.API_BASE_URL + 'status.get'
        response = requests.get(url, params=params)
        return response.json().get('response', {}).get('text')


    def set_status(self, user_id, new_status):
        """
        Изменение статуса пользователя.

        Args:
            user_id: ID пользователя VK.

            new_status: Новый текст статуса.

        Returns:
            Строка с текстом статуса пользователя.
        """

        params = self.get_common_params()
        params.update({'user_ids': user_id, 'text': new_status})
        url = self.API_BASE_URL + 'status.set'
        response = requests.get(url, params=params)
        response.raise_for_status()


    def replase_status(self, user_id, target, replace_string):

        """
        Замена текста в статусе пользователя.

        Args:
            target: Текст, который нужно заменить.
            replace_string: Текст, на который нужно заменить.

        Returns:
            Строка с текстом статуса пользователя.
        """

        status = self.get_status(user_id)
        new_status = status.replace(target, replace_string)
        return self.set_status(user_id, new_status)


    def get_profile_photos(self, user_id, count=5, album_id='profile'):
        
        """
        Получение фотографий профиля пользователя.

        Args:
            user_id: ID пользователя VK.

            count: Количество фотографий.

            album_id: Идентификатор альбома в VK (по умолчанию 'profile'): 
                'wall' — фотографии со стены;
                'profile' — фотографии профиля.

        Returns:
            Список с кортежами вида (likes, date, url).
            likes - количество лайков на фотографии;
            date - дата загрузки фотографии;
            url - URL-адрес фотографии.
        """

        profile_photos = []
        params = {**self.get_common_params(),
                  'owner_id': user_id,
                  'album_id': album_id,
                  'extended': 1,
                  'photo_sizes': 1,
                  'count': count
                  }
        url = self.API_BASE_URL + 'photos.get'
        response = requests.get(url, params=params)
        image_list = response.json()['response']['items']
        for image_info in image_list:
            for size in image_info['sizes']:
                if self.photo_type in size['type']:
                    profile_photo = image_info['likes']['count'], image_info['date'], size['url']
                    profile_photos.append(profile_photo)
        return profile_photos

    def save_photos_to_yandex_disk(self, album_id_vk, count_photos=5, album_id='profile'):

        """
        Сохранение фотографий c VK профиля пользователя на Яндекс.Диск.

        Args:
            album_id_vk: Идентификатор пользователя VK.    

            count_photos: количество фотографий, которые нужно сохранить на Яндекс.Диск, по умолчанию 5.

            album_id: Идентификатор альбома в VK (по умолчанию 'profile'): 
                'wall' — фотографии со стены;
                'profile' — фотографии профиля.
        """

        photos = self.get_profile_photos(album_id_vk, count_photos, album_id)
        headers = {'Authorization': f'OAuth {TOKEN_YA_DISK}'}
        folder_path = 'backup_photos'
        photo_info_json = []
        response = requests.get('https://cloud-api.yandex.net/v1/disk/resources',
                                headers=headers,
                                params={'path': folder_path})
        if response.status_code == 404:
            response = requests.put('https://cloud-api.yandex.net/v1/disk/resources',
                                    headers=headers,
                                    params={'path': folder_path})
        likes_counts = [photo[0] for photo in photos]
        for index, (likes, date, photo_url) in enumerate(tqdm(photos, desc="Загрузка фотографи на Яндекс.Диск", total=count_photos)):
            url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
            image_name = f"{likes}_likes.jpg"
            if likes_counts.count(likes) != 1:
                date = datetime.fromtimestamp(
                    date).strftime('%Y-%m-%d_%H-%M-%S')
                image_name = f"{likes}_likes__{date}.jpg"
            params = {'path': f'{folder_path}/{image_name}',
                      'url': photo_url,
                      'disable_redirects': 'true'}
            response = requests.post(url, headers=headers, params=params)
            photo_info_json.append(
                {'file_name': image_name, 'size': self.photo_type})
            # print(f"Загрузка фотографии № {index+1} из {count_photos} на Яндекс.Диск: {image_name}")
        with open('photo_info_ya_disk.json', 'w') as json_file:
            json.dump(photo_info_json, json_file, indent=4)


    def save_photos_to_google_drive(self, album_id_vk, count_photos=5, album_id='profile'):

        """
        Сохранение фотографий c VK профиля пользователя на Google Диск.

        Args:
            album_id_vk: Идентификатор пользователя VK.

            count_photos: количество фотографий, которые нужно сохранить на Google Drive, по умолчанию 5.

            album_id: Идентификатор альбома в VK (по умолчанию 'profile'): 
                'wall' — фотографии со стены;
                'profile' — фотографии профиля.
        """

        photos = self.get_profile_photos(album_id_vk, count_photos, album_id)
        SCOPES = ["https://www.googleapis.com/auth/drive"]
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        service = build("drive", "v3", credentials=creds)

        # Проверка существования папки backup_photos именно в родительском каталоге
        folder_name = "backup_photos"
        folder_id = None
        query = f"name='{
            folder_name}' and mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"

        response = service.files().list(q=query, fields="files(id)").execute()
        folders = response.get('files', [])
        if folders:
            folder_id = folders[0]['id']
        else:
            # Если папка не существует, создаем ее
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = service.files().create(body=folder_metadata, fields="id").execute()
            folder_id = folder.get("id")

        photo_info_json = []
        likes_counts = [photo[0] for photo in photos]
        for index, (likes, date, photo_url) in enumerate(tqdm(photos, 
                                                              desc="Загрузка фотографи на Google Диск", 
                                                              total=count_photos)):
            image_name = f"{likes}_likes.jpg"
            if likes_counts.count(likes) > 1:
                date = datetime.fromtimestamp(date).strftime('%Y-%m-%d_%H-%M-%S')
                image_name = f"{likes}_likes__{date}.jpg"
            file_metadata = {
                "name": image_name,
                "parents": [folder_id],
                "mimeType": "image/jpeg"
            }
            response = requests.get(photo_url)
            media = MediaInMemoryUpload(response.content, 
                                        resumable=True, 
                                        mimetype='image/jpeg')
            
            created_file = service.files().create(body=file_metadata,
                                          media_body=media,
                                          fields="id").execute()
            
            # Очищаем переменную, чтобы не было утечки памяти
            media = None

            photo_info_json.append({'file_name': image_name, 'size': self.photo_type})
            # print(f"Загрузка фотографии № {index+1} из {count_photos} на Google Диск: {image_name}")
        with open('photo_info_g_drive.json', 'w') as json_file:
            json.dump(photo_info_json, json_file, indent=4)


with open('api.txt', 'r') as token:
    TOKEN_VK = token.readline()
    USER_ID = token.readline()
    TOKEN_YA_DISK = token.readline()

if __name__ == '__main__':
    vk_client = VkApiClient(TOKEN_VK)
    print(vk_client.status_info(USER_ID))

    # print(vk_client.get_status(USER_ID))
    # vk_client.replase_status(USER_ID, 'Изучаю', 'Учу')
    # print(vk_client.get_status(USER_ID))

    # pprint(vk_client.get_profile_photos(USER_ID))
    vk_client.save_photos_to_yandex_disk(USER_ID, 5)
    vk_client.save_photos_to_google_drive(USER_ID, 10, 'wall')

    print('Работа завершена')
