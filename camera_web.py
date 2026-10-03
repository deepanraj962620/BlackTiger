from flask import Flask, render_template, request
app = Flask(__name__)

@app.route("/")
def index():
    theme = request.args.get("theme", "birthday")
    if theme not in {"birthday", "festival", "marriage"}:
        theme = "birthday"
    title = request.args.get("title", "Camera Memory")
    message = request.args.get(
        "message",
        "This page requests camera permission and can record video only after you approve."
    )
    return render_template("camera.html", theme=theme, title=title, message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
