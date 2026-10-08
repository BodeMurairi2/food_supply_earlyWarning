#!/usr/bin/env bash
# Commit the project in separate categories, then push to GitHub.
# Run from the repository root: bash push.sh
set -e

# 1. Project setup
git add .gitignore requirements.txt README.md
git commit -m "chore: project setup (gitignore, requirements, readme)"

# 2. Temperature data: download, processing and validation
git add download_era5_land.py process_temperature.py validate_temperature.py download_temp_data.py
git commit -m "feat(data): ERA5-Land temperature download, district aggregation and station validation"

# 3. Feature pipeline (steps 1-6)
git add pipeline/
git commit -m "feat(pipeline): target and feature extraction pipeline (CFSVA, rainfall, temperature, prices, SAS)"

# 4. Documentation
git add documentation/
git commit -m "docs: pipeline and temperature data documentation"

# 5. Final modelling dataset
git add food_security_dataset.csv
git commit -m "data: district-year food security dataset (2006-2026)"

# 6. Analysis notebook
git add analysis.ipynb
git commit -m "feat(analysis): feature selection and baseline model notebook"

git log --oneline
git push -u origin main
