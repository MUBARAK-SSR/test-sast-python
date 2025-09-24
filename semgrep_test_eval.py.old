import sqlite3

def get_user_data_vulnerable(user_id):
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    # Vulnerable to SQL Injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    data = cursor.fetchone()
    conn.close()
    return data

def get_user_data_secure(user_id):
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    # Secure using parameterized queries
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data

# Testing for SQL Injection
# Example of a malicious input
malicious_input = "1 OR 1=1"
print(f"Vulnerable query result for '{malicious_input}': {get_user_data_vulnerable(malicious_input)}")
print(f"Secure query result for '{malicious_input}': {get_user_data_secure(malicious_input)}")

def dangerous_eval(user_input):
    #Intentional vuln: using eval on user-controlled input
    return eval(user_input)
