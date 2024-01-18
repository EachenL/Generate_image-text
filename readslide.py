import os
if hasattr(os, 'add_dll_directory'):
    # Python >= 3.8 on Windows
    with os.add_dll_directory(os.getenv('OPENSLIDE_PATH')):
        import openslide
else:
    import openslide
import shutil
class SlideReader:
    def __init__(self, file_path):
        self.slidefile = file_path
        self.file_dir, self.filename = os.path.split(file_path)
        self.tempslide = os.path.join(self.file_dir, 'temp.ndpi')
        os.rename(file_path, self.tempslide)
        try:
            self.slide = openslide.OpenSlide(self.tempslide)
        except:
            os.rename(self.tempslide, file_path)
        os.rename(self.tempslide, file_path)
# p = openslide.OpenSlide(r'D:\slidedata\1-50\02585_1_SCC_1.ndpi')