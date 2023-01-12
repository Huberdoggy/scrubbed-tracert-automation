import os
import re
from secrets import password as prem_pass
from secrets import username as prem_username
from time import sleep

import paramiko
from banner import banner_motd

from ad_group_membership import (determine_membership, gpresults_generation,
                                 search_ad_groups)
from common import ete_hosts  # For just the filtered hostnames
from common import ite_hosts  # For just the filtered hostnames
from common import clear
from common import ete_gws_dict as ete_gws
from common import ite_gws_dict as ite_gws
from common import routers

increment = 3

# what I use based on verbose output from SSH connection
conf_file_opts = [
    "Host 192.168.237.*",
    "\n  KexAlgorithms=+diffie-hellman-group14-sha1",
    "\n  HostKeyAlgorithms=+ssh-rsa",
]


def check_conf_file(filepath):
    if os.path.isfile(filepath):
        return True
    else:
        return False


def write_conf_file(filename, opts=conf_file_opts):
    with open(filename, "w") as f:
        f.writelines(opts)
        f.close()


def validate_input(**data):
    digit_str = r"\d{1,2}"
    try:
        digit_regex = re.compile(digit_str)
        for v in data.values():
            if re.fullmatch(digit_regex, v) and int(v) in range(1, 31):
                continue
            else:
                return False
        return True
    except Exception as e:
        print(e)


def set_params():
    while True:
        timeout = input("Specify the default timeout: ")
        min_ttl = input("Specify minimum number of hops: ")
        max_ttl = input("Specify max number of hops: ")
        check = validate_input(timeout=timeout, min_ttl=min_ttl, max_ttl=max_ttl)
        if check:
            return [timeout, min_ttl, max_ttl]
        else:
            clear()
            print("INVALID INPUT")
            print("Please enter only digits")
            print("Additionally, min hops >= 1 and max hops <= 30")


def rm_old_logs(logfile1="<internal_router_1>_traces.txt", logfile2="<internal_router_2>_traces.txt"):
    # Check if we already have tracelogs in curr directory from previous run
    # AND condition will throw error if non-existent, so enclose in nested try block
    clear()
    sleep(increment)
    arg_c = locals()
    for key in arg_c.keys():
        try:
            if os.path.exists(arg_c[key] and os.stat(arg_c[key]).st_size > 0):
                print(f"\nDetected existing file {arg_c[key]}.\nWill remove to generate a fresh log this run.")
                try:
                    os.remove(arg_c[key])
                except IOError:
                    print(f"\nIt appears {arg_c[key]} is open. Skipping removal..")
        except FileNotFoundError:
            print(f"\n\nNew log will be saved at: {os.getcwd()}/{arg_c[key]}.")
            continue
    sleep(increment + 4)
    clear()
    print("\n" * 5 + "\t\tPlease wait..")


def open_channel(count, gw_dict, timeout, min_ttl, max_ttl, **kwargs):
    router_name = kwargs["router_name"]  # because we passed explicit override
    host_names = ete_hosts if "next_controller" in kwargs.keys() else ite_hosts
    curr_dir = os.getcwd()
    output_file = f"{curr_dir}/{router_name}_traces.txt"
    ip = routers[router_name]["ip"]
    port = routers[router_name]["port"]
    ssh = paramiko.SSHClient()  # instantiate an instance
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # incase it's not already in known_host, prevents error
    ssh.connect(
        hostname=ip, username=prem_username, port=int(port), password=prem_pass, look_for_keys=False
    )  # Must set 'look_for_keys' false to force Paramiko to use script creds
    try:
        gw_ip = gw_dict[host_names[count]][0]  # Equates to the dict GW's IP, for each iteration (ie. azr-usga-ite-dv2*)
        remote_command = f"trace ip {gw_ip} timeout {timeout} ttl {min_ttl} {max_ttl}"
        stdin, stdout, stderr = ssh.exec_command(remote_command)
        trace_output = stdout.readlines()

        with open(output_file, "a+") as f:
            if host_names == ete_hosts and count == 0:
                f.write(" BEGIN ETE ".center(140, "*") + "\n\n")
            elif count > 0 and count <= len(list(gw_dict)) - 1:
                f.write("Next Gateway".upper() + "\n\n")
            f.write(f"HOSTNAME: {host_names[count].upper()}")
            for line in trace_output:
                f.write(str(line))
            f.write("\n" * 4)
    except paramiko.SSHException as e:
        print(e)
    return output_file


