import requests
import youtube_dl
from moviepy.editor import *
from PIL import Image, ImageEnhance


class WatermarkCreator:
    def __init__(self, watermark: str, opacity: float = 0.4):
        self.watermark = watermark
        self.opacity = opacity

    def add_photo_watermark(self, image: requests.models.Response) -> Image:
        image = Image.open(image.raw)
        watermark = Image.open(self.watermark)
        assert 0 <= self.opacity <= 1
        if self.opacity < 1:
            if watermark.mode != 'RGBA':
                watermark = watermark.convert('RGBA')
            else:
                watermark = watermark.copy()
            alpha = watermark.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(self.opacity)
            watermark.putalpha(alpha)
        layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
        title_w, title_h = layer.size
        watermark_w, watermark_h = watermark.size
        layer.paste(watermark, (title_w - watermark_w - 8, title_h - watermark_h - 8))
        return Image.composite(layer, image, layer)

    def add_video_watermark(self, video: str) -> str:
        # title = video.split('.')[0] + '.webm'
        title = video.split('.')[0] + '_new.mp4'
        watermark = Image.open(self.watermark)
        assert 0 <= self.opacity <= 1
        if self.opacity < 1:
            if watermark.mode != 'RGBA':
                watermark = watermark.convert('RGBA')
            else:
                watermark = watermark.copy()
            alpha = watermark.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(self.opacity)
            watermark.putalpha(alpha)
            watermark.save("new_logo.png")
        video = VideoFileClip(video, audio=True)
        # Make the text. Many more options are available.
        logo = (ImageClip("new_logo.png")
                .set_duration(video.duration)
                # .resize(height=50) # if you need to resize...
                .margin(right=8, bottom=8, opacity=0)  # (optional) logo-border padding
                .set_pos(("right", "bottom")))
        result = CompositeVideoClip([video, logo])  # Overlay text on video
        # result.write_videofile(title, fps=25)  # Many options...
        result.write_videofile(title, codec='libx264', audio_codec="aac")
        # result.write_videofile("movie1.mp4")  # default codec: 'libx264', 24 fps
        # result.write_videofile("movie2.mp4", fps=15)
        # result.write_videofile("movie3.webm")  # webm format

        return title

    @staticmethod
    def video_downloader(video_url: str):
        ydl_opts = {'outtmpl': 'video%(id)s.%(ext)s'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(
                video_url, download=True)
            video = ydl.prepare_filename(meta)
        # video = passage(video.split('.')[0], 'video')
        print(video)
        return video
