import sqlite3
import logging
import hashlib
from typing import Optional


class Profile:
    def __init__(self, image_list: list, profile_text: str):
        self.__hash = None
        self.__name = None
        self.__age = None
        self.__descriptions = None

        items = profile_text.split(',')
        if len(items) > 1:
            self.__name = items[0]
            self.__age = items[1]
            self.__descriptions = ",".join(items[2: ])
            self.__hash = self.gen_hash()

    def __repr__(self):
        return (f"Profile(\n"
                f"\thash={self.get_hash()}"
                f"\tname={self.get_name()},\n"
                f"\tage={self.get_age()},\n"
                f"\tdescriptions={self.get_descriptions()}\n)")

    def gen_hash(self):
        # Combine the fields into a single string
        combined_string = f"{self.get_name()}{self.get_age()}{self.get_descriptions()}"

        # Encode the string to bytes (required for hashing)
        combined_bytes = combined_string.encode('utf-8')

        # Create a SHA-256 hash object
        hash_object = hashlib.sha256()

        # Update the hash object with the combined bytes
        hash_object.update(combined_bytes)

        # Get the hexadecimal representation of the hash
        hash_hex = hash_object.hexdigest()
        return hash_hex

    def save_to_db(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> bool:
        if Profile.create_table(cursor=cursor):
            return self.insert(cursor=cursor, conn=conn)
        return False

    @staticmethod
    def create_table(cursor: sqlite3.Cursor) -> bool:
        try:
            cursor.execute(Profile.__create_table_sql_re())
            return True
        except Exception as e:
            logging.error(f"SQL REQ ERROR: {str(e)}")
            return False

    def insert(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> bool:
        if self.get_name() and self.get_name() and self.get_descriptions():
            try:
                cursor.execute(Profile.__insert_into_table_sql_req(),
                               (
                                self.get_hash(),
                                self.get_name(),
                                self.get_age(),
                                self.get_descriptions()
                               )
                )
                conn.commit()
                return True
            except Exception as e:
                logging.error(f"SQL REQ ERROR: {str(e)}")
                return False
        else:
            return False

    @staticmethod
    def find_profile_with_hash(cursor: sqlite3.Cursor, conn: sqlite3.Connection, hash) -> Optional[list]:
        try:
            cursor.execute(Profile.__select_record_with_hash(), (hash,))
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"SQL REQ ERROR: {str(e)}")
            return None

    @staticmethod
    def __create_table_sql_re() -> str:
        return """
        CREATE TABLE IF NOT EXISTS PROFILES (
            hash TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            age INTEGER,
            descriptions TEXT
        );
        """

    @staticmethod
    def __insert_into_table_sql_req() -> str:
        return """
        INSERT INTO PROFILES (hash, name, age, descriptions)
        VALUES (?, ?, ?, ?);
        """

    @staticmethod
    def __select_record_with_hash() -> str:
        return """SELECT * FROM PROFILES WHERE hash = ?;"""

    def get_hash(self):
        return self.__hash

    def get_name(self):
        return self.__name

    def get_age(self):
        return self.__age

    def get_descriptions(self):
        return self.__descriptions

