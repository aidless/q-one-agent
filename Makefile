# --- acceptance_backfill (EVAL_ACCEPTANCE_STANDARD.md P4) ---
# 证据来源: checks.yml
# 命令逐字取自该来源，未增删任何参数。
# 归一: python → python3（本机无 python 别名，实测 Error 127）
# 归一: 补 PYTHONPATH=src。CI 在跑测试前 `python -m pip install .` 装包，
#   本机未安装 qone_agent（src 布局），裸 unittest 报 ModuleNotFoundError: qone_agent；
#   PYTHONPATH=src 等价于安装后的导入路径，不动任何源码/测试。
.PHONY: eval

eval:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
