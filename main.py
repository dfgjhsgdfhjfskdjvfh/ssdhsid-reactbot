
from flask import Flask
import threading
import subprocess
import time

app = Flask(__name__)

@app.route('/')
def status():
    return 'alive', 200

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def run_script_with_restart():
    while True:
        try:
            print("Starting run.py...")
            process = subprocess.Popen(['python3', 'bot.py'])
            process.wait()
            print("run.py crashed or exited. Restarting in 2 seconds...")
            time.sleep(2)
        except Exception as e:
            print(f"Error while running bot.py: {e}")
            time.sleep(2)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    time.sleep(1)
    threading.Thread(target=run_script_with_restart).start()
