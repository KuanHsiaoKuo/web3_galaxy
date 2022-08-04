"""
主要将plantuml的mindmap写法转为vega可用的json文件
"""
import sys
import re
import json


def converter(puml_path: str):
    """
    传入puml文件路径进行解析转化
    1. 标题都是以*开头, 且一个*的都是根节点
    2. 父级节点只会比子级节点少一个*，如果当前节点比下一个节点少于超过一个*，puml就无法通过
    3. 如果下一个节点比上一个节点少*，就去对应列表里面找最后一个
    :param puml_path:
    :return:
    """
    print(f"开始处理{puml_path}...")
    levels = {}
    json_results = []
    with open(puml_path, 'r') as f:
        notes = extract_notes(f.read())

    with open(puml_path, 'r') as f:
        lines = [line for line in f.readlines()]
        title_index = 1
        for index, line in enumerate(lines):
            # 标题的*后面只会出现三种情况：空格、:、[
            if line.startswith('*'):
                stars, name, color, links, title_note = extract_stars_name_links_color(line)
                levels[stars] = (line, title_index)
                parent = levels.get(stars[:-1])
                has_child = False
                node = {
                    "id": title_index,
                    # "name": wrap_name,
                    # "size": len(name)
                    # "link": 'https://www.google.com'
                }
                if parent:
                    has_child = True
                    node["parent"] = parent[1]
                if links:
                    # 如果是有链接，就变成子节点
                    link_count = 1
                    for link_name, link in links.items():
                        title_index += 1
                        if link_count == 1:
                            node['link'] = link
                        if link_count > 1:  # 多于一个链接才作为子节点
                            has_child = False
                            wrap_link_name = get_wrap_name(f"链接{link_count}: {link_name}", has_child)
                            child_node = {
                                "id": title_index,
                                "name": wrap_link_name,
                                "link": link,
                                "parent": node['id'],
                                "note": f'来自{node["name"]}的链接'
                            }
                            json_results.append(child_node)
                            link_count += 1
                if color:
                    node["color"] = '#' + color
                if index < len(lines) and lines[index + 1].startswith('<code>'):
                    note = notes.pop(0)
                    print(f"弹出的注释：{note}")
                    node['note'] = f"{title_note}\n{note}" if title_note else note
                wrap_name = get_wrap_name(name, has_child)
                node['name'] = wrap_name
                json_results.append(node)
                title_index += 1
    filename = f"{re.split('[/|.]', puml_path)[-2]}.json"
    file_path = '../src/overview/vega/'
    with open(f"{file_path}{filename}", 'w') as f:
        f.write(json.dumps(json_results))


def extract_stars_name_links_color(line=''):
    color = None
    links = re.findall('\[\[(.*?)\]\]', line)
    link_dict = {}
    for index, link in enumerate(links):
        href, title = link.split(' ', 1)
        # 除了第一个链接，其他都作为子链接
        if index == 0:
            line = line.replace(f"[[{href} {title}]]", f' {title}')
        else:
            line = line.replace(f"[[{href} {title}]]", "")
        link_dict[title] = href
    try:
        stars = re.split('[ :\[]', line)[0]
        name = line[len(stars):]
        if name.startswith('[#'):  # 如果有颜色
            color = re.findall('\[#(.*?)\]', name)[0]
            name = name.split(']')[1]
        if name.startswith(':'):  # 如果有注释
            name = name[1:]
        if ': ' in name: # 如果是github这种在": "之后有说明的
            name, title_note = name.split(': ', 1)
        else:
            title_note = None
    except:
        print(line)
    return stars, name, color, link_dict, title_note


def get_wrap_name(name, has_child):
    """
    根据是否有子节点选择是否换行
    1. 有子节点，选择换行
    2. 没有子节点，不需要换行，否则文字会重叠
    :param name:
    :param has_child:
    :return:
    """
    # 统一添加换行符
    if not has_child:
        wrap_name = []
        space_count = 0
        for char in name:
            if char == ' ':
                space_count += 1
            if space_count == 3:
                char = '\n'
                space_count = 0
            wrap_name.append(char)
        return ''.join(wrap_name)
    else:
        return name


def extract_notes(text=''):
    #     text = '''
    #         ****:tail -n 80 customSpec.json
    # <code>
    #
    # 此命令显示 Wasm 二进制字段后面的最后部分，
    # 包括运行时使用的几个托盘的详细信息，
    # 例如 sudo 和 balances 托盘。
    # </code>;
    # ****:Modify the name field to identify this chain specification as a custom chain specification.
    # <code>
    #
    # "name": "My Custom Testnet",
    # </code>
    # ****:Modify aura field to specify the nodes
    # <code>
    #     '''
    # 同时匹配换行符
    # (?:pattern) 来解决方括号不适用的场景
    # [正则匹配所有字符（包括换行）_尐东东的博客-CSDN博客_正则匹配所有字符](https://blog.csdn.net/u011158908/article/details/105666329)
    notes = re.findall('\<code\>((?:.|\n)*?)\</code\>', text)
    return notes


def extract_links(text=''):
    links = re.findall('\[\[(.*?)\]\]', text)
    link_dict = {}
    for link in links:
        href, title = link.split(' ', 1)
        link_dict[title] = href
    return link_dict


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("请传入puml文件路径...")
    else:
        puml_path = sys.argv[1]
        if not puml_path.endswith('.puml'):
            print("请传入puml文件...")
    converter(puml_path)