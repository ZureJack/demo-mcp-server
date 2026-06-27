#!/usr/bin/env python3
"""c_identifier_find Server 入口。

用法:
    python c_identifier_find_server.py /path/to/config.json
"""

import sys
import json


def main():
    if len(sys.argv) < 2:
        print(
            "用法: python c_identifier_find_server.py /path/to/config.json",
            file=sys.stderr,
        )
        sys.exit(1)

    config_path = sys.argv[1]
    try:
        with open(config_path) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"错误: 无法读取配置文件 {config_path}: {e}", file=sys.stderr)
        sys.exit(1)

    from tools_server.c_identifier_find.server import run_server

    run_server(config)


if __name__ == "__main__":
    main()
