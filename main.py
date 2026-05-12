import sys
import os
print("STARTING MAIN")

def get_path(path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

from part_2 import improvement_velocity
from part_2 import Prediction_model

def run_improvement():
    improvement_velocity.main()

def run_prediction():
    Prediction_model.main()

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
            run_improvement()

        elif choice == "2":
            run_prediction()

        elif choice == "0":
            print("Exiting.")
            break

        else:
            print("Invalid option.")