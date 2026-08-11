import sys
import os

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection
from managers.milestone_manager import add_milestone, update_milestone, list_milestones, delete_milestone

def test_milestone_lifecycle():
    print("Testing Milestone lifecycle...")
    
    # Dynamically find a valid shipment to run the test
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, job_no FROM shipments LIMIT 1")
            row = cur.fetchone()
            if not row:
                print("No shipments found in database. Skipping milestone lifecycle test.")
                return
            shipment_id = row['id']
            job_no = row['job_no']
            
    print(f"Found shipment ID={shipment_id}, job_no={job_no} for test.")

    try:
        # Create
        m_id = add_milestone(
            shipment_id=shipment_id,
            job_no=job_no,
            code="TEST_CODE",
            name="Test Milestone",
            event_date="2026-08-11 12:00:00",
            location="Bangkok",
            remark="On schedule"
        )
        assert m_id is not None
        print(f"Created milestone with ID: {m_id}")

        # List
        milestones = list_milestones(job_no)
        assert len(milestones) > 0
        found = False
        for m in milestones:
            if m["id"] == m_id:
                found = True
                assert "Bangkok" in m["remarks"]
        assert found, "Created milestone not found in list"
        print("Milestone listed successfully.")

        # Update
        updated = update_milestone(m_id, event_date="2026-08-11 13:00:00", location="Laem Chabang", remark="Delayed")
        assert updated is True
        print("Milestone updated successfully.")

        # Delete
        deleted = delete_milestone(m_id, job_no)
        assert deleted is True
        print("Milestone deleted successfully.")
    except Exception as e:
        print(f"Error during milestone test: {e}")
        raise

if __name__ == "__main__":
    test_milestone_lifecycle()
    print("All milestone manager tests passed successfully!")
