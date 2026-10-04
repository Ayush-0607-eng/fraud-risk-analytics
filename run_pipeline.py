"""
Runs the complete analytics pipeline end to end, in order:

  1. Generate synthetic raw data
  2. Clean and validate data
  3. Engineer behavioral risk features
  4. Apply rule-based fraud detection
  5. Apply Isolation Forest anomaly detection
  6. Blend scores, run statistical tests, assign risk categories
  7. Generate charts
  8. Export the Power BI-ready dataset
  9. Build the SQLite analytics database

Usage: python run_pipeline.py
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "python")

STEPS = [
    "01_data_generation.py",
    "02_data_cleaning.py",
    "03_feature_engineering.py",
    "04_rule_based_detection.py",
    "05_anomaly_detection.py",
    "06_statistical_analysis.py",
    "07_generate_visuals.py",
    "08_export_powerbi.py",
    "00_build_database.py",
]


def main():
    for step in STEPS:
        path = os.path.join(SCRIPT_DIR, step)
        print(f"\n{'=' * 60}\nRunning {step}\n{'=' * 60}")
        result = subprocess.run([sys.executable, path], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"\nPipeline stopped: {step} failed with exit code {result.returncode}")
            sys.exit(1)
    print(f"\n{'=' * 60}\nPipeline completed successfully.\n{'=' * 60}")


if __name__ == "__main__":
    main()
