from ..database import EpushSessionLocal, get_mongo_db
from sqlalchemy.orm import Session
from datetime import datetime

def fetch_epush_data():
    """
    🔄 Fetches attendance data from MySQL EPUSH Database and syncs it to MongoDB.
    """
    db: Session = EpushSessionLocal()
    mongo_db = get_mongo_db()  # Connect to MongoDB

    try:
        query = """
        SELECT employee_id, punch_in, punch_out, DATE(punch_in) AS date, status
        FROM attendance WHERE DATE(punch_in) = CURDATE()
        """
        results = db.execute(query).fetchall()

        if not results:
            return {"message": "No new attendance records found in EPUSH"}

        attendance_collection = mongo_db["attendance"]
        synced_count = 0

        for record in results:
            employee_id = record["employee_id"]
            punch_in_time = record["punch_in"]
            punch_out_time = record["punch_out"]
            date = record["date"]

            # Check if record already exists in MongoDB
            existing_record = attendance_collection.find_one({
                "employee_id": employee_id,
                "date": str(date)
            })

            if not existing_record:
                # Insert new record
                attendance_collection.insert_one({
                    "employee_id": employee_id,
                    "punch_in": punch_in_time,
                    "punch_out": punch_out_time,
                    "status": record["status"],
                    "date": str(date),  # Store date as string for compatibility
                    "synced_at": datetime.utcnow()
                })
                synced_count += 1

        return {"message": f"Synced {synced_count} new attendance records from EPUSH"}

    except Exception as e:
        return {"error": f"Sync failed: {str(e)}"}

    finally:
        db.close()
