import os
import tkinter as tk
# import re
from time import sleep
from tkinter import messagebox

import maskpass
import urllib3
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from common import ete_hosts, ite_hosts, routers

aviatrix_ite = "https://<internal URL here>"
aviatrix_ete = "https://<internal URL here>"
interval = 10


def verify_msgbox(message, title="Verification"):
    root = tk.Tk()
    root.overrideredirect(1)  # Pass Bool 1 to ignore this
    root.withdraw()  # And hide it (otherwise will spawn a 2nd window alongside msgbox)
    messagebox.showinfo(title, message)
    root.destroy()


def login_to_controller(_driver, username, password, _interval=interval, next=None):

    # Creative solution to ensure that after clicking the "Trace Route" button,
    # the script waits for page to be ready prior to continuing iteration (see for loop at the bottom)
    class ajax_req_to_finish(object):
        def __call__(self, _driver):
            return _driver.execute_script("return jQuery.active == 0")

    web_els, found_items = [], []
    url = (
        aviatrix_ite if not next else aviatrix_ete
    )  # take the default unless override is passed to func call, then take ETE URL
    _driver.get(url)
    _driver.maximize_window()
    _driver.find_element(By.XPATH, "//input[@placeholder='Username']").send_keys(username)
    _driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(password)
    _driver.find_element(By.XPATH, "//button[@type='submit']").send_keys(Keys.RETURN)
    _driver.switch_to.active_element
    sleep(_interval)  # Seems to be necessary or sometimes it doesn't think the popup is clickable yet
    popup = WebDriverWait(_driver, _interval + 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Close Tour']"))
    )
    if popup:
        sleep(5)
        print("Pop-up located on landing page. X'd out of it...")
        popup.click()
    troubleshoot_items = _driver.find_element(By.XPATH, "(//li[contains(@class, 'is-sub')])[last()]")
    troubleshoot_items.location_once_scrolled_into_view
    _driver.find_element(By.XPATH, "(//b[@class='caret'])[last()]").click()
    print("Expanding the Troubleshoot side menu..")
    sleep(_interval)
    _driver.find_element(By.XPATH, "//div[@id='troubleshoot']//ul//li//a[@title='Diagnostics']").click()
    print("Now entering the diagnostics sub menu...")
    sleep(_interval)
    locator = "//form//div[1]//select"
    clickable = WebDriverWait(_driver, _interval + 10).until(EC.element_to_be_clickable((By.XPATH, locator)))
    clickable.click()
    select = Select(_driver.find_element(By.XPATH, locator))  # Now, target it again using the special constructor

    gw_list = ite_hosts if not next else ete_hosts  # If override is explicitly specified, we already iterated through ITE
    # Loop thru the dropdown list of all our GW's and store them in a new list
    for option in range(len(select.options)):
        text = select.options[option].get_attribute("textContent")
        if option == 0:  # irrelevant data in HTML markup
            continue
        web_els.append(text)

    for i in range(len(web_els)):
        str_item = str(web_els[i]).strip()
        if str_item in gw_list:
            found_items.append(str_item)  # Shortened lst of only relevant GW's we want

    # Compare
    switch = False

    while True:
        for i in range(len(found_items)):
            select.select_by_visible_text(found_items[i])
            router_name = "<Internal prem router 1>" if not switch else "<Internal prem router 2>"
            print(f"Selected dropdown option: {found_items[i]}")
            place_holder = routers[router_name]["ip"]
            _driver.find_element(By.XPATH, "//input[contains(@placeholder, 'google')]").send_keys(place_holder)
            sleep(_interval)
            _driver.find_element(By.XPATH, "//button[contains(text(), 'Trace Route')]").click()
            wait = WebDriverWait(_driver, _interval + 20)
            wait.until(ajax_req_to_finish())
            verify_msgbox("Copy the trace output and click 'OK' to continue the script")
            _driver.find_element(By.XPATH, "//form//div[3]//div//input").clear()  # Being more direct here seems to work

            if i == len(found_items) - 1 and not switch:
                print("Changing destination IP to <internal prem router 2>...")
                switch = True
            elif i == len(found_items) - 1 and switch:
                return _driver


def in_rbac():
    identity = {}
    engineers = {
        # Key value mapping of names to internal employee ID's
    }

    for k, v in engineers.items():
        if v == os.getenv("USERNAME"):
            identity["name"] = k
            return identity
    return False


def initiate_driver(username, password, **kwargs):

    urllib3.disable_warnings(
        urllib3.exceptions.InsecureRequestWarning
    )  # This in tandem with experimental opts to silence terminal output
    os.environ["WDM_SSL_VERIFY"] = "0"  # Bypasses the self signed certs detected when pulling the latest exe
    os.environ["WDM_LOCAL"] = "1"  # Override default install dir of $HOME to use local proj dir instead
    opts = webdriver.ChromeOptions()  # opts.add_argument("--headless")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])  # Turns off annoying verbose output
    # The next line will bypass the need to install/point the code to a chrome driver executable on the local machine
    s = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(
        service=s, options=opts
    )  # creates a new instance of the Chrome driver using "service" we instantiated above

    sesh = (
        login_to_controller(driver, username, password)
        if not kwargs
        else login_to_controller(driver, username, password, next="Yes")
    )
    sesh.quit()
    sesh.stop_client()
    if not kwargs:
        print("\nITE Complete!")
        return 0  # Flag


def main():
    emp_name = in_rbac()
    if emp_name:
        print(f"{emp_name.get('name', 'null')} please use your LOCAL controller creds for the following prompts")
        print("\nSAML will not work")
        username = input("\nEnter your username for the Aviatrix controller: ").strip()
        password = maskpass.askpass(prompt="And now, your password: ", mask="*").strip()
        print("Thank you. Please be patient while automated browser navigation is performed...")
        sesh = initiate_driver(username, password)
        if sesh == 0:  # First controller return code
            print("Moving onto next controller momentarily...")
            sleep(interval)
            initiate_driver(
                username,
                password,
                data=True,  # dummy variable to flag Chrome driver to move onto ETE URL. Pass as keyword arg
            )
            print("\nBoth controllers finished with reverse traces.")
    else:
        print("You are not part of the engineer's RBAC group.\nThis is needed for authentication with the controller")
    return True  # Doing this for either outcome, so they'll get dropped back to the main menu anyway


if __name__ == "__main__":
    print("In browser_nav.py")
    # main()  # Allow direct run module during testing
