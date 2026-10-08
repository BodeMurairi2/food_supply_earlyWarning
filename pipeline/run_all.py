"""Run every pipeline step in order: python pipeline/run_all.py"""

import step01_target
import step02_rainfall
import step03_temperature
import step04_prices
import step05_sas
import step06_build_dataset

for step in [step01_target, step02_rainfall, step03_temperature, step04_prices, step05_sas, step06_build_dataset]:
    print(f"\n=== {step.__name__} ===")
    step.main()
