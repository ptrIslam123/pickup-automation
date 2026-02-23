import sqlite3
import logging
from profile_parser import Profile
from typing import Optional


class ProfilesDB:
    def __init__(self, db_path: str):
        self.__db_path = db_path
        self.__conn = sqlite3.connect(db_path)
        self.__cursor = self.__conn.cursor()

    def create_table(self) -> bool:
        try:
            self.__cursor.execute(Profile.__create_table_sql_re())
            return True
        except Exception as e:
            logging.error(f"SQL REQ ERROR: {str(e)}")
            return False

    def insert(self, profile: Profile):
        try:
            self.__cursor.execute(Profile.__insert_into_table_sql_req(),
                            (
                            profile.get_hash(),
                            profile.get_name(),
                            profile.get_age(),
                            profile.get_location(),
                            self.get_descriptions()
                            )
            )
            self.__conn.commit()
        except Exception as e:
            logging.error(f"SQL REQ ERROR: {str(e)}")

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

