import sys
sys.path.append('..')
import srt
from EPRReaderPY.src.epr_reader import read_epr
# timestamp should multiply 100 times // OK
# The path can also be read from a config file, etc.
# OPENSLIDE_PATH = r'D:\openslide-win64-20230414\bin'
import codecs
import chardet
import os
import cv2
if hasattr(os, 'add_dll_directory'):
    # Python >= 3.8 on Windows
    with os.add_dll_directory(os.getenv('OPENSLIDE_PATH')):
        import openslide
else:
    import openslide
import traceback
from .error import *
from PIL import Image
import numpy as np
import Generate_book.read_srt as read_srt
import json
# import hdbscan
# from epr_reader import read_epr # for install mode
# epr_reader = read_epr() 
# epr_file = '../1-4-2/1-4-2_肝细胞坏死__-_40x.epr'
# srt_file = '../1-4-2/1-4-2_肝细胞坏死__-_40x.srt'
# slide_file = '../1-4-2/1-4-2_肝细胞坏死__-_40x.ndpi'
picture_mode = 'fixation'
# img_folder = f'../1-4-2/1-4-2_肝细胞坏死__-_40x-img-{picture_mode}'

def change_codec(file):
    # 检测原始文件的编码类型
    with open(file, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        print(encoding)

    # 如果编码类型为GBK，则进行编码转换
    if encoding == 'GBK':
        with codecs.open(file, 'r', encoding='gbk') as f_in:
            with codecs.open(file, 'w', encoding='utf-8') as f_out:
                # 逐行读取原始文件内容，并以UTF-8编码写入目标文件
                for line in f_in:
                    f_out.write(line)

        print("文件编码转换完成。")
    else:
        print("文件编码不是GBK，无需转换。")
        

class srt_md_unit():
    def __init__(self, index, start, end, content, img_path):
        self.index = index
        self.start = start
        self.end = end
        self.content = content
        self.img_path = img_path

# def get_focus_by_HDBSCAN(xy, l):
#     cluster = hdbscan.HDBSCAN(min_cluster_size=10)
    
#     cluster_labels = cluster.fit_predict(xy)
    
#     return
def get_roi_imgs(roi_list, slide, minlevel):
    square_points = []
    for roi in roi_list:
        x, y, r, level = roi['x'], roi['y'], roi['radius'], roi['level']
        square = [x-r, y-r, x+r, y+r, level - minlevel]
        square_points.append(square)
    # get biggest level, and normalize list to the maxmium level
    # maxmium_level = max(square_points[:,4])
    maxmium_level = max(point[4] for point in square_points)
    for box in square_points:
        if box[4] != maxmium_level:
            difference = box[4]-maxmium_level
            # we remap the lower level points to highest level
            box[0:4] = list(map(lambda x: x * (2**difference), box[0:4]))        
    
    # 得到图像区域，最小左上角点，以及最大右下角点
    square_points = np.array(square_points).astype(int)
    left_up_point = (min(square_points[:,0]), min(square_points[:,1]))
    right_down_point = (max(square_points[:,2]), max(square_points[:,3]))
    width = right_down_point[0] - left_up_point[0]
    height = right_down_point[1] - left_up_point[1]
    # 得到关注区域背景图像
    background_img = slide.read_region(left_up_point, int(maxmium_level), (width, height))
    # 将roilist转换成已背景图像被标准的坐标
    for roi in roi_list:
        # 转换roi坐标
        roi['level'] = roi['level'] - minlevel
        roi['x'] = roi['x']* (2 ** (roi['level']-maxmium_level)) - left_up_point[0]
        roi['y'] = roi['y']* (2 ** (roi['level']-maxmium_level)) - left_up_point[1]
        roi['radius'] = roi['radius'] * (2 ** (roi['level']-maxmium_level))
        
    # 得到关注区域掩码图像
    # 在掩码图像中将ROI区域填充为白色
    mask = np.zeros((width, height), dtype=np.uint8)
    mask = np.array(mask, dtype=np.uint8)
    for roi in roi_list:
        center_x, center_y, radius = int(roi['x']), int(roi['y']), int(roi['radius'])
        cv2.circle(mask, (center_x, center_y), radius, 255, -1)
    background_img = np.array(background_img)
    # 生成roi区域图像
    if mask.shape[:2] != background_img.shape[:2]:
        mask = cv2.resize(mask, (background_img.shape[1], background_img.shape[0]))
    roi_img = cv2.bitwise_and(background_img, background_img, mask=mask)
    # 生成除了roi区域的图像
    back_img_without_roi = cv2.bitwise_and(background_img, background_img, mask=~mask)
    # 降低back_img_without_roi的亮度
    back_img_without_roi = cv2.addWeighted(back_img_without_roi, 0.5, np.zeros_like((back_img_without_roi), dtype=np.uint8), 0.5, 0)
    # 融合roi_img和back_img_without_roi生成最终图像
    final_img = cv2.add(roi_img, back_img_without_roi)
    background_img = Image.fromarray(background_img)
    final_img = Image.fromarray(final_img)
    return background_img, final_img
        
def get_roi_list(start, end, epr):
    roilist = []
    Roi_List = epr.additionalInfoSet["roiList"]
    for roi in Roi_List:
        if roi["beginFrameIndex"] > start and roi["beginFrameIndex"] < end:
            roilist.append(roi)
    return roilist
# define a function that can get the image by timestamp
def get_window_by_fixation(datum, epr, slide):
    '''
    return a list [x, y, level]
    x, y is the coordinate of the eye position, then scale to the level 0
    level, is the scale-level of the eye position before scale
    '''
    X0 = -datum.screenX + datum.eyeX
    Y0 = -datum.screenY + datum.eyeY
    level = datum.level - epr.minlevel
    drop_flag = False

    if level < 0:
        a = 1
    if X0 < 0:
        drop_flag = True
        X0 = 0

    if Y0 < 0:
        drop_flag = True
        Y0 = 0


    if X0 > slide.level_dimensions[level][0]:
        drop_flag = True
        X0 = slide.level_dimensions[level][0]
   
    if Y0 > slide.level_dimensions[level][1]:
        drop_flag = True
        Y0 = slide.level_dimensions[level][1]
    
    

    level_window = [X0, Y0]    
    level_window = np.array(level_window)
    level0_window = list(level_window * (2 ** level))
    level0_window.append(level)
    return level0_window, drop_flag

def find_prop_window(level0_windows, mode, minlevel):
    
    arr = np.array(level0_windows)
    max = np.max(arr, axis = 0)
    max_index = arr.argmax(axis=0)
    min = np.min(arr, axis = 0)
    min_index = arr.argmin(axis=0)
    if mode == 'screen_path':
        
        x, y, w, h = min[0], min[1], max[2]-min[0], max[3]-min[1]
        # read the image from the slide in level 0
        level = arr[max_index[4]][4]
        return x, y, w, h, level
    
    if mode == 'fixation':
        x, y, w, h = min[0], min[1], max[0]-min[0], max[1]-min[1]
        # read the image from the slide in level 0
        level = arr[max_index[2]][2]
        return x, y, w, h, level

def get_window_by_screenpath(datum, epr, slide):
    X0 = datum.screenX
    Y0 = datum.screenY
    level = datum.level - epr.minlevel
    
    if level < 0:
        a = 1
    if X0 > 0:
        X0 = 0
    else:
        X0 = -X0
    if Y0 > 0:
        Y0 = 0
    else:
        Y0 = -Y0
    width = epr.screenPixelWidth
    height = epr.screenPixelHeight
    if X0 + epr.screenPixelWidth > slide.level_dimensions[level][0]:
        
        width = slide.level_dimensions[level][0] - X0
        # if slide.level_dimensions[level][0] - screenPixelWidth < 0 :
            
        
    if Y0 + epr.screenPixelHeight > slide.level_dimensions[level][1]:
        height = slide.level_dimensions[level][1] - Y0
        # if slide.level_dimensions[level][1] - screenPixelHeight < 0:
            
    
    X1, Y1 = X0 + width, Y0 + height
    level_window = [X0, Y0, X1, Y1]    
    level_window = np.array(level_window)
    level0_window = list(level_window * (2 ** level))
    level0_window.append(level)
    return level0_window



class srt_datumn():
    def __init__(self, x0, y0, width, height, x1, y1, level):
        self.level_window = [[x0, y0], [x1, y1]]
        self.width, self.height = width, height
        self.level = level
        self.level0_window = self.level_window * (level+1)
        

def get_part_start_end_time(part, srt_content):
    
    start_index, end_index = part['index_range'].split('-')
    start_index, end_index = int(start_index)-1, int(end_index)-1
    # srt_content = list(srt_content)
    start_time = srt_content[start_index].start.seconds*1000 + srt_content[start_index].start.microseconds/1000
    end_time = srt_content[end_index].end.seconds*1000 + srt_content[end_index].end.microseconds/1000
    return start_time, end_time

def generate_target_picture(roi_list, part, slide, img_folder, minlevel):
    img_name = str(part['index_range']) + '.png'
    img_path = os.path.join(img_folder, img_name)
    # get roi_list occupy img, and hot img
    back_img, roi_img = get_roi_imgs(roi_list, slide, minlevel)
    back_img.save(img_path, 'PNG')
    roi_img.save(os.path.join(img_folder, "roi_"+img_name), 'PNG')
    back_img.close()
    roi_img.close()
    a = 1
    
def write_part_list_to_file(part_list, json_file):
    with open(json_file, "w") as outfile:
        json.dump(part_list, outfile)
    return

def gen_partlist_by_srt(img_folder, srt_file):
    srt_content = srt.parse(open(srt_file, 'r', encoding='utf-8-sig'))
    srt_content = list(srt_content)
    # check img_folder is exist, if not, create it
    if not os.path.exists(img_folder):
        os.mkdir(img_folder)
    start_end_list = []
    while flag == False:
        try:
            part_list = read_srt.get_final_text(srt_file)
            write_part_list_to_file(part_list, os.path.join(img_folder, 'part_list.json'))
            # get start and end list
            for part in part_list:
                start_time, end_time = get_part_start_end_time(part, srt_content)
                start_end_list.append([start_time, end_time])
            flag = True
            print('get start and end list success')
        except:
            start_end_list = []
            print('get start and end list failed, try to regenerate')
            continue

def gen_part_pic(epr_file, srt_file, img_folder, slide_file, part_list):
    try:
        epr_reader = read_epr()
        epr = epr_reader.read(epr_file)
    except:
        raise Epr_Error('epr open failed')

    srt_content = srt.parse(open(srt_file, 'r', encoding='utf-8-sig'))
    srt_content = list(srt_content)
    # check img_folder is exist, if not, create it
    if not os.path.exists(img_folder):
        os.mkdir(img_folder)
        
    epr_pointer = 0

    try:
        slide = openslide.OpenSlide(slide_file)
    except:
        raise Slide_Error('slide open failed')
      
    
    for part in part_list:
        roi_list = []
        start_time = part['start_time']
        end_time = part['end_time']
        while epr_pointer < len(epr.rawDataFrames)-1 and epr.rawDataFrames[epr_pointer]['timeStamp'] * 1000 <= start_time:
            epr_pointer += 1
        start_pointer = epr_pointer
        while epr_pointer < len(epr.rawDataFrames)-1 and epr.rawDataFrames[epr_pointer]['timeStamp'] * 1000 <= end_time:
            epr_pointer += 1
        end_pointer = epr_pointer
        roi_list = get_roi_list(start_pointer, end_pointer, epr)
        generate_target_picture(roi_list, part, slide, img_folder, epr.minLevel)
    
    return part_list, srt_content

def write_content_to_md(img_dir, srt_content, part_list, name, img_folder):
    md_file = os.path.join(img_dir, (os.path.basename(img_dir) + '.md'))
    with open(md_file, 'a') as f:
        # write file name:
        total_content = ''
        total_content += f'#  {name}\n\n'

        for part in part_list:
            content = ''
            # write part of a file
            content += f"##  {part['title']}\n\n"
            # write re-content
            content += f"{part['re_content']}\n"
            # add background pic
            content += f"![{part['index_range']}]({img_folder}/{part['index_range']}.png)\n"
            # add roi pic
            content += f"![{part['index_range']}]({img_folder}/roi_{part['index_range']}.png)\n"
            # write part picture
            total_content += content
        f.write(total_content)
        
def read_partlist_from_json(json_file):
    with open(json_file) as f:
        data = json.load(f)
    return data

def read_srt_content(srt_file):
    srt_content = srt.parse(open(srt_file, 'r', encoding='utf-8-sig'))
    srt_content = list(srt_content)
    return srt_content
    
def gen_md_by_dir(rec_dir, img_dir):
    # traverse record directory to find epr, slide, srt to generate final file
    for root, dirs, files in os.walk(rec_dir):
        epr_file = ''
        srt_file = ''
        img_folder = img_dir
        img_folder = os.path.join(img_folder, os.path.basename(os.path.normpath(root)))
        slide_file = ''
        # get files we need
        for file in files:
            ext = file.split('.')[1]
            name = file.split('.')[0]
            if ext == 'epr':
                epr_file = os.path.join(root, file)
            elif ext == 'ndpi':
                slide_file = os.path.join(root, file)
            elif ext == 'srt':
                srt_file = os.path.join(root, file)
            else:
                continue
        # excute mission
        json_file = os.path.join(img_dir, name+'/part_list.json')
        flag = False
        times = 3
        if epr_file != '' and slide_file != '' and srt_file != '' and os.path.exists(json_file):
            # file deprecate flag, while the epr, slide, srt is error, than jump to the next file folder
            while flag == False and times > 0:
                try: 
                    # json_file = os.path.join(img_folder, 'part_list.json')
                    # json_file = os.path.join(img_dir, '2022年4月26日_1/part_list.json') # for test
                    part_list = read_partlist_from_json(json_file)
                    srt_content = read_srt_content(srt_file)
                    gen_part_pic(epr_file, srt_file, img_folder, slide_file, part_list)
                    
                    write_content_to_md(img_dir, srt_content, part_list, name, os.path.basename(os.path.normpath(root)))
                    flag = True
                except Slide_Error:
                    times -= 1
                    print('slide open failed')
                    break
                except Epr_Error:
                    times -= 1
                    print('epr open failed')
                    break
                except Exception:
                    times -= 1
                    print(traceback.format_exc())
                    continue
                
def gen_book(rec_dir, project_name):
    rec_dir = rec_dir
    project_name = project_name
    img_folder = os.path.join(rec_dir, project_name)
    if not os.path.exists(img_folder):
        os.mkdir(img_folder)
    gen_md_by_dir(rec_dir, img_folder)
            
            

# if __name__ == '__main__':
#     # record directory
#     rec_dir = r'/home/omnisky/nsd/miaoyuan_all'
#     project_name = 'miaoyuan_lession'
#     img_folder = os.path.join(rec_dir, project_name)
#     # create project folder
#     if not os.path.exists(img_folder):
#         os.mkdir(img_folder)
#     # generate
    
#     # read_srt.gen_partlist(rec_dir, img_folder)
#     gen_md_by_dir(rec_dir, img_folder)