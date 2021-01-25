from flask import Flask, request

app = Flask(__name__)


@app.route("/<name>")
def home(name):
    return "hello %s query : %s" % (name, request.args.get('name', "default"))
