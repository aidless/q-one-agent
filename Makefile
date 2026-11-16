# Offline checks. Requires Python 3.10+ and httpx (pip install -e .).
# After that install, these targets do not use the network.
.PHONY: check eval

check: eval
	PYTHONPATH=src python3 scripts/fault_matrix.py --check
	PYTHONPATH=src python3 scripts/check_drift.py
	PYTHONPATH=src python3 eval/run_cases.py
	PYTHONPATH=src python3 eval/run_cases.py --selftest

eval:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
