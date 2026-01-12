#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'air_risk.settings')
django.setup()

from reports.models import Report

# Check report 15
report = Report.objects.filter(id=15).first()
if report:
    print(f"Report 15: Status={report.status}, Error={report.error_message or 'None'}")
    if report.file_path:
        print(f"File path: {report.file_path}")
        print(f"File size: {report.file_size}")
else:
    print("Report 15 not found")

# Check report 17
report17 = Report.objects.filter(id=17).first()
if report17:
    print(f"Report 17: Status={report17.status}, Error={report17.error_message or 'None'}")
else:
    print("Report 17 not found")