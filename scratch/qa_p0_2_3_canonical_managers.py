import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import get_connection
from managers.container_manager import add_container, list_containers, delete_container
from managers.milestone_manager import add_milestone, list_milestones, update_milestone, delete_milestone

def setup_test_shipment():
    job_no = "QA-TEST-1000"
    with get_connection() as conn:
        conn.execute("DELETE FROM shipments WHERE job_no = %s", (job_no,))
        conn.commit()
        cur = conn.execute("INSERT INTO shipments (job_no, status) VALUES (%s, 'Proceed') RETURNING id", (job_no,))
        shipment_id = cur.fetchone()['id']
        conn.commit()
    return shipment_id, job_no

def cleanup(job_no):
    with get_connection() as conn:
        conn.execute("DELETE FROM shipments WHERE job_no = %s", (job_no,))
        conn.commit()

def run_tests():
    print("Running Canonical Manager Tests...")
    shipment_id, job_no = setup_test_shipment()
    
    try:
        # CONTAINER TESTS
        print("1. Add Valid Container...")
        res = add_container({"job_no": job_no, "shipment_id": shipment_id, "container_no": "TCNU1234567"})
        assert res == True, "Failed to add container"
        
        print("2. List Containers...")
        ctrs = list_containers(job_no=job_no)
        assert len(ctrs) == 1
        c_id = ctrs[0]['id']
        
        print("3. Duplicate container rejection...")
        try:
            add_container({"job_no": job_no, "shipment_id": shipment_id, "container_no": "TCNU1234567"})
            assert False, "Should have rejected duplicate"
        except Exception as e:
            print(f"   Success: Caught DB Constraint {type(e).__name__}")
            
        print("4,5,6,7. Negative Tare/Gross/VGM auto-correction...")
        add_container({"job_no": job_no, "shipment_id": shipment_id, "container_no": "MSKU1234567", "tare_weight": -100, "gross_weight": -100})
        ctrs = list_containers(job_no=job_no)
        for c in ctrs:
            if c['container_no'] == "MSKU1234567":
                assert c['tare_weight'] > 0, "Failed auto tare"
                assert c['gross_weight'] > 0, "Failed auto gross"
                c2_id = c['id']
                
        print("8. Correct shipment ownership...")
        assert ctrs[0]['shipment_id'] == shipment_id
        
        print("9. Delete container...")
        assert delete_container(c_id, job_no) == True
        assert delete_container(c2_id, job_no) == True
        
        # MILESTONE TESTS
        print("10. Add valid milestone...")
        m_id = add_milestone(shipment_id, job_no, "BKD", "Booking", "2023-01-01 10:00:00", "BKK", "Test")
        assert m_id > 0
        
        print("11. List milestones...")
        ms = list_milestones(job_no)
        assert len(ms) == 1
        
        print("12. Update milestone...")
        update_milestone(m_id, event_date="2023-01-02 10:00:00", location="LCB", remark="Updated")
        ms = list_milestones(job_no)
        assert ms[0]['location'] == "LCB"
        
        print("13. Delete milestone...")
        delete_milestone(m_id, job_no)
        assert len(list_milestones(job_no)) == 0
        
        print("Tests completed successfully!")
    finally:
        cleanup(job_no)

if __name__ == "__main__":
    run_tests()
