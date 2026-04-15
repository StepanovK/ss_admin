import requests
import datetime
import config
from config import logger


class VKOAuth:
    """Класс для работы с OAuth ВКонтакте"""

    TOKEN_URL = 'https://id.vk.com/oauth2/auth'
    REFRESH_URL = 'https://id.vk.com/oauth2/refresh'

    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        self.client_id = client_id or config.vk_oauth_client_id
        self.client_secret = client_secret or config.vk_oauth_client_secret
        self.redirect_uri = redirect_uri or config.vk_oauth_redirect_uri

    def get_token_by_code(self, code, device_id=None):
        """Получение токена по коду авторизации"""
        payload = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        if device_id:
            payload['device_id'] = device_id

        try:
            response = requests.post(self.TOKEN_URL, data=payload)
            response.raise_for_status()
            data = response.json()

            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in'),
                'user_id': data.get('user_id'),
            }
        except Exception as ex:
            logger.error(f'Failed to get token by code: {ex}')
            return None

    def refresh_token(self, refresh_token, device_id=None):
        """Обновление токена по refresh_token"""
        payload = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
        }
        if device_id:
            payload['device_id'] = device_id

        try:
            response = requests.post(self.REFRESH_URL, data=payload)
            response.raise_for_status()
            data = response.json()

            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in'),
            }
        except Exception as ex:
            logger.error(f'Failed to refresh token: {ex}')
            return None

    def get_auth_url(self, state=None):
        """Получить URL для авторизации (для первоначального получения кода)"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'v': '5.199',
        }
        if state:
            params['state'] = state

        from urllib.parse import urlencode
        return f'https://id.vk.com/authorize?{urlencode(params)}'
