import os
class TrackLogger:
    def __init__(self, file_path):
        self.logger_file = file_path
        self.f = open(file_path, mode="a", encoding="utf-8")
    
    def write(self, message:str):
        self.f.write(f"{message}\n")

    def reportToServer(backtestID:str):
        print("xxx")