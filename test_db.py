import mysql.connector

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Chin@2006",
        database="placement_management"
    )
    print("Connected successfully!")
except mysql.connector.Error as err:
    print("Error:", err)