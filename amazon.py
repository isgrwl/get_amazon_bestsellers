import sys
import json
from multiprocessing import Queue, Pool, Process, Manager, TimeoutError
from seleniumbase import SB
import time

sys.argv.append("-n")




def get_asins(s, root):
    if "asins_ranked" in root:
        for asin in root["asins_ranked"]:
            s.add(asin)

    if "children" in root:
        for child in root["children"]:
            get_asins(s, child)


def dump_asins(inf, outf):
    with open(inf, "r") as f:
        data = json.load(f)
        unique_asins = set()
        get_asins(unique_asins, data)

        with open(outf, "w+") as a:
            json.dump(list(unique_asins), a)
            print(f"Wrote {len(unique_asins)} unique asins to: {outf}")


def node_factory(manager):
    def new_node(title, path, level):
        return {
            "title": title,
            "path": path,
            "level": level,
            "children": manager.list([]),
            "asins_ranked": manager.list([]),
        }

    return new_node


def serialize_recursive(key_map, k):
    d = key_map[k]
    children = list(d["children"])  # convert to pure python list
    asins = list(d["asins_ranked"])

    # delete empty lists
    if children and len(children) > 0:
        d["children"] = list(
            map(lambda x: serialize_recursive(key_map, x), children)
        )  # recursively serialize each child dict
    else:
        del d["children"]

    if asins and len(asins) > 0:
        d["asins_ranked"] = asins
    else:
        del d["asins_ranked"]

    return d


def scraper_instance(q, d, instance_num, prefix, new_node):
    with SB(
        uc=True,
        headed=False,
        ad_block=True,
        page_load_strategy="eager",
        skip_js_waits=True,
        block_images=True,
        disable_js=True,
    ) as sb:
        sb.activate_cdp_mode()

        sb.sleep(instance_num * 5)  # wait for earlier instances to initialize list

        # bfs
        try:
            while not q.empty():

                try:
                    cur = q.get(timeout=5)
                except TimeoutError:
                    print("Error: Tried to access empty queue")
                    break

                page = sb.cdp.get(prefix + cur)  # navigate to page
                sb.cdp.scroll_to_bottom()

                # note: selected page is bolded(and not clickable) in the link tree
                selectedInGroup = None
                t1 = time.time()
                try:
                    # =leaf node
                    

                    selectedInGroup = sb.cdp.select(
                        'div[role="group"] > div[role="treeitem"] > span', 0.01
                    )
                    

                except Exception:
                    # = not a leaf node
                    pass
                t2 = time.time()
                print(f"Rendered in {t2-t1}s")

                try:
                    # get lowest layer tree items (they're all in a div in role "group")
                    itemTags = sb.cdp.select_all(
                        'div[role="group"] > div[role="treeitem"] > a', 0.01
                    )

                    # only add items in the group if the current item is outside the group
                    if not selectedInGroup:
                        for itemTag in itemTags:
                            nodeKey = itemTag.attrs.href
                            # print(f"Added {itemTag.text} to queue")
                            # add new tree node with data from each link in the tree
                            new = new_node(
                                itemTag.text,
                                nodeKey,
                                d[cur]["level"] + 1,
                            )
                            d[nodeKey] = new  # create new node in hash table
                            d[cur]["children"].append(nodeKey)
                            q.put(nodeKey)

                    # get all products asins from page listing
                    productDivs = sb.cdp.select_all("#gridItemRoot", 1)
                    for product in productDivs:
                        asin_container = product.query_selector("div[data-asin]")
                        asin = asin_container.get_attribute("data-asin")
                        d[cur]["asins_ranked"].append(asin)

                except Exception as error:
                    print(error)
                    sb.cdp.save_screenshot("error.png")
                    # TODO: check for challenge
                    pass

                sb.sleep(3)

        finally:
            print(f"Instance {instance_num} exited")
            return


def main():
    tree_file = "tree.json"
    numInstances = 1
    url_prefix = "https://amazon.ca"
    start_url = "/Best-Sellers-Beauty-Personal-Care-Oral-Hygiene-Products/zgbs/beauty/6371153011/ref=zg_bs_unv_beauty_2_23912483011_1"  # "/gp/bestsellers"

    manager = Manager()

    result_map = manager.dict()  # stores results
    url_queue = Queue()  # stores urls to navigate

    new_node = node_factory(manager)

    url_queue.put(start_url)
    result_map[start_url] = new_node("root", start_url, 0)

    processes = []

    # spawn processes
    with Pool(processes=numInstances) as pool:
        for instance_num in range(numInstances):
            process = Process(
                target=scraper_instance,
                args=(url_queue, result_map, instance_num, url_prefix, new_node),
            )
            process.start()
            print(f"Spawned instance {instance_num}")
            processes.append(process)

    # wait for all processes to complete
    for process in processes:
        process.join()

    # convert mp lists into pure lists to be json serializable
    result = serialize_recursive(result_map, start_url)

    print("Done scraping all product branches from: " + start_url)

    # write results
    with open(tree_file, "w+") as f:
        print(f"Wrote bestseller tree to: {tree_file}")
        json.dump(result, f)

    # dump asins
    dump_asins(tree_file, "asins.json")


if __name__ == "__main__":
    main()
