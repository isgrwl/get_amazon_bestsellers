import sys
import json
from multiprocessing import Queue, Pool, Process, Manager, TimeoutError
from seleniumbase import SB
import time

def scrape_product_data(asins):
    with SB(
        uc=True,
        headed=True,
        ad_block=True,
        page_load_strategy="eager",
        skip_js_waits=True,
        block_images=True,
        disable_js=True,
    ) as sb:
        sb.activate_cdp_mode()
        while len(asins) > 0:
            try:
                asin = asins.pop()
            except TimeoutError:
                print("Error: Tried to access empty queue")
                break
        
            page = sb.cdp.get("https://amazon.ca/dp/"+ asin)

            #get contents
            title = sb.cdp.find("#titleSection").text
            print(title)

with open("asins.json","r") as f:
    asins = json.load(f)
    scrape_product_data(asins)