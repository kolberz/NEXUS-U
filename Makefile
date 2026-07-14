PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: bootstrap test reality-test lint compile demo discovery obligations reality routing-benchmark federation-benchmark tension-benchmark discovery-trials independent-challenge preregistered-reproduction lower-bound-lab lower-bound-search formalized-lower-bound cross-kernel kernel-bridge kernel-receipts nexus-kernel capabilities serve package release clean

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip setuptools wheel build
	$(BIN)/python -m pip install -e ".[dev]"

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

reality-test:
	PYTHONPATH=src $(PYTHON) -m pytest -q -m reality

lint:
	PYTHONPATH=src $(PYTHON) -m compileall -q src tests scripts

compile: lint

demo:
	PYTHONPATH=src $(PYTHON) -m nexus_u run examples/hello_python.json --output artifacts

discovery:
	PYTHONPATH=src $(PYTHON) -m nexus_u run examples/discovery.json --output artifacts

obligations:
	PYTHONPATH=src $(PYTHON) -m nexus_u run examples/obligation_aware.json --output artifacts
	@GRAPH=$$(ls -t artifacts/*.obligations.json | head -1); PYTHONPATH=src $(PYTHON) -m nexus_u verify-obligations $$GRAPH

reality:
	PYTHONPATH=src $(PYTHON) -m nexus_u reality-benchmark --builtin --output benchmark-results

routing-benchmark:
	PYTHONPATH=src $(PYTHON) -m nexus_u routing-benchmark --output benchmark-results

federation-benchmark:
	PYTHONPATH=src $(PYTHON) -m nexus_u federation-benchmark --output benchmark-results

tension-benchmark:
	PYTHONPATH=src $(PYTHON) -m nexus_u tension-benchmark --output benchmark-results

discovery-trials:
	PYTHONPATH=src $(PYTHON) -m nexus_u discovery-trials --output benchmark-results

independent-challenge:
	PYTHONPATH=src $(PYTHON) -m nexus_u independent-challenge --output benchmark-results

preregistered-reproduction:
	PYTHONPATH=src $(PYTHON) -m nexus_u preregistered-reproduction --output benchmark-results/reproduction

lower-bound-lab:
	PYTHONPATH=src $(PYTHON) -m nexus_u lower-bound-lab --output benchmark-results

lower-bound-search:
	PYTHONPATH=src $(PYTHON) -m nexus_u lower-bound-search --output benchmark-results

formalized-lower-bound:
	PYTHONPATH=src $(PYTHON) -m nexus_u formalized-lower-bound --output benchmark-results

cross-kernel:
	PYTHONPATH=src $(PYTHON) -m nexus_u cross-kernel --output benchmark-results

kernel-bridge:
	PYTHONPATH=src $(PYTHON) -m nexus_u kernel-bridge --output benchmark-results

kernel-receipts:
	PYTHONPATH=src $(PYTHON) -m nexus_u kernel-receipts --output benchmark-results

nexus-kernel:
	PYTHONPATH=src $(PYTHON) -m nexus_u nexus-kernel-benchmark --output benchmark-results

capabilities:
	PYTHONPATH=src $(PYTHON) -m nexus_u capabilities

serve:
	PYTHONPATH=src $(PYTHON) -m nexus_u serve --host 0.0.0.0 --port 8080

package:
	$(PYTHON) -m build

release: test reality-test lint demo discovery obligations reality routing-benchmark federation-benchmark tension-benchmark discovery-trials independent-challenge preregistered-reproduction lower-bound-lab lower-bound-search formalized-lower-bound cross-kernel kernel-bridge kernel-receipts nexus-kernel package
	PYTHONPATH=src $(PYTHON) scripts/release_gate.py

clean:
	rm -rf .venv build dist *.egg-info src/*.egg-info artifacts benchmark-results .pytest_cache __pycache__
