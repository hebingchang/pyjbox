import requests, json
from pyjbox import downloader
import signal
from urllib.parse import unquote

class JboxShare:
    def __init__(self, url):
        self.file_id = self.shareUrlParser(url)

        r = requests.get("https://jbox.sjtu.edu.cn/v2/delivery/metadata/%s" % self.file_id)
        self.file_info = json.loads(r.content)

        self.download_url = self.file_info['download_url']
        self.file_size = self.file_info['bytes']

        r = requests.get(self.download_url, stream=True)
        self.file_name = unquote(r.headers['content-disposition'].split("''")[-1])

    def getFileIdFromShortUrl(self, short):
        r = requests.get(short, allow_redirects=False)
        file_id = r.headers['location'].split("/")[-1]
        return file_id

    def shareUrlParser(self, url):
        if '/' in url:
            file_id = url.split('/')[-1]
            if file_id == '': file_id = url.split('/')[-2]
        else:
            file_id = url

        if len(file_id) < 32:
            return self.getFileIdFromShortUrl("https://jbox.sjtu.edu.cn/l/" + file_id)
        else:
            return file_id

    def getFileInfo(self):
        return self.file_info

    def download(self, connections=4, timeout=5):
        manager = downloader.DownloadManager(self.file_id, self.download_url, self.file_name, self.file_size, connections, timeout)
        signal.signal(signal.SIGINT, manager.signal_handler)

        result = manager.start_download()
        return result
