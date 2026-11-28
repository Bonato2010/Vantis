import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import unittest

loader = unittest.TestLoader()
suite = unittest.TestSuite()

test_files = [
    "tests.test_fase1_foundation",
    "tests.test_fase2_orchestration",
    "tests.test_fase3_multichannel",
    "tests.test_fase4_discovery_portal1",
    "tests.test_fase5_audiovisual",
    "tests.test_fase6_distribution",
    "tests.test_fase7_dashboard",
    "tests.test_fase8_vantis_pipeline",
    "tests.test_fase9_agent_architecture",
    "tests.test_fase10_audiovisual_pipeline",
    "tests.test_fase11_pilot_channels_and_dashboard",
    "tests.test_fase12_deployment_and_editorial_training",
    "tests.test_fase13_massive_audiovisual_learning",
    "tests.test_fase14_real_learning_and_zero_simulation"
]

for tf in test_files:
    mod_suite = loader.loadTestsFromName(tf)
    suite.addTests(mod_suite)

print(f"Total test cases loaded: {suite.countTestCases()}")
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

if not result.wasSuccessful():
    print(f"FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
    sys.exit(1)
else:
    print(f"ALL {suite.countTestCases()} TESTS PASSED WITH 100% SUCCESS!")
    sys.exit(0)
