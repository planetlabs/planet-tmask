.PHONY: remove_pycache
remove_pycache:
	find . -name "*.pyc" -delete
	find . -name __pycache__ -type d -empty -delete

clean: remove_pycache
	find installation_tests -name "*.so"  -delete
	$(MAKE) clean -C tmask

test_gsl:
	$(MAKE) -C installation_tests/test_gsl

unit_tests:
	nosetests data_prep/tests/*
	nosetests tmask/tests/*

requirements:
	pip3 install -U -r requirements.txt

build: requirements
	$(MAKE) -C tmask

run_data_prep:
	python3 data_prep.py --lon -67.68 --lat -14.2455 --bufferval 0.003

