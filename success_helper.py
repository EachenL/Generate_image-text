import os

class success_helper:
    '''
    save the success parted srt file to success_file_record.txt with chatgpt to avoid repeat process same srt file.
    his class is a helper class to operate the success_file_record.txt.
    '''
    def __init__(self, success_file_record):
        self.success_file_record = success_file_record
        if not os.path.exists(self.success_file_record):
            # create this file
            with open(self.success_file_record, 'w') as f:
                pass
        self.success_list = []
    
    def get_success_list(self):
        if os.path.exists(self.success_file_record):
            with open(self.success_file_record, 'r') as f:
                self.success_list = f.readlines()
                self.success_list = [line.strip() for line in self.success_list]
        return self.success_list

    def add_success_file(self, success_file):
        with open(self.success_file_record, 'a') as f:
            f.write(success_file)
            f.write('\n')
    
# helper = success_helper('success_file_record.txt')
# helper.add_success_file('test.txt')
# helper.add_success_file('test2.txt')
# helper.add_success_file('test3.txt')
# helper.get_success_list()
# a=1