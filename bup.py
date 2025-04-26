import threading
from concurrent.futures import ThreadPoolExecutor
from seleniumbase import SB
import sys
from queue import Queue
import json

sys.argv.append("-n")


def tree_node(title, path, level, parent):
    return {
        "title": title,
        "path": path,
        "level": level,
        "parent": parent,
        "children": [],
    }


"""
class tree_node:
    def __init__(self, title, url, level, parent):
        self.title = title
        self.url = url
        self.level = level
        self.parent = parent
        self.children = []

    def addChild(self, child):
        self.children.append(child)

    def isLeaf(self):
        return len(self.children) == 0

    def getInfo(self):
        print(f"Title: {self.title}")
        print(f"URL: {self.url}")
        print(f"Level: {self.level}")
        print(f"Num children: {len(self.children)}")

    def toJson(self):
        return {
            "title": self.title,
            "url": self.url,
            "level": self.level,
            "children": list(map(lambda x: x.toJson(), self.children)),
        }
"""

def get_initial_categories():
     with SB(
        uc=True,
        headed=True,
        ad_block=True,
        page_load_strategy="eager",
        skip_js_waits=True,
        block_images=True,
        disable_js=True,
    ) as sb:
        categories = []
        sb.activate_cdp_mode("amazon.ca/gp/bestsellers")
        try:
            # get lowest layer tree items (they're all in a div in role "group")
            itemTags = sb.cdp.select_all(
                'div[role="group"] > div[role="treeitem"] > a', 0.01
            )

            if not selectedInGroup:
                for itemTag in itemTags:
                    # add new tree node with data from each link in the tree
                    categories.append({
                        "category":itemTag.text,
                        "link": itemTag.attrs.href
                    })

            print("Got categories")
            return true
        except Exception as error:
            print("Couldnt get categories")
            sb.cdp.save_screenshot("error.png")
            # TODO: check for challenge
            return false


def initiate_scrapers(numInstances):
    return

def scraper_instance(initial):
    q = Queue()
    with SB(
        uc=True,
        headed=True,
        ad_block=True,
        page_load_strategy="eager",
        skip_js_waits=True,
        block_images=True,
        disable_js=True,
    ) as sb:
        sb.activate_cdp_mode(initial)
        # bfs
        while not q.empty():
            page = sb.cdp.get(prefix + cur["path"])
            # note: selected page is bolded(and not clickable) in the link tree
            selectedInGroup = None
            try:
                selectedInGroup = sb.cdp.select(
                    'div[role="group"] > div[role="treeitem"] > span', 0.01
                )
                # print("LEAF")
            except Exception:
                # print("NOT A LEAF")
                pass

            try:
                # get lowest layer tree items (they're all in a div in role "group")
                itemTags = sb.cdp.select_all(
                    'div[role="group"] > div[role="treeitem"] > a', 0.01
                )

                # only add items in the group if the current item is not in the group

                if not selectedInGroup:
                    for itemTag in itemTags:
                        # add new tree node with data from each link in the tree
                        newNode = tree_node(
                            itemTag.text,
                            itemTag.attrs.href,
                            cur["level"] + 1,
                            cur,
                        )
                        cur["children"].append(newNode)
                        shared_q.put(newNode)

                    for child in cur["children"]:
                        shared_q.put(child)

                print(cur["title"])
            except Exception as error:
                print(error)
                sb.cdp.save_screenshot("error.png")
                # TODO: check for challenge
                pass


def main():
    numInstances = 1
    prefix = "https://amazon.ca"
    start = "/Best-Sellers-Amazon-Devices-Accessories-Device-Bundles/zgbs/amazon-devices/21579927011/ref=zg_bs_unv_amazon-devices_3_21579936011_2"  # "/gp/bestsellers"

    resultTree = tree_node("root", start, 0, None)
    shared_q = Queue()
    shared_q.put(resultTree)

    with ThreadPoolExecutor(max_workers=numInstances) as executor:
        for i in range(numInstances):
            executor.submit(scraper_instance, shared_q, i, prefix)

    print(resultTree)
    
    with open("tree.json", "w+") as f:
        json.dump(resultTree, f)
    

if __name__ == "__main__":
    main()
