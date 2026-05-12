import os
import hashlib

# BUF_SIZE is totally arbitrary, change for your app!
BUF_SIZE = 65536  # lets read stuff in 64kb chunks!


class FileManager:

    def __init__(self, shared_folder):
        self.shared_folder = shared_folder
        self.file_index = {}

        self.download_folder = f"{shared_folder}_downloads"
        os.makedirs(self.download_folder, exist_ok=True)

    def scan_files(self):
        self.file_index = {}
        with os.scandir(self.shared_folder) as d:
            for f in d:
                if f.is_file():
                    self.file_index[f.name] = {"filename" : f.name,
                                               "path": f.path,
                                               "size": os.path.getsize(f.path),
                                               "hash": self.compute_hash(f.path)}

    def list_files(self):
        return list(self.file_index.values())

    def has_file(self, filename):
        return filename in self.file_index

    def get_file_info(self, filename):
        return self.file_index.get(filename)

    def compute_hash(self, path):
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def get_download_path(self, filename):
        return os.path.join(self.download_folder, filename)
