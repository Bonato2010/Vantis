"""
VANTIS / IAS - Executor e Auditor Automatizado de Testes
Executa as baterias de testes (Fase 1 a Fase 7 + Services), computa tempos,
classifica resultados e gera relatório operacional sem alterar o código do IDE.
"""
import os
import sys
import time
import unittest
import importlib
from pathlib import Path

# Configura ambiente
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

TEST_FILES = [
    "test_services.py",
    "test_fase1_foundation.py",
    "test_fase2_orchestration.py",
    "test_fase3_multichannel.py",
    "test_fase4_discovery_portal1.py",
    "test_fase5_audiovisual.py",
    "test_fase6_distribution.py",
    "test_fase7_dashboard.py",
    "test_fase8_vantis_pipeline.py",
    "test_fase9_agent_architecture.py",
    "test_fase10_audiovisual_pipeline.py",
    "test_fase11_pilot_channels_and_dashboard.py",
    "test_fase12_deployment_and_editorial_training.py",
    "test_fase13_massive_audiovisual_learning.py",
    "test_fase14_real_learning_and_zero_simulation.py",
    "test_fase15_real_shorts_physical_pilot.py",
    "test_fase15_1_forensic_audit.py",
    "test_fase16_pilot_100_shorts.py",
    "test_fase17_scale_readiness.py",
    "test_fase18_learning_and_benchmark.py",
    "test_fase19_drive_first_and_calibration.py",
    "test_fase20_operational_e2e.py",
    "test_fase21_editorial_production.py",
    "test_fase22_audiovisual_rendering.py",
    "test_fase23_production_review_flow.py",
    "test_fase24_asset_intelligence_and_scripts.py",
    "test_fase25_asset_acquisition_and_render.py",
    "test_fase26_multichannel_validation.py",
    "test_fase27_brand_identity_and_youtube_registry.py"
]

def run_test_suite():
    tests_dir = BASE_DIR / "tests"
    print("=" * 70)
    print("        VANTIS / IAS - BATERIA AUTOMATIZADA DE TESTES OPERACIONAIS        ")
    print("=" * 70)

    overall_results = {
        "total_files": len(TEST_FILES),
        "executed_files": 0,
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "files_summary": []
    }

    start_total_time = time.time()

    for test_file in TEST_FILES:
        file_path = tests_dir / test_file
        if not file_path.exists():
            print(f"\n[AVISO] Arquivo não encontrado: {test_file}")
            overall_results["files_summary"].append({
                "file": test_file,
                "status": "NOT_FOUND",
                "tests": 0, "passed": 0, "failed": 0, "errors": 0
            })
            continue

        print(f"\n>>> Executando: {test_file} ...")
        t_start = time.time()
        
        # Carrega e executa suite
        module_name = f"tests.{test_file.replace('.py', '')}"
        loader = unittest.TestLoader()
        try:
            suite = loader.loadTestsFromName(module_name)
        except Exception as load_err:
            print(f"  [ERRO DE CARREGAMENTO]: {load_err}")
            overall_results["files_summary"].append({
                "file": test_file,
                "status": "LOAD_ERROR",
                "error": str(load_err)
            })
            continue

        runner = unittest.TextTestRunner(verbosity=1)
        res = runner.run(suite)
        t_dur = time.time() - t_start

        tests_run = res.testsRun
        failures_count = len(res.failures)
        errors_count = len(res.errors)
        skipped_count = len(res.skipped)
        passed_count = tests_run - (failures_count + errors_count + skipped_count)

        status_str = "APROVADO" if (failures_count == 0 and errors_count == 0) else "REPROVADO"
        print(f"  Status: {status_str} | Total: {tests_run} | Passou: {passed_count} | Falhou: {failures_count} | Erros: {errors_count} ({t_dur:.2f}s)")

        # Detalha falhas se houver
        if res.failures:
            print("  [DETALHE DAS FALHAS]:")
            for tc, err in res.failures:
                print(f"    - {tc.id()}: {err.splitlines()[-1]}")
        if res.errors:
            print("  [DETALHE DOS ERROS]:")
            for tc, err in res.errors:
                print(f"    - {tc.id()}: {err.splitlines()[-1]}")

        overall_results["executed_files"] += 1
        overall_results["total_tests"] += tests_run
        overall_results["passed"] += passed_count
        overall_results["failed"] += failures_count
        overall_results["errors"] += errors_count
        overall_results["skipped"] += skipped_count
        overall_results["files_summary"].append({
            "file": test_file,
            "status": status_str,
            "duration_sec": round(t_dur, 2),
            "tests_run": tests_run,
            "passed": passed_count,
            "failed": failures_count,
            "errors": errors_count,
            "skipped": skipped_count
        })

    total_duration = time.time() - start_total_time

    print("\n" + "=" * 70)
    print("                    RESUMO CONSOLIDADO DOS TESTES                  ")
    print("=" * 70)
    print(f"Arquivos Executados : {overall_results['executed_files']} / {overall_results['total_files']}")
    print(f"Total de Testes     : {overall_results['total_tests']}")
    print(f"Aprovados           : {overall_results['passed']}")
    print(f"Reprovados (Falhas) : {overall_results['failed']}")
    print(f"Erros de Execução   : {overall_results['errors']}")
    print(f"Ignorados (Skipped) : {overall_results['skipped']}")
    print(f"Tempo Total         : {total_duration:.2f} segundos")
    if overall_results["total_tests"] > 0:
        taxa_sucesso = (overall_results["passed"] / overall_results["total_tests"]) * 100
        print(f"Taxa de Sucesso     : {taxa_sucesso:.1f}%")
    print("=" * 70)

if __name__ == "__main__":
    run_test_suite()
