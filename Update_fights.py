import subprocess
import sys

python = sys.executable  # ensures same Python version

print("Running UFC scraper...")
subprocess.run([python, "UFC_scraper.py"], check=True)

print("Running transformer...")
subprocess.run([python, "Transformer.py"], check=True)

print("Running data cleaning(1)...")
subprocess.run([python, "data_clean.py"], check=True)

print("Running data cleaning(2)...")
subprocess.run([python, "part_2/part_2_data_prep.py"], check=True)
print("Done.")
