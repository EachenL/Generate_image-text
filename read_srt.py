import srt
import openai
from .use_openai import ChatGPT
import json
import os
import traceback
from .success_helper import success_helper
chatbot = ChatGPT()
suc_helper = success_helper('/home/omnisky/nsd/miaoyuan_all/success_file_record.txt')

def get_part_start_end_time(part, srt_content):
    
    start_index, end_index = part['index_range'].split('-')
    start_index, end_index = int(start_index)-1, int(end_index)-1
    # srt_content = list(srt_content)
    start_time = srt_content[start_index].start.seconds*1000 + srt_content[start_index].start.microseconds/1000
    end_time = srt_content[end_index].end.seconds*1000 + srt_content[end_index].end.microseconds/1000
    return start_time, end_time, start_index, end_index

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
    flag = False
    times = 3
    while flag == False and times > 0:
        try:
            part_list = get_final_text(srt_file)
            # get start and end list
            for part in part_list:
                start_time, end_time, start_index, end_index = get_part_start_end_time(part, srt_content)
            print('part_list check success')    
            for part in part_list:
                content = []
                start_time, end_time, start_index, end_index = get_part_start_end_time(part, srt_content)
                start_end_list.append([start_time, end_time])
                part['start_time'] = start_time
                part['end_time'] = end_time
                for i in range(start_index, end_index - 1):
                    content += srt_content[i].content + ','
                content += srt_content[end_index].content + '。\n'
                part['re_content'] = deal_srt_content(content)
                                
            write_part_list_to_file(part_list, os.path.join(img_folder, 'part_list.json'))
            suc_helper.add_success_file(srt_file)
            flag = True
            print('get start and end list success')
        except:
            start_end_list = []
            print(traceback.format_exc())
            print(f'{srt_file} get start and end list failed, try to regenerate')
            times -= 1
            continue

def gen_partlist(record_folder, partlist_folder):
    for root, dir, files in os.walk(record_folder):
        for file in files:
            ext = file.split('.')[1]
            name = file.split('.')[0]
            if ext == 'srt':
                srt_file = os.path.join(root, file)
                if srt_file not in suc_helper.get_success_list():
                    gen_partlist_by_srt(os.path.join(partlist_folder, name), srt_file)
    

def deal_srt_content(content):
    chatbot.clear_memory()
    input = f"请将以下内容用尽可能书面的语言来重新描述：{content}"
    re = chatbot.chat(input)
    print(re)
    return re


def get_final_text(srtfile):
    '''
    读取srt文件，将其分成7至8个部分并为每个部分起一个标题, 并返回每部分的索引范围
    '''
    chatbot.clear_memory()
    srt_file = open(srtfile)
    srt_content = srt.parse(srt_file)
    
    # content = srt_file.readlines()
    content = ''
    for sub in srt_content:
        content += f'{sub.index}: {sub.content}\n'

    example = '例子为：\n\
    1. 肝脏组织结构及血管、管道的组成\n\
    索引范围：1-7\n\
    2. 汇管区和其中的管道结构\n\
    索引范围：9-13\n\
    3. 脂肪变性和细胞坏死的特征\n\
    索引范围：15-19'
    ins = '请以上述例子的格式, 根据以下文本内容将其分成7至8个部分, 并为每个部分起一个标题, 并返回每部分的索引范围, 且索引范围为一个连续的范围, 各部分的索引范围要求不重叠, 如果索引范围为1则弃用。内容为'
 
    input = f"{example}. {ins}: {content}"
    re = chatbot.chat(input)
    print(re)

    input = '用json的形式重新返回上述内容, 索引范围命名为index_range, index_range中的值用\'-\'隔开, 标题命名为title'
    # chatbot.clear_memory()
    
    re = chatbot.chat(input)
    try:
        part_list = json.loads(re)
        print(part_list)
    except:
        re = chatbot.chat(f'重新{input}')
        part_list = json.loads(re)
        print(part_list)

    # input = '请为所有文本内容起一个标题'
    # title = chatbot.chat(input)
    # print(title)
    return part_list

# for _ in range(10):
#     get_final_text('../1-4-2/1-4-2_肝细胞坏死__-_40x.srt')
#     chatbot.clear_memory()
if __name__ == '__main__':
    # record directory
    rec_dir = r'/home/omnisky/nsd/miaoyuan_all'
    project_name = 'miaoyuan_lession'
    img_folder = os.path.join(rec_dir, project_name)
    # create project folder
    if not os.path.exists(img_folder):
        os.mkdir(img_folder)
    # generate
    
    gen_partlist(rec_dir, img_folder)
    # gen_md_by_dir(rec_dir, img_folder)