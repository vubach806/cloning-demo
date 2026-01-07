"""Initialize database tables."""

from database.postgres import create_all_tables

if __name__ == "__main__":
    print("Creating all database tables...")
    try:
        create_all_tables()
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
