import multiprocessing
import subprocess

def run_main():
    subprocess.run(["python", "main.py"])

def run_dashboard():
    subprocess.run(["python", "dashboard.py"])

if __name__ == "__main__":
    # create two processes  
    main_process = multiprocessing.Process(target=run_main)
    dashboard_process = multiprocessing.Process(target=run_dashboard)

    # start the processes
    main_process.start()
    dashboard_process.start()

    # wait for the processes to finish
    main_process.join()
    dashboard_process.join()
