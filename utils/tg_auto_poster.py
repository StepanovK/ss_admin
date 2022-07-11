import os
from pathlib import Path
from pyrogram import Client
from TG_AutoPoster import AutoPoster
from TG_AutoPoster.utils import Post, Sender
import config
from utils.connection_holder import ConnectionsHolder


class MyAutoPoster(AutoPoster):
    def __init__(self, cache_dir: Path = Path(".cache"), **kwargs):
        self.directory = os.getcwd()
        name = self.__class__.__name__.lower()
        Client.__init__(self,
                        name,
                        **config.telegram,
                        **kwargs, )
        self.domain = config.domain
        self.cache_dir = cache_dir.absolute()
        self.what_to_parse = "all"
        self._session = ConnectionsHolder().vk_api_admin
        self.connect()
        self.me = self.sign_in_bot(config.telegram.get("bot_token"))

    def send_new_post(self, post):
        try:
            os.chdir(self.cache_dir)
        except FileNotFoundError:
            self.cache_dir.mkdir()
            os.chdir(self.cache_dir)
        post = self._session.method(
            method="wall.getById",
            values={"posts": post},
        )
        parsed_post = Post(
            post[0],
            self.domain,
            self._session,
            sign_posts=True,
            what_to_parse={self.what_to_parse}

        )
        parsed_post.parse_post()
        sender = Sender(
            bot=self,
            post=parsed_post,
            chat_ids=[config.channel])
        sender.send_post()
        for data in self.cache_dir.iterdir():
            data.unlink()
        try:
            os.chdir(Path(self.directory))
        except FileNotFoundError:
            Path(self.directory).mkdir()
            os.chdir(Path(self.directory))


if __name__ == "__main__":
    auto_sender = MyAutoPoster()
    auto_sender.send_new_post("-187393286_512")
