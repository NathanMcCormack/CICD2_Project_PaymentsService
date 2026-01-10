PaymentServiceAPP = app.main:app 
install: 
	pip install -r requirements.txt 

runPayment: 
	python -m uvicorn $(PaymentServiceAPP) --host 0.0.0.0 --port 8000 --reload 

test: 
	python -m pytest -q
