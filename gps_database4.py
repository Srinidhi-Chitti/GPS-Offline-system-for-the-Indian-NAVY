import sqlite3
import time
from datetime import datetime, timedelta


class GPSDatabase:
    def __init__(self, db_name="gps_coordinates (1).db"):
        """
        Initialize the GPSDatabase class and connect to the database.

        Args:
            db_name (str): Name of the database file. Defaults to "gps_coordinates.db".
        """
        self.db_name = db_name
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        """
        Create tables for storing phone numbers and GPS coordinates if they do not already exist.
        """
        # Create phone_numbers table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS phone_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE
            )
        """)

        # Create coordinates table with a foreign key reference to phone_numbers
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS coordinates (
                phone_number_id INTEGER,
                timestamp TEXT,
                latitude REAL,
                longitude REAL,
                date TEXT,
                FOREIGN KEY (phone_number_id) REFERENCES phone_numbers(id)
            )
        """)
        self.connection.commit()

    def insert_coordinates(self, phone_number, time_value, lat, lon):
        """
        Insert GPS coordinates and associate them with a phone number. Updates the timestamp by 1 minute for each new entry.

        Args:
            phone_number (str): Phone number to associate with the coordinates.
            time_value (str): Initial timestamp for the coordinates.
            lat (float): Latitude value.
            lon (float): Longitude value.

        Returns:
            int: ID of the phone number in the database.
        """
        with sqlite3.connect(self.db_name, check_same_thread=False) as connection:
            cursor = connection.cursor()
            date = time.strftime("%Y-%m-%d")  # Get the current date

            # Insert phone number if it does not exist
            cursor.execute(
                "INSERT OR IGNORE INTO phone_numbers (phone_number) VALUES (?)",
                (phone_number,)
            )

            # Retrieve the ID of the phone number
            cursor.execute(
                "SELECT id FROM phone_numbers WHERE phone_number = ?",
                (phone_number,)
            )
            phone_number_id = cursor.fetchone()[0]

            # Retrieve the latest timestamp for the same phone number and date
            cursor.execute("""
                SELECT timestamp
                FROM coordinates
                WHERE phone_number_id = ? AND date = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (phone_number_id, date))
            last_timestamp_row = cursor.fetchone()

            if last_timestamp_row:
                last_timestamp = datetime.strptime(last_timestamp_row[0], "%H:%M:%S")
                new_timestamp = last_timestamp + timedelta(minutes=1)
            else:
                # Use the provided timestamp if no previous record exists
                new_timestamp = datetime.strptime(time_value, "%H:%M:%S")

            # Insert GPS coordinates with the updated timestamp
            cursor.execute("""
                INSERT INTO coordinates (phone_number_id, latitude, longitude, timestamp, date)
                VALUES (?, ?, ?, ?, ?)
            """, (phone_number_id, lat, lon, new_timestamp.strftime("%H:%M:%S"), date))
            connection.commit()
            return phone_number_id

    def get_coordinates_for_id_and_date(self, phone_number_id, date):
        """
        Retrieve GPS coordinates for a specific phone number ID and date, updating timestamps to ensure uniqueness.

        Args:
            phone_number_id (int): ID of the phone number.
            date (str): Date to filter the coordinates.

        Returns:
            list: List of tuples containing latitude, longitude, and updated timestamps.
        """
        self.cursor.execute("""
            SELECT latitude, longitude, timestamp 
            FROM coordinates
            WHERE phone_number_id = ? AND date = ?
            ORDER BY timestamp
        """, (phone_number_id, date))
        results = self.cursor.fetchall()

        if not results:
            return []

        updated_results = []
        seen_timestamps = set()

        for i, (lat, lon, timestamp) in enumerate(results):
            # Parse the timestamp
            ts = datetime.strptime(timestamp, "%H:%M:%S")

            # Ensure unique timestamps by adding 1 minute if needed
            while ts.strftime("%H:%M:%S") in seen_timestamps:
                ts += timedelta(minutes=1)

            updated_results.append((lat, lon, ts.strftime("%H:%M:%S")))
            seen_timestamps.add(ts.strftime("%H:%M:%S"))

        return updated_results

    def get_all_phone_numbers_with_ids(self):
        """
        Retrieve all phone numbers and their corresponding IDs.

        Returns:
            list: List of tuples containing IDs and phone numbers.
        """
        self.cursor.execute("SELECT id, phone_number FROM phone_numbers")
        return self.cursor.fetchall()

    def get_all_dates_for_number(self, phone_number_id):
        """
        Retrieve all distinct dates for a specific phone number ID.

        Args:
            phone_number_id (int): ID of the phone number.

        Returns:
            list: List of dates (as strings) associated with the phone number.
        """
        self.cursor.execute("""
            SELECT DISTINCT date 
            FROM coordinates 
            WHERE phone_number_id = ?
        """, (phone_number_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_phone_number_by_id(self, phone_number_id):
        """
        Retrieve the phone number corresponding to a specific ID.

        Args:
            phone_number_id (int): ID of the phone number.

        Returns:
            str: Phone number associated with the ID.
        """
        self.cursor.execute("""
            SELECT phone_number 
            FROM phone_numbers 
            WHERE id = ?
        """, (phone_number_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
