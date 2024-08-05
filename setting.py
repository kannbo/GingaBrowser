from flask import *

app = Flask(__name__)

@app.route("/")
def hello_world():
    return """<title>Ginga Browser setting</title><h1>Gingaをセッティング
<a href="test">aaa</a>"""

@app.route("/test")
def hello_wosrld():
    return "<title>Ginga Browser setting</title><h1>Gingaをセッティング"
app.run(port=8264)
