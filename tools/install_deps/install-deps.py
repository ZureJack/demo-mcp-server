"""
命令行入口：按需安装指定能力模块的依赖。

用法:
    python tools/install_deps/install-deps.py
    python tools/install_deps/install-deps.py time_tools file_tools
"""

import sys
from tools.install_deps import install_deps

if __name__ == "__main__":
    modules = sys.argv[1:] if len(sys.argv) > 1 else None
    results = install_deps(modules)
    for name, status in results.items():
        print(f"[{name}] {status}")
