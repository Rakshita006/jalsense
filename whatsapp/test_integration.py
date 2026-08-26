from whatsapp_service.analysis_service import analyze_field, format_report_hi

result = analyze_field("Chitrakoot", "rice")
print(result)

print("\n--- Formatted report ---\n")
print(format_report_hi(result))