def run_loop(gw_dict, timeout, min_ttl, max_ttl, **kwargs):
    # My sloppy solution since parimiko cant sustain
    # socket keep alive long enough for full iteration in 1 session
    router_name = ""
    next_controller = ""
    router_name = kwargs["router_name"]  # unpack the name passed in from keyword args
    if "next_controller" in kwargs.keys():
        next_controller = kwargs["next_controller"]
    i = 0
    while i < len(list(gw_dict)):
        if router_name and next_controller:
            open_channel(
                i,
                gw_dict,
                timeout,
                min_ttl,
                max_ttl,
                router_name=router_name,
                next_controller=next_controller,  # pass both keyword args
            )
            sleep(increment)
            i += 1
        elif router_name and not next_controller:
            open_channel(
                i, gw_dict, timeout, min_ttl, max_ttl, router_name=router_name  # pass only keyword arg for "router_name"
            )  # switch router, but stay on current controller
            sleep(increment)
            i += 1
    return True


def filter_banner(text, filename):
    replace = ""
    with open(f"{filename}", "r") as f:
        data = f.read()
        data = data.replace(text, replace)

    with open(f"{filename}", "w") as f:
        f.write(data)
    return filename


def tracert_main():
    username = os.getenv("USERNAME")
    clear()
    print(f"Welcome {username}")
    sleep(increment)
    clear()
    pol_file = gpresults_generation()
    user_groups, pattern = search_ad_groups(pol_file)
    xr_xe = determine_membership(user_groups, pattern)
    if xr_xe and xr_xe == 2:
        print(
            f"{username} belongs to AD groups {str(user_groups[0]).upper()} and {str(user_groups[1]).upper()}"
            "\nClear to proceed..."
        )
    else:
        print(f"Cannot run Python script. {username} does not belong to the appropriate AD groups.")
        return

    home = os.getenv("HOME")
    ssh_config_file = ".ssh/config"
    conf_path = f"{home}/{ssh_config_file}"
    does_exist = check_conf_file(conf_path)
    if does_exist:
        print(f"""SSH config file exists for {username}\nCreating a backup under {home}/.ssh\n""")
        os.system(f"cp {conf_path} {home}/.ssh/config.bkp")
    else:
        print("Could not find existing SSH config file.")
        print("Will make it with appropriate opts.")
        filename = conf_path
        if not os.path.exists(f"{home}/.ssh"):
            print("No parent directory exists for system SSH configurations. Creating..")
            dir_command = os.mkdir(f"{home}/.ssh")
            os.system(dir_command)
        os.system(f"touch {filename}")
        write_conf_file(filename)

    # Unpack the returned list
    timeout, min_ttl, max_ttl = set_params()

    rm_old_logs()
    first_pass = run_loop(ite_gws, timeout, min_ttl, max_ttl, router_name="<internal_router_1>")
    second_pass = run_loop(ite_gws, timeout, min_ttl, max_ttl, router_name="<internal_router_2>")
    if first_pass and second_pass:
        run_loop(ete_gws, timeout, min_ttl, max_ttl, router_name="<internal_router_1>", next_controller="Y")
        run_loop(ete_gws, timeout, min_ttl, max_ttl, router_name="<internal_router_2>", next_controller="Y")
    filter_banner(banner_motd, "<internal_router_1>_traces.txt")
    filter_banner(banner_motd, "<internal_router_2>_traces.txt")
    print("Log generation complete!\nNow returning to main menu...")
    sleep(increment)
    return True  # Back to main menu


if __name__ == "__main__":
    print("In tracert.py")
    # main()  # Allow direct run module during testing
