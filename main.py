import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMPROVEMENT_SCRIPT = os.path.join(BASE_DIR, "part_2/improvement_velocity.py")
PREDICTION_SCRIPT = os.path.join(BASE_DIR, "part_2/Prediction_model.py")


def run_script(path):
    subprocess.run([sys.executable, path])
if __name__ == "__main__":
    while True:
        print("\n==============================")
        print("UFC DATA SCIENCE PROJECT")
        print("==============================")
        print("1 - Run Career Improvement Model/Quality")
        print("2 - Run Fight Predictor")
        print("0 - Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            run_script(IMPROVEMENT_SCRIPT)

        elif choice == "2":
            run_script(PREDICTION_SCRIPT)

        elif choice == "0":
            print("Exiting.")
            break

        else:
            print("Invalid option.")