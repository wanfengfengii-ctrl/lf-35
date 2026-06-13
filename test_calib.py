import sys
sys.path.insert(0, '.')

from database.db_manager import get_db

db = get_db()

print('Testing get_calibration_records...')
try:
    records = db.get_calibration_records()
    print(f'Success! {len(records)} records')
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()

print('\nTesting get_calibration_records with device_id=1...')
try:
    records = db.get_calibration_records(1)
    print(f'Success! {len(records)} records')
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()

print('\nDone.')
