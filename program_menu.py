import re
import sys
from os import name, system
from time import sleep

from pyfiglet import Figlet

from browser_nav import main as browser_nav_main
from tracert import tracert_main

menu_options = [
    "Run traces over SSH to cloud from prem routers",
    "Run GUI traces from hosts in Aviatrix controllers",
    "Quit",
]
int_menu_pattern = re.compile(r"^[1-3]{1}$")
valid_input = False


def clear():
    if name == "nt":
        _ = system("cls")
    else:
        _ = system("clear")


def make_menu(lst):
    menu_dict = {}
    for i in range(len(lst)):
        menu_dict[i + 1] = lst[i]
    return menu_dict


def format_main_menu(menu_dict, header="Traceroute automation".upper()):
    f = Figlet(font="standard", justify="center")
    print(f"{f.renderText(header)}\n")
    print("\tPlease enter a number corresponding to one of the following:\n")
    print("\t" * 3 + ("*" * 30))
    for key in menu_dict:
        print("\t" * 3 + str(key) + " - " + menu_dict[key])
    print("\t" * 3 + ("*" * 30))


def determine_module(choice):
    if choice == 1:
        module = tracert_main()
    elif choice == 2:
        module = browser_nav_main()
    else:
        return
    return module


menu_dict = make_menu(menu_options)
while not valid_input:
    clear()
    format_main_menu(menu_dict)
    choice = input("=> ").strip()
    if re.fullmatch(int_menu_pattern, choice):
        keep_running = determine_module(int(choice))
        if keep_running is None:  # I'm not returning custom val, so default will be to end the program.
            print("Okay, thank you. Good bye!")
            sys.exit(0)
    else:
        clear()
        print("Invalid input\nPlease enter a number correspoding to one of the given options.")
    sleep(3)
