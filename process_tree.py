import json


def count_children_recursive(root):
    s = 0
    if "children" not in d or len(d["children"]) == 0:
        s = 1
    for c in d["children"]:
        s += count_children_recursive(c)

    return s


def get_asins(s, root):
    if "asins_ranked" in root:
        for asin in root["asins_ranked"]:
            s.add(asin)

    if "children" in root:
        for child in root["children"]:
            get_asins(s, child)


def dump_asins(inf,outf):
    with open(inf, "r") as f:
        data = json.load(f)
        unique_asins = set()
        get_asins(unique_asins, data)

        print(list(unique_asins))

        with open(outf,"w+") as a:
            json.dump(list(unique_asins),a)
    
