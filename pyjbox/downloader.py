import requests, sys, timeit, threading, os, time, queue, json, socket
from pyjbox.terminal_size import get_terminal_size

from datetime import timedelta

last_state = [0, timeit.default_timer()]
speed = 0

downloaded_size = 0
lock = threading.Lock()

active_threads = 0

def update_downloaded_size(delta):
    global downloaded_size
    downloaded_size += delta

def task_finish():
    global active_threads
    active_threads -= 1

class DownloadManager:
    def __init__(self, file_id, link, file_name, file_size, connections=4, timeout=5):
        self.file_id, self.link, self.file_name, self.file_size, self.connections, self.timeout = file_id, link, file_name, file_size, connections, timeout
        # print('File size: %s' % self.file_size)

    def start_download(self):
        global active_threads

        self.threads = []
        self.stopper = threading.Event()
        self.network_error = threading.Event()

        self.interrupt_queue = queue.Queue()

        monitor_thread = DownloadMonitor(self.file_name, self.file_size, self.connections, self.stopper, self.network_error)
        monitor_thread.start()
        self.threads.append(monitor_thread)

        if not os.path.exists(self.file_name):
            f = open(self.file_name, 'w')
            f.close()

        if os.path.exists("%s.downloading" % self.file_id):
            f = open("%s.downloading" % self.file_id, 'r')
            downloading = json.loads(f.read())
            global last_state, downloaded_size
            downloaded_size = self.file_size + 1

            for t in downloading['threads']:
                downloaded_size -= (t['unfinished_bytes'][1] - t['unfinished_bytes'][0] + 1)
                thread = Downloader(self.link, t['part_id'], self.file_name, t['unfinished_bytes'][0], t['unfinished_bytes'][1], self.stopper,
                                    self.interrupt_queue, self.network_error, self.timeout)
                thread.start()
                self.threads.append(thread)
                active_threads += 1

            last_state = [downloaded_size, timeit.default_timer()]
            f.close()

        else:
            # 创建新线程
            active_threads = self.connections

            for thread_id in range(self.connections):
                start_byte = thread_id * int(self.file_size / self.connections)

                if thread_id == self.connections - 1:
                    end_byte = self.file_size
                else:
                    end_byte = (thread_id + 1) * int(self.file_size / self.connections) - 1

                thread = Downloader(self.link, thread_id, self.file_name, start_byte, end_byte, self.stopper, self.interrupt_queue, self.network_error, self.timeout)
                thread.start()
                self.threads.append(thread)

        for t in self.threads:
            t.join()

        if self.network_error.is_set():
            self.write_status_file()
            return False

        if os.path.exists("%s.downloading" % self.file_id): os.remove("%s.downloading" % self.file_id)
        return True

    def write_status_file(self):
        interrupt_list = list()
        for thread in range(active_threads):
            interrupt_list.append(self.interrupt_queue.get())

        f = open("%s.downloading" % self.file_id, 'w')
        f.write(json.dumps({
            'file': {
                'name': self.file_name,
                'url': self.link,
                'size': self.file_size
            },
            'threads': interrupt_list
        }))
        f.close()

    def signal_handler(self, sig, frame):
        self.stopper.set()
        self.write_status_file()

        sys.exit(0)

class DownloadMonitor(threading.Thread):
    def __init__(self, file_name, file_size, connections, stopper, network_error):
        super().__init__()
        self.file_name, self.file_size, self.connections, self.stopper, self.network_error = file_name, file_size, connections, stopper, network_error

    def run(self):
        print("Downloading %s:" % self.file_name)
        sizex, sizey = get_terminal_size()
        progress_bar_width = sizex - 60

        while True:
            global last_state, downloaded_size

            speed = (downloaded_size - last_state[0]) / (timeit.default_timer() - last_state[1]) / 1024 / 1024
            last_state = [downloaded_size, timeit.default_timer()]
            done = int(progress_bar_width * downloaded_size / self.file_size)

            if speed == 0:
                eta = '∞'
            else:
                delta = timedelta(seconds=(self.file_size - downloaded_size) / (speed * 1024 * 1024))
                eta = delta - timedelta(microseconds=delta.microseconds)

            sys.stdout.write("\r%.2f MB/s [%s>%s] %.2f%% [%s/%s Connections] [ETA: %s]" %
                             (speed, '=' * (done - 1), ' ' * (progress_bar_width - done),
                              downloaded_size / self.file_size * 100, active_threads, self.connections,
                              eta))
            sys.stdout.flush()

            time.sleep(1)
            if done >= progress_bar_width:
                print()
                break

            if self.stopper.is_set():
                print('\nDownload interrupted!')
                break

            if self.network_error.is_set():
                print('\nNetwork Error!')
                break

class Downloader(threading.Thread):
    def __init__(self, link, part_id, file_name, start_byte, end_byte, stopper, interrupt_queue, network_error, timeout):
        super().__init__()
        self.link, self.part_id, self.file_name, self.start_byte, self.end_byte, self.stopper, self.interrupt_queue, self.network_error, self.timeout\
            = link, part_id, file_name, start_byte, end_byte, stopper, interrupt_queue, network_error, timeout

        self.current_bytes = start_byte

    def return_status(self):
        self.interrupt_queue.put({
            'part_id': self.part_id,
            'unfinished_bytes': (self.current_bytes, self.end_byte)
        })

    def run(self):
        if self.start_byte >= self.end_byte: return

        headers = {
            'Range': 'bytes=%s-%s' % (self.start_byte, self.end_byte)
        }

        with open(self.file_name, "rb+") as f:
            f.seek(self.start_byte)

            with requests.get(self.link, headers=headers, stream=True, timeout=self.timeout) as response:
                try:
                    for data in response.iter_content(chunk_size=4096):
                        self.current_bytes += len(data)

                        lock.acquire()
                        try:
                            update_downloaded_size(len(data))
                        finally:
                            lock.release()

                        f.write(data)

                        if self.stopper.is_set():
                            self.return_status()
                            break

                    f.close()

                    lock.acquire()
                    try:
                        task_finish()
                    finally:
                        lock.release()


                except requests.exceptions.ConnectionError:
                    # print('Timeout!')
                    self.return_status()
                    self.network_error.set()

        # print('\nPart #%s finished! Downloaded: %s' % (self.part_id, downloaded_size))