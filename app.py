from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from aws_config import get_s3_client

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "super_secure_cloud_secret_key")

# AWS S3 Bucket Name
S3_BUCKET_NAME = os.getenv("S3_BUCKET", "secure-cloud-document-vernita-2026")


def create_tables():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            s3_path TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


create_tables()

def get_db_connection():

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    return conn



# LOGIN

@app.route("/", methods=["GET","POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))


    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]


        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        conn.close()


        if user and check_password_hash(user["password"],password):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("dashboard"))

        else:

            flash("Invalid username or password","danger")


    return render_template("login.html")





# REGISTER

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method=="POST":

        username=request.form["username"]

        password=request.form["password"]

        hashed=generate_password_hash(password)


        conn=get_db_connection()


        try:

            conn.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username,hashed)
            )

            conn.commit()

            flash("Registration successful","success")

            return redirect(url_for("login"))


        except sqlite3.IntegrityError:

            flash("Username already exists","danger")


        finally:

            conn.close()


    return render_template("register.html")





# DASHBOARD

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(url_for("login"))


    conn=get_db_connection()


    documents=conn.execute(

        "SELECT * FROM documents WHERE user_id=? ORDER BY id DESC",

        (session["user_id"],)

    ).fetchall()


    conn.close()


    return render_template(

        "dashboard.html",

        username=session["username"],

        documents=documents,

        total_docs=len(documents),

        storage="AWS S3",

        recent=min(len(documents),5)

    )





# DOCUMENTS PAGE

@app.route("/documents")
def documents():

    if "user_id" not in session:

        return redirect(url_for("login"))


    conn=get_db_connection()


    docs=conn.execute(

        "SELECT * FROM documents WHERE user_id=? ORDER BY id DESC",

        (session["user_id"],)

    ).fetchall()


    conn.close()


    return render_template(

        "documents.html",

        documents=docs

    )






# UPLOAD

@app.route("/upload", methods=["GET","POST"])
def upload_file():


    if "user_id" not in session:

        return redirect(url_for("login"))



    if request.method=="GET":

        return render_template("upload.html")



    file=request.files.get("file")


    if not file or file.filename=="":

        flash("Please select a file","danger")

        return redirect(url_for("upload_file"))



    filename=secure_filename(file.filename)



    s3=get_s3_client()



    if s3:

        try:

            s3.upload_fileobj(

                file,

                S3_BUCKET_NAME,

                filename

            )



            conn=get_db_connection()


            conn.execute(

                """
                INSERT INTO documents
                (user_id,filename,s3_path)
                VALUES(?,?,?)
                """,

                (
                    session["user_id"],
                    filename,
                    filename
                )

            )


            conn.commit()

            conn.close()



            flash(
                "Document uploaded successfully!",
                "success"
            )


            return redirect(url_for("dashboard"))



        except Exception as e:

            return f"Upload Error: {e}"



    return "AWS S3 connection failed"







# DOWNLOAD

@app.route("/download/<filename>")
def download_file(filename):


    if "user_id" not in session:

        return redirect(url_for("login"))



    s3=get_s3_client()


    try:

        url=s3.generate_presigned_url(

            "get_object",

            Params={

                "Bucket":S3_BUCKET_NAME,

                "Key":filename

            },

            ExpiresIn=300

        )


        return redirect(url)



    except Exception as e:

        return f"Download error: {e}"








# DELETE

@app.route("/delete/<int:doc_id>",methods=["POST"])
def delete_file(doc_id):


    if "user_id" not in session:

        return redirect(url_for("login"))



    conn=get_db_connection()


    doc=conn.execute(

        """
        SELECT * FROM documents 
        WHERE id=? AND user_id=?
        """,

        (
            doc_id,
            session["user_id"]
        )

    ).fetchone()



    if doc:


        s3=get_s3_client()


        if s3:

            s3.delete_object(

                Bucket=S3_BUCKET_NAME,

                Key=doc["filename"]

            )


        conn.execute(

            "DELETE FROM documents WHERE id=?",

            (doc_id,)

        )


        conn.commit()



    conn.close()


    flash(
        "Document deleted successfully",
        "success"
    )


    return redirect(url_for("dashboard"))






# PROFILE

@app.route("/profile")
def profile():

    if "user_id" not in session:

        return redirect(url_for("login"))


    return render_template(

        "profile.html",

        username=session["username"]

    )





# ACTIVITY

@app.route("/activity")
def activity():

    if "user_id" not in session:

        return redirect(url_for("login"))


    return render_template(

        "activity.html"

    )





# SETTINGS

@app.route("/settings")
def settings():

    if "user_id" not in session:

        return redirect(url_for("login"))


    return render_template(

        "settings.html",

        username=session["username"]

    )





# ANALYTICS

@app.route("/analytics")
def analytics():

    if "user_id" not in session:

        return redirect(url_for("login"))


    conn=get_db_connection()


    total=conn.execute(

        "SELECT COUNT(*) FROM documents WHERE user_id=?",

        (session["user_id"],)

    ).fetchone()[0]


    conn.close()



    return render_template(

        "analytics.html",

        username=session["username"],

        total_docs=total

    )






# ABOUT

@app.route("/about")
def about():

    if "user_id" not in session:

        return redirect(url_for("login"))


    return render_template("about.html")






# LOGOUT

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)