from os import name, system

# This file contained internally relevant nested dictionaries mapping router objects & hostnames to IP's

ite_hosts = [key for key in ite_gws_dict]  # assignment trick to convert top lvl dict strs to lst
# with inner nested list of their corresponding IPs
# For easier mix 'n matching later during iteration and writing info to the files
ete_hosts = [key for key in ete_gws_dict]


def clear():
    if name == "nt":
        _ = system("cls")
    else:
        _ = system("clear")
