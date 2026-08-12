import psycopg2
import os

def run_migration():
    print("Connecting to Supabase production database...")
    try:
        conn = psycopg2.connect(
            host="aws-1-ap-southeast-1.pooler.supabase.com",
            port=5432,
            dbname="postgres",
            user="postgres.mziinbzvgphrqafxityk",
            password="E+tA.5@-_FZLMt7",
            sslmode="require"
        )
        print("Connected successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        sql_file_path = os.path.join(os.path.dirname(__file__), "phase29_supabase_migration.sql")
        with open(sql_file_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        with conn.cursor() as cur:
            print("Applying migration script...")
            cur.execute(sql_script)
            conn.commit()
            print("Migration applied successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Migration execution failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
