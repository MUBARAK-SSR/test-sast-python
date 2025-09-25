import os
from flask import request, Flask

app = Flask(__name__)

@app.route("/ping")
def ping():
    host = request.args.get("host")
    # Vulnérable : injection possible si l'utilisateur passe ; rm -rf /
    return os.popen(f"ping -c 1 {host}").read()


def dangerous_eval(user_input):
    # Intentional vuln: using eval on user-controlled input
    return eval(user_input)
