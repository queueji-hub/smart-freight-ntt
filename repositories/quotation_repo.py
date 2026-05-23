from database.connection import get_connection

def create_quotation_db(data):

    with get_connection() as conn:

        cur = conn.execute("""
            INSERT INTO quotations (
                job_type,
                customer_name,
                quotation_date
            )
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            data["job_type"],
            data["customer_name"],
            data["quotation_date"]
        ))

        qid = cur.fetchone()["id"]

        for i, item in enumerate(data["items"]):
            conn.execute("""
                INSERT INTO quotation_items (
                    quotation_id,
                    description,
                    price,
                    currency,
                    sort_order
                )
                VALUES (%s,%s,%s,%s,%s)
            """, (
                qid,
                item["description"],
                item["price"],
                item.get("currency", "USD"),
                i
            ))

        conn.commit()

    return qid


def get_quotation(qid):
    with get_connection() as conn:
        q = conn.execute("SELECT * FROM quotations WHERE id=%s", (qid,)).fetchone()
        items = conn.execute(
            "SELECT * FROM quotation_items WHERE quotation_id=%s ORDER BY sort_order",
            (qid,)
        ).fetchall()

    return {
        "quotation": dict(q),
        "items": [dict(i) for i in items]
    }