import sys
sys.path.insert(0, 'src')
from marswalk.core.environment_science_experiment import EnvironmentScienceExperimentRunner

runner = EnvironmentScienceExperimentRunner()
results = runner.run_all_experiments()

print(f"Executed {len(results)} scientific validation experiments:")
for res in results:
    print(f"\n[{res.experiment_id}] {res.title}")
    print(f"  Sample size: {res.sample_size}")
    print(f"  Key finding: {list(res.quantitative_findings.items())[:2]}")
    print(f"  Conclusion: {res.scientific_conclusion[:100]}...")
