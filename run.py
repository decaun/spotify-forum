#$env:FLASK_APP=".\run.py"
#$env:FLASK_DEBUG=1
#$env:FLASK_RUN_PORT=80 - bi sike yaramadi
#flask run --host=127.0.0.1 --port=80
#python -m flask run --host=127.0.0.1 --port=80

from main import app

if __name__=='__main__':
    app.run(debug=True,host = '127.0.0.1',port=80)
