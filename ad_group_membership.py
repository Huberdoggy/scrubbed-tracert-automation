import os
import re


def gpresults_generation():
    file_name = f"{os.getcwd()}\\gpresults.txt"
    command = f"gpresult /R >{file_name} 2>&1"
    try:
        if not os.path.exists(file_name):
            print("Generating group policy output file in current direcory\nPlease wait...")
            os.system(command)
        else:
            print("Group policy output file already exists\n")
        return file_name
    except Exception as e:
        print(e)


def search_ad_groups(rsop_file):
    match_lst = []
    search_str = re.compile(r"^(\s+)?ca{2}\.[dv]{2}\d\.wan.*$")  # check if user is a part of caa.dv2.wan.xr/xe.read groups
    with open(rsop_file, "r") as f:
        for line in f.readlines():
            line = str(line).strip()
            if re.fullmatch(search_str, line):
                match_lst.append(line)
            else:
                continue
    return [match_lst, search_str]


def determine_membership(group_lst, reg_pat):
    count = 0
    if len(group_lst) > 0:
        for group in group_lst:
            if re.search(reg_pat, group):
                count += 1
        return count
    return False
