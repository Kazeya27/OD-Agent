pip install -r requirements.txt
python generate_test_db.py
python -m uvicorn app:app --reload