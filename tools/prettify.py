####################################################################################################

import argparse
from pathlib import Path

try:
    import orjson as json
except ImportError:
    import json

try:
    from rich.console import Console
    from rich.highlighter import RegexHighlighter, _combine_regex
    from rich.theme import Theme
except ImportError:
    print('https://github.com/textualize/rich is required')
    print('Run `pip install rich` or `uv add rich`')

####################################################################################################

class ReprHighlighter(RegexHighlighter):
    """Highlights the text typically produced from ``__repr__`` methods."""
    # See https://stackoverflow.com/questions/26459749/pretty-printing-json-with-ascii-color-in-python/68190273#68190273
    # https://github.com/Textualize/rich/discussions/1042
    base_style = "repr."
    highlights = [
        r"(?P<tag_start>\<)(?P<tag_name>[\w\-\.\:]*)(?P<tag_contents>[\w\W]*?)(?P<tag_end>\>)",
        r"(?P<attrib_name>[\w_]{1,50})=(?P<attrib_value>\"?[\w_]+\"?)?",
        r"(?P<brace>[\{\[\(\)\]\}])",
        _combine_regex(
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
            r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
            r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
            r"(?P<call>[\w\.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            r"(?P<ellipsis>\.\.\.)",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[\-\+]?\d+?)?\b|0x[0-9a-fA-F]*)",
            r"(?P<path>\B(\/[\w\.\-\_\+]+)*\/)(?P<filename>[\w\.\-\_\+]*)?",
            # value_str
            r":(?<![\\\w]) (?P<value_str>b?\'\'\'.*?(?<!\\)\'\'\'|b?\'.*?(?<!\\)\'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            r"(?<![\\\w])(?P<str>b?\'\'\'.*?(?<!\\)\'\'\'|b?\'.*?(?<!\\)\'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            r"(?P<uuid>[a-fA-F0-9]{8}\-[a-fA-F0-9]{4}\-[a-fA-F0-9]{4}\-[a-fA-F0-9]{4}\-[a-fA-F0-9]{12})",
            r"(?P<url>(https|http|ws|wss):\/\/[0-9a-zA-Z\$\-\_\+\!`\(\)\,\.\?\/\;\:\&\=\%\#]*)",
        ),
    ]

####################################################################################################

parser = argparse.ArgumentParser(
    prog='prettify',
    description='Prettify LSP logs',
    epilog='',
)
parser.add_argument(
    'filename',
    type=Path,
)
args = parser.parse_args()

####################################################################################################

theme = Theme({
    'level': 'red',
    'time': 'yellow',
    'server': 'magenta',
    'direction': 'orange_red1',
    'method': 'light_slate_blue',
    "repr.str": "bright_blue",
    "repr.value_str": "green",
})
console = Console(theme=theme, highlighter=ReprHighlighter())

console.print(args.filename)
console.print()
file_content = args.filename.read_bytes()
for line in file_content.splitlines():
    line = line.strip()
    level = chr(line[0]).upper()
    i = line.find(b']')
    mtime = line[2:i].decode()
    rich1 = f"[level]{level}[/] [time]{mtime}[/]"
    j = line.find(b'{')
    if j == -1:
        # print(line)
        jsonrpc = None
        right = line[i + 2:].decode()
        if right[0] == '[':
            _: list[str] = right.split(maxsplit=4)
            server, date, hour, server_level, message = _
            console.print(f"{rich1} [server]{server}[/] [time]{date}[/] [level]{server_level}[/] {message}")
        else:
            console.print(f"{rich1} {right}")
    elif line[-1] == ord(b'}'):
        right = line[i+1:j].decode().split(maxsplit=3)
        if len(right) == 3:
            server, direction, method = right
            console.print(f"{rich1} [direction]{direction}[/][server]\{server:6}[/]  [method]{method}[/]")
        else:
            direction, method = right
            console.print(f"{rich1} [direction]{direction}[/]{' ' * 6} [method]{method}[/]")
        jsonrpc = json.loads(line[j:])
        console.print(jsonrpc)
    elif line.endswith(b'bytes total)'):
        console.print(f"{rich1} truncated")
    else:
        print(line)
        raise ValueError
