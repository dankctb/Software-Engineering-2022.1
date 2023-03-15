from flask import Flask, request, render_template, redirect, url_for, jsonify
import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb
import datetime
import pytesseract
from PIL import Image
import io
from sympy import latex

app = Flask(__name__)

@app.route('/')
def main_web():
    return render_template('signup.html')

@app.route('/sign_up', methods=['POST'])
def sign_up():
    # Get the form data
    username = request.form['username']
    password = request.form['password']
    billing = request.form['billing']
    email = request.form['email']
        
    # Connect to the database
    conn = MySQLdb.connect(host="localhost", user="root", passwd="29122002", db="math_expression")
    cursor = conn.cursor()
    # Check if the username already exists in the database
    sql = "SELECT * FROM User WHERE name=%s"
    values = (username)
    cursor.execute(sql, values)

    if cursor.fetchone() is not None:
        # If a row with the same username exists, notify the user to change their input
        error = "Username already exists. Please choose a different username."
        return render_template('signup.html', error=error)
    else:
        # Insert the new user into the database
        sql = "INSERT INTO User (email , name, password, billing_infor) VALUES (%s,%s, %s, %s)"
        values = (email, username, password, billing)
        cursor.execute(sql, values)
        cursor = conn.cursor()

        #retrive the lastest user_id
        cursor.execute("SELECT LAST_INSERT_ID()")
        user_id = cursor.fetchone()[0]
        
        #set up transaction infor
        if billing == '0':
            max_num_photos = 50
        if billing == '1':
            max_num_photos = 1000
        else:
            max_num_photos = 2 ** 31 - 1

        # Insert the transaction into the database
        sql = "INSERT INTO Transaction ( user_id, Max_number_of_photos, price, timestamp_start) VALUES (%s, %s, %s, %s)"
        values = (user_id, max_num_photos, billing, datetime.datetime.now())
        cursor.execute(sql, values)

        # Commit the changes to the database
        conn.commit()

        # Close the database connection
        conn.close()

        # Redirect the user to the login page
        return redirect(url_for('login'))

@app.route('/login') #used in sign up page
def login():
    return render_template('login.html')

#---------------------------------------------- new phase, the log in check
@app.route('/cre_check', methods=['POST'])
def cre_check():
    # Connect to the database
    conn = MySQLdb.connect(host="localhost", user="root", passwd="29122002", db="math_expression")
    cursor = conn.cursor()

    # Get the user's credentials from the form
    username = request.form['username']
    password = request.form['password']

    # Check if the user exists in the database
    sql = "SELECT * FROM User WHERE name=%s AND password=%s"
    values = (username, password)
    cursor.execute(sql, values)
    user = cursor.fetchone()

    # If the user exists, redirect to the main page
    if user:
        global ongoing_user_id
        ongoing_user_id = user[0]
        user_id = ongoing_user_id

        #check current available photos
        sql = "SELECT Max_number_of_photos FROM math_expression.Transaction WHERE user_id = %s"
        values = (user_id)
        cursor.execute(sql, values)

        current_number_photo = cursor.fetchone()[0]
        if current_number_photo == 0 :
            # Commit the changes to the database and close
            conn.commit()
            conn.close()
            return render_template('new_transaction.html')
        # Commit the changes to the database and close
        conn.commit()
        conn.close()

        return render_template('ocr.html')

    # If the user doesn't exist or the password is incorrect, display an error message
    error = "Invalid username or password ahihi."
    return render_template('login.html', error=error)

#--------------------------------------------------------------------math ocr phase

@app.route('/process', methods=['POST'])
def process():
    # Connect to the database
    conn = MySQLdb.connect(host="localhost", user="root", passwd="29122002", db="math_expression")
    cursor = conn.cursor()
    # Get the photo_name and the image from the form data
    photo_url = request.form['photo_name']
    image = request.files['image'].read()
    user_id =  ongoing_user_id 

    # Convert the image to text using Tesseract OCR
    text = pytesseract.image_to_string(Image.open(io.BytesIO(image)))

    # Convert the text to LaTeX using SymPy
    latex_code = latex(text)

    #update photo table in database
    sql = "INSERT INTO Photo ( user_id, photo_url, created_date, latex_result) VALUES (%s, %s, %s, %s)"
    values = (user_id, photo_url, datetime.datetime.now(), latex_code)
    cursor.execute(sql, values)

    #check current available photos
    sql = "SELECT Max_number_of_photos FROM math_expression.Transaction WHERE user_id = %s"
    values = (user_id)
    cursor.execute(sql, values)

    current_number_photo = cursor.fetchone()[0]

    current_number_photo = current_number_photo - 1
    sql = "UPDATE Transaction SET  Max_number_of_photos = %s WHERE user_id = %s;"
    values = (current_number_photo,user_id)
    cursor.execute(sql, values)

    # Commit the changes to the database and close
    conn.commit()
    conn.close()

    # Return the LaTeX code as a response
    return jsonify({'latex_code': latex_code})
#---------------------------------------------------------------------new_transaction
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    conn = MySQLdb.connect(host="localhost", user="root", passwd="29122002", db="math_expression")
    cursor = conn.cursor()

    billing = request.form['billing']
    user_id = ongoing_user_id 


    #set up transaction infor
    if billing == '0':
        max_num_photos = 50
    if billing == '1':
        max_num_photos = 1000
    else:
        max_num_photos = 2**31 - 1

    # Insert the transaction into the database
    sql = "UPDATE Transaction SET Max_number_of_photos = %s, timestamp_start = %s , price = %s WHERE user_id = %s;"
    values = (max_num_photos,  datetime.datetime.now(), billing , user_id)
    cursor.execute(sql, values)

    # Commit the changes to the database and close
    conn.commit()
    conn.close()

    return render_template('ocr.html')


@app.route('/check_history', methods=[ 'POST'])
def check_history(): 
    # Connect to the database
    conn = MySQLdb.connect(host="localhost", user="root", passwd="29122002", db="math_expression")
    cursor = conn.cursor()
    user_id = ongoing_user_id

    #check current available photos
    sql = "SELECT Photo.photo_url, Photo.latex_result, Photo.created_date , Transaction.Max_number_of_photos \
    FROM Photo, Transaction \
    WHERE Photo.user_id = %s && Transaction.user_id = %s"
    values = (user_id,user_id)
    cursor.execute(sql, values)

    # Fetch the results of the query
    results = cursor.fetchall()
    print(results)

    # Commit the changes to the database and close
    conn.commit()
    conn.close()
    return render_template('history.html', results=results)
if __name__ == '__main__':
    app.run(debug=True)
