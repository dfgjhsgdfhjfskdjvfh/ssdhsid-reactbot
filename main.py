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
            print("Starting bot.py...")
            process = subprocess.Popen(['python3', 'bot.py'])
            start_time = time.time()

            while True:
                time.sleep(1)
                if process.poll() is not None:
                    print("bot.py crashed or exited.")
                    break
                # Restart if running for more than 10 minutes
                if time.time() - start_time >= 600:
                    print("10 minutes passed. Restarting bot.py...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break

            print("Restarting bot.py in 2 seconds...")
            time.sleep(2)

        except Exception as e:
            print(f"Error while running bot.py: {e}")
            time.sleep(2)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    time.sleep(1)
    threading.Thread(target=run_script_with_restart).start()

