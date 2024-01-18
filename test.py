import json
import sys
import os
sys.path.append('..')
import chardet
# from EPRReaderPY.src.epr_reader.bindings.easy_pathology_record import EasyPathologyRecord
# from EPRReaderPY.src.epr_reader import read_epr
from epr_reader import read_epr
# from epr_reader.bindings.easy_pathology_record import EasyPahtologyRecord
if hasattr(os, 'add_dll_directory'):
    # Python >= 3.8 on Windows
    with os.add_dll_directory(os.getenv('OPENSLIDE_PATH')):
        import openslide
else:
    import openslide
openslide.__version__
openslide.__library_version__
from readslide import SlideReader
epr_reader = read_epr()

# import openslide
if __name__ == "__main__":
    epr_folder = r'/home/omnisky/nsd/miaoyuan_all'
    error_epr = []
    error_slide = []
    # 测试epr文件是否能正常读取，以及epr读取服务器是否正常运行
    for root, dir, files in os.walk(epr_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.splitext(file_path)[1] == '.epr':
                try:
                    epr = epr_reader.read(file_path)
                except:
                    error_epr.append(file_path)
    # 测试ndpi文件是否能正常读取
    # for root, dir, files in os.walk(epr_folder):
    #     for file in files:
    #         file_path = os.path.join(root, file)
    #         if os.path.splitext(file_path)[1] == '.ndpi': 
    #             try:
    #                 slide = openslide.OpenSlide(file_path)
    #                 # slide = SlideReader(file_path).slide
                    
    #             except:
    #                 error_slide.append(file_path)
    # 测试文件名编码  
    # for root, dir, files in os.walk(epr_folder):
    #     for file in files:
    #         file_path = os.path.join(root, file)
    #         if os.path.splitext(file_path)[1] == '.ndpi':
    #             # 查看文件名编码
    #             filename = file_path
    #             with open(filename, 'rb') as f:
    #                 data = f.read()
    #                 encoding = chardet.detect(data)['encoding']
    #             print('The encoding of the filename is:', encoding)
            
                         
    with open(r'..\samples\吴泽教学视频_1532677.json', encoding='utf-8') as f:
        epr_dict = json.load(f)['data']
        epr = EasyPathologyRecord(**epr_dict)
        print(epr)
