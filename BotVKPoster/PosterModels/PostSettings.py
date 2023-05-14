from peewee import *
from .base import BaseModel


class PostSettings(BaseModel):
    post_id = CharField(100, primary_key=True)
    reformat_text = BooleanField(default=False)

    class Meta:
        table_name = 'post_settings'

    @classmethod
    def get_post_settings(cls, post_id: str) -> dict:
        settings = {
            'reformat_text': False
        }

        try:
            post_settings = PostSettings.get(post_id=post_id)
            settings['reformat_text'] = post_settings.reformat_text
        except PostSettings.DoesNotExist:
            pass

        return settings
