

if __name__ == "__main__":
    from sparrow.base.app import Sparrow
    app = Sparrow({
        "APPLICATION_ROOT": "/",
        "SERVER_NAME": None,
        "PREFERRED_URL_SCHEME": "http",
    })


    @app.route("/hello", methods=["GET"])
    def hello():
        return "Hello World!", 200, {"Content-Type": "text/plain"}
    app.run()