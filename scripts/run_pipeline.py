from backend.service.orchestrator import run_pipeline

result = run_pipeline()
print("=== PIPELINE RESULT ===")
print("Status:", result.get("status"))
print("Cycle ID:", result.get("cycle_id"))
print("Steps completed:", result.get("steps_completed"))
print("Total duration:", result.get("total_duration_s", "N/A"), "s")
if result.get("error"):
    print("Error:", result.get("error"))
