from pickwise.app import app


if __name__ == "__main__":
    # Entry point so that `python app.py` from the project root starts the Flask server.
    app.run(host="0.0.0.0", port=5000, debug=True)

