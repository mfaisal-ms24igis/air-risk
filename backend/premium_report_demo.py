#!/usr/bin/env python3
"""
Demonstrate Premium Report Generation and Monitoring
"""

import requests
import time
import json

BASE_URL = 'http://127.0.0.1:8000'

def main():
    print("🎯 PREMIUM REPORT DEMONSTRATION")
    print("=" * 50)

    # Login as premium user
    print("\n🔐 Logging in as premium user...")
    login_response = requests.post(f'{BASE_URL}/api/v1/auth/login/', json={
        'username': 'premium_test',
        'password': 'testpass123'
    })

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return

    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    print("✅ Successfully authenticated as premium user")

    # Check existing reports
    print("\n📋 Checking existing reports...")
    reports_response = requests.get(f'{BASE_URL}/api/v1/exposure/reports/', headers=headers)
    reports_data = reports_response.json()
    print(f"📊 Total reports: {reports_data['count']}")

    if reports_data['count'] > 0:
        print("📄 Recent reports:")
        for report in reports_data['reports'][:3]:
            print(f"   • ID: {report['id']}, Status: {report['status']}, Type: {report['type']}")

    # Create a new premium report
    print("\n📝 Creating new premium location report...")
    print("📍 Location: Lahore, Pakistan (31.5204°N, 74.3587°E)")
    print("📅 Date Range: Dec 1-15, 2025")
    print("🎯 Radius: 5km")
    print("🤖 AI Insights: Enabled")

    report_response = requests.post(f'{BASE_URL}/api/v1/exposure/reports/location/',
        headers=headers,
        json={
            'lat': 31.5204,
            'lng': 74.3587,
            'radius_km': 5.0,
            'start_date': '2025-12-01',
            'end_date': '2025-12-15',
            'include_ai': True
        }
    )

    if report_response.status_code != 202:
        print(f"❌ Failed to create report: {report_response.status_code}")
        print(f"Response: {report_response.text}")
        return

    report_data = report_response.json()
    report_id = report_data['report_id']
    poll_url = report_data['poll_url']

    print("\n✅ Premium report creation initiated!")
    print(f"📊 Report ID: {report_id}")
    print(f"⏱️  Status: {report_data['status']}")
    print(f"🎯 Poll URL: {poll_url}")
    print(f"⏳ Estimated time: {report_data['estimated_time_seconds']} seconds")
    print(f"💎 Tier: {report_data['tier']}")
    print(f"🤖 AI Insights: {report_data['include_ai']}")

    # Poll for completion
    print("\n🔄 Monitoring report generation progress...")
    max_attempts = 15  # 15 attempts = ~30 seconds
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        progress = f"[{attempt}/{max_attempts}]"
        time.sleep(2)  # Wait 2 seconds between polls

        status_response = requests.get(BASE_URL + poll_url, headers=headers)
        if status_response.status_code == 200:
            status_data = status_response.json()
            current_status = status_data.get('status')

            if current_status == 'processing':
                print(f"⏳ {progress} Status: {current_status} - Report generation in progress...")
            elif current_status == 'completed':
                print(f"\n🎉 {progress} REPORT COMPLETED!")
                print("\n" + "=" * 60)
                print("📄 FINAL PREMIUM REPORT DETAILS")
                print("=" * 60)

                # Display the complete report data
                print(json.dumps(status_data, indent=2))

                # Extract key information
                if 'download_url' in status_data:
                    print(f"\n📥 DOWNLOAD LINK: {status_data['download_url']}")
                    print("💡 The PDF report is ready for download!")

                if 'file_size_kb' in status_data:
                    print(f"📏 File Size: {status_data['file_size_kb']} KB")

                if 'tier' in status_data:
                    print(f"💎 Tier: {status_data['tier']}")

                if 'include_ai' in status_data:
                    ai_status = "✅ Enabled" if status_data['include_ai'] else "❌ Disabled"
                    print(f"🤖 AI Insights: {ai_status}")

                print("\n🎊 Premium report generation successful!")
                return

            elif current_status == 'failed':
                error_msg = status_data.get('error_message', 'Unknown error')
                print(f"\n❌ {progress} Report generation failed: {error_msg}")
                return
        else:
            print(f"⚠️  {progress} HTTP {status_response.status_code} - Unable to check status")

    # Timeout reached
    print(f"\n⏰ Report still processing after {max_attempts * 2} seconds")
    print("💡 The report generation continues in the background")
    print(f"🔗 You can check the status later using: {poll_url}")
    print("\n💭 Premium reports typically take 30-60 seconds to generate due to:")
    print("   • AI-powered health recommendations")
    print("   • Advanced data analysis")
    print("   • High-quality PDF formatting")
    print("   • Comprehensive air quality insights")

if __name__ == "__main__":
    main()