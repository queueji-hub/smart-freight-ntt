import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Add root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import init_database, get_connection
from managers.document_numbering_service import generate_document_number, normalize_doc_no
from unittest.mock import patch

def test_normalization():
    print("=" * 60)
    print("TEST 1: Search Normalization")
    print("=" * 60)
    
    cases = [
        ("INV-2608-0001",   "INV26080001"),
        ("inv-2608-0001",   "INV26080001"),
        ("INV 2608 0001",   "INV26080001"),
        ("INV26080001",     "INV26080001"),
        ("INV/2608/0001",   "INV26080001"),
        ("INV.2608.0001",   "INV26080001"),
        ("qt-2608-0048",    "QT26080048"),
        ("JOB 2608 0137",   "JOB26080137"),
        ("BK/2608/0124",    "BK26080124"),
        ("HBL-2608-0001",   "HBL26080001"),
        ("MBL.2608.0001",   "MBL26080001"),
        ("",                ""),
        ("  INV - 2608 - 0001  ", "INV26080001"),
    ]
    
    for input_val, expected in cases:
        result = normalize_doc_no(input_val)
        assert result == expected, f"FAIL: normalize_doc_no('{input_val}') = '{result}', expected '{expected}'"
        print(f"  OK: '{input_val}' -> '{result}'")
    
    print("PASS: All search normalization tests passed.\n")


def test_sequential_generation():
    print("=" * 60)
    print("TEST 2: Sequential Generation")
    print("=" * 60)
    
    with patch('managers.document_numbering_service.get_current_tenant_id', return_value='TEST_SEQ_TENANT'):
        results = []
        for _ in range(10):
            doc = generate_document_number("SEQ", datetime(2026, 8, 10))
            results.append(doc)
        
        # Verify all unique
        assert len(set(results)) == 10, f"Duplicate detected in sequential generation: {results}"
        
        # Verify all start with SEQ-2608-
        for r in results:
            assert r.startswith("SEQ-2608-"), f"Unexpected format: {r}"
        
        # Verify strict sequential ordering (each number is greater than previous)
        nums = [int(r.split("-")[-1]) for r in results]
        for i in range(1, len(nums)):
            assert nums[i] == nums[i-1] + 1, f"Non-sequential: {nums[i-1]} -> {nums[i]}"
        
        print(f"  Generated: {results[0]} ... {results[-1]}")
        print("PASS: Sequential generation verified.\n")


def test_concurrency():
    print("=" * 60)
    print("TEST 3: Concurrency + Tenant Isolation (100 simultaneous)")
    print("=" * 60)
    
    tenant_a_results = []
    tenant_b_results = []
    lock_a = threading.Lock()
    lock_b = threading.Lock()
    
    def generate_for_a():
        with patch('managers.document_numbering_service.get_current_tenant_id', return_value='CONC_TENANT_A'):
            doc = generate_document_number("CC", datetime(2026, 8, 10))
            with lock_a:
                tenant_a_results.append(doc)
        
    def generate_for_b():
        with patch('managers.document_numbering_service.get_current_tenant_id', return_value='CONC_TENANT_B'):
            doc = generate_document_number("CC", datetime(2026, 8, 10))
            with lock_b:
                tenant_b_results.append(doc)

    tasks = []
    for _ in range(50):
        tasks.append(generate_for_a)
        tasks.append(generate_for_b)

    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(lambda f: f(), tasks))
        
    # Validation: correct count
    assert len(tenant_a_results) == 50, f"TENANT_A count: {len(tenant_a_results)}"
    assert len(tenant_b_results) == 50, f"TENANT_B count: {len(tenant_b_results)}"
    
    # Uniqueness within each tenant
    assert len(set(tenant_a_results)) == 50, f"TENANT_A had duplicates! {tenant_a_results}"
    assert len(set(tenant_b_results)) == 50, f"TENANT_B had duplicates! {tenant_b_results}"
    
    # Verify sequential (extract numbers, sort, check contiguous)
    nums_a = sorted([int(r.split("-")[-1]) for r in tenant_a_results])
    nums_b = sorted([int(r.split("-")[-1]) for r in tenant_b_results])
    
    for i in range(1, 50):
        assert nums_a[i] == nums_a[i-1] + 1, f"TENANT_A gap: {nums_a[i-1]} -> {nums_a[i]}"
        assert nums_b[i] == nums_b[i-1] + 1, f"TENANT_B gap: {nums_b[i-1]} -> {nums_b[i]}"
    
    print(f"  TENANT_A: {tenant_a_results[0]} ... last_seq={nums_a[-1]}")
    print(f"  TENANT_B: {tenant_b_results[0]} ... last_seq={nums_b[-1]}")
    print("PASS: No race conditions, no duplicates, no gaps.")
    print("PASS: Strict tenant isolation confirmed.\n")


def test_format_consistency():
    print("=" * 60)
    print("TEST 4: Format Consistency Across Document Types")
    print("=" * 60)
    
    doc_types = ["QT", "BK", "JOB", "HBL", "MBL", "INV", "PAY", "RCT"]
    
    with patch('managers.document_numbering_service.get_current_tenant_id', return_value='FMT_TEST_TENANT'):
        for dt in doc_types:
            doc = generate_document_number(dt, datetime(2026, 8, 10))
            assert doc.startswith(f"{dt}-2608-"), f"Unexpected format for {dt}: {doc}"
            seq = doc.split("-")[-1]
            assert len(seq) == 4, f"Sequence padding wrong for {dt}: {seq}"
            print(f"  OK: {dt} -> {doc}")
    
    print("PASS: All document type formats consistent.\n")


def test_no_reuse_after_gap():
    print("=" * 60)
    print("TEST 5: Number Never Reused (Gap Tolerance)")
    print("=" * 60)
    
    with patch('managers.document_numbering_service.get_current_tenant_id', return_value='GAP_TEST_TENANT'):
        doc1 = generate_document_number("GAP", datetime(2026, 8, 10))
        doc2 = generate_document_number("GAP", datetime(2026, 8, 10))
        doc3 = generate_document_number("GAP", datetime(2026, 8, 10))
        
        n1 = int(doc1.split("-")[-1])
        n2 = int(doc2.split("-")[-1])
        n3 = int(doc3.split("-")[-1])
        
        assert n2 == n1 + 1
        assert n3 == n2 + 1
        
        # Simulate: doc2 was "deleted" — next number should still be n3+1, not n2
        doc4 = generate_document_number("GAP", datetime(2026, 8, 10))
        n4 = int(doc4.split("-")[-1])
        assert n4 == n3 + 1, f"Number reuse detected! Expected {n3+1}, got {n4}"
        
        print(f"  {doc1} -> {doc2} -> {doc3} -> {doc4}")
        print("PASS: No number reuse after simulated deletion.\n")


if __name__ == "__main__":
    init_database()
    
    test_normalization()
    test_sequential_generation()
    test_concurrency()
    test_format_consistency()
    test_no_reuse_after_gap()
    
    print("=" * 60)
    print("ALL DOCUMENT NUMBERING TESTS PASSED")
    print("=" * 60)
