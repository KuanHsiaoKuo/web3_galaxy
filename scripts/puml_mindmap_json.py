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
                # 存放节点信息、节点id、节点多少子节点
                levels[stars] = [line, title_index, 0]
                parent = levels.get(stars[:-1])
                node = {
                    "id": title_index,
                    "layers": len(stars),
                    "name": name,
                    # "size": len(name)
                    # "link": 'https://www.google.com'
                }
                title_index += 1
                if parent:
                    node["parent"] = parent[1]
                    parent[2] = parent[2] + 1
                if links:
                    # 如果是有链接，就变成子节点
                    link_count = 1
                    for link_name, link in links.items():
                        if link_count == 1:
                            node['link'] = link
                        if link_count > 1:  # 多于一个链接才作为子节点
                            child_node = {
                                "id": title_index,
                                "name": f"链接{link_count}: {link_name}",
                                "link": link,
                                "parent": node['id'],
                                "note": f'来自{node["name"]}的链接'
                            }
                            title_index += 1
                            json_results.append(child_node)
                            link_count += 1
                if color:
                    node["color"] = '#' + color
                if index < len(lines) and lines[index + 1].startswith('<code>'):
                    note = notes.pop(0)
                    node['note'] = f"{title_note}\n{note}" if title_note else note
                json_results.append(node)
    json_results = add_child_count(json_results)
    json_results = add_node_count(json_results)
    json_results = add_tool_tip(json_results)
    return json_results


def add_child_count(parse_results: list[dict]):
    """
    添加子节点数量, 根据子节点数量控制标题换行
    :param parse_results:
    :return:
    """
    children_count = {}
    for node in parse_results:
        if node.get('parent'):  # 根节点就不处理
            children_count[node['parent']] = children_count.get(node['parent'], 0) + 1
    # 再加上子节点数量
    for node in parse_results:
        node['child_count'] = children_count.get(node['id'], 0)
        node['name'] = get_wrap_name(node['name'], node['child_count'])
    return parse_results


def add_node_count(parse_results: list[dict]):
    """
    根据子节点数量child_count+1作为父节点名下节点的数量node_count
    按层数从外到内缩小
    :param parse_results:
    :return:
    """
    layers_list = {}
    max_layer = 1
    for node in parse_results:
        layer = node['layers']
        if not layers_list.get(layer):
            layers_list[layer] = []
        layers_list[layer].append(node)
        if layer > max_layer:
            max_layer = layer
    id_dict = {node['id']: node for node in parse_results}
    while max_layer > 0:
        layer_nodes = layers_list[max_layer]
        for node in layer_nodes:
            parent = id_dict.get(node.get('parent', None))
            if parent:
                # parent['node_count'] = parent.get('node_count', 1) + node.get('node_count', 1)
                parent['node_count'] = parent.get('node_count', 0) + node.get('node_count', 1)
            if node.get('child_count') == 0:
                node['node_count'] = 1
        max_layer -= 1
    parsed_results = []
    for layer, nodes in layers_list.items():
        parsed_results.extend(nodes)
    # 最后统一计算所占角度
    # root = layers_list[1][0]
    # total_node_count = root['node_count']
    # node_angle = float('%.4f' % (360 / total_node_count))
    # for node in parsed_results:
    #     node['node_angle'] = node['node_count'] * node_angle
    return parsed_results


def add_tool_tip(parse_results: list[dict]):
    optional_fileds = ['note', 'link']
    for node in parse_results:
        node['tool_tip'] = {
            'title': node['name'],
        }
        for field in optional_fileds:
            value = node.get(field)
            if value:
                node['tool_tip'][field] = value
    return parse_results


def write_bubble_json(parse_results: list[dict]):
    filename = f"{re.split('[/|.]', puml_path)[-2]}_bubble.json"
    file_path = '../src/overview/vega/'
    amount_start = 0.91
    bubble_content = []
    for item in parse_results:
        node = {
            "category": item['name'],
            "amount": float('%.2f' % (amount_start - 0.03 * item['layers']))
        }
        if item.get('link'):
            node['link'] = item['link']
        if item.get('note'):
            node['note'] = item['note']
        bubble_content.append(node)
    with open(f"{file_path}{filename}", 'w') as f:
        f.write(json.dumps(bubble_content))


def write_knowledge_graph_json(parse_results: list[dict]):
    filename = f"{re.split('[/|.]', puml_path)[-2]}_knowledge_graph.json"
    file_path = '../src/overview/vega/'
    # knowledge_graph_nodes = parse_results
    knowledge_graph_links = []
    knowledge_graph_nodes = []
    for node in parse_results:
        if node.get('parent'):
            link = {'source': node['id'], 'target': node['parent'], 'value': 1}
            knowledge_graph_links.append(link)
        node['index'] = node['id']
        knowledge_graph_nodes.append(node)
    knowledge_graph = {'nodes': knowledge_graph_nodes, 'links': knowledge_graph_links}
    with open(f"{file_path}{filename}", 'w') as f:
        f.write(json.dumps(knowledge_graph))


def write_tree_json(parse_results: list[dict]):
    filename = f"{re.split('[/|.]', puml_path)[-2]}.json"
    file_path = '../src/overview/vega/'
    with open(f"{file_path}{filename}", 'w') as f:
        f.write(json.dumps(parse_results))


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
    stars = re.split('[ :\[]', line)[0]
    name = line[len(stars):]
    if name.startswith('[#'):  # 如果有颜色
        color = re.findall('\[#(.*?)\]', name)[0]
        name = name.split(']')[1]
    if name.startswith(':'):  # 如果有注释
        name = name[1:]
    if ': ' in name:  # 如果是github这种在": "之后有说明的
        name, title_note = name.split(': ', 1)
    else:
        title_note = None
    return stars, name, color, link_dict, title_note


def get_wrap_name(name, child_count):
    """
    根据子节点个数来确定换行,避免文字重叠
    一般来说，父节点行数 = 子节点个数 - 1
    :param name:
    :param child_count:
    :return:
    """
    # 统一添加换行符
    name = name.strip().replace('  ', ' ')
    wrap_name_list = [char for char in name]
    # space_count = 0
    wrap_count = 0
    # symbols = ['/', '-']
    for index, char in enumerate(wrap_name_list):
        # if char == ' ':
        #    space_count += 1
        # if space_count == 2:
        #    if wrap_count < child_count:
        #        wrap_name_list[index] = '\n'
        #        wrap_count += 1
        #    space_count = 0
        # if char in symbols:
        #    wrap_name_list[index] += '\n'
        if index > 0 and index % 12 == 0 and wrap_count < child_count - 1:
            wrap_count += 1
            wrap_name_list[index] += '\n'
    wrap_name = ''.join(wrap_name_list).strip()
    if child_count:
        print(child_count, wrap_name_list)
    return wrap_name


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
    converted_results = converter(puml_path)
    write_tree_json(converted_results)
    write_bubble_json(converted_results)
    write_knowledge_graph_json(converted_results)
