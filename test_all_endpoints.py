"""
Comprehensive test for all API endpoints to verify commit_message handling
Tests that commit_message doesn't interfere with config validation
"""
import requests
import json
import time

BASE_URL = "http://localhost:8099/api"
API_KEY = ""  # Add your API key if needed

def test_create_helper():
    """Test helper creation with commit_message"""
    print("\n=== Testing Helper Creation ===")
    response = requests.post(
        f"{BASE_URL}/helpers/create",
        json={
            "type": "input_boolean",
            "config": {
                "name": "test_comprehensive_helper",
                "icon": "mdi:test-tube"
            },
            "commit_message": "Test helper: comprehensive test for commit_message handling"
        },
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Helper creation failed: {response.text}"
    return response.json()

def test_create_automation():
    """Test automation creation with commit_message"""
    print("\n=== Testing Automation Creation ===")
    response = requests.post(
        f"{BASE_URL}/automations/create",
        json={
            "id": "test_comprehensive_automation",
            "alias": "Test Comprehensive Automation",
            "description": "Test automation for commit_message",
            "trigger": [{"platform": "state", "entity_id": "input_boolean.test_comprehensive_helper", "to": "on"}],
            "action": [{"service": "logbook.log", "data": {"name": "Test", "message": "Automation triggered"}}],
            "mode": "single",
            "commit_message": "Test automation: comprehensive test for commit_message handling"
        },
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Automation creation failed: {response.text}"
    return response.json()

def test_create_script():
    """Test script creation with commit_message"""
    print("\n=== Testing Script Creation ===")
    # Test Format 1: Dictionary with script_id as key
    response = requests.post(
        f"{BASE_URL}/scripts/create",
        json={
            "test_comprehensive_script": {
                "alias": "Test Comprehensive Script",
                "sequence": [{"service": "logbook.log", "data": {"name": "Test", "message": "Script executed"}}],
                "mode": "single",
                "icon": "mdi:test-tube"
            },
            "commit_message": "Test script: comprehensive test for commit_message handling"
        },
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Script creation failed: {response.text}"
    return response.json()

def test_create_theme():
    """Test theme creation with commit_message"""
    print("\n=== Testing Theme Creation ===")
    response = requests.post(
        f"{BASE_URL}/themes/create",
        json={
            "theme_name": "test_comprehensive_theme",
            "theme_config": {
                "primary-color": "#ff0000",
                "accent-color": "#00ff00"
            },
            "commit_message": "Test theme: comprehensive test for commit_message handling"
        },
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Theme creation failed: {response.text}"
    return response.json()

def test_delete_helper():
    """Test helper deletion with commit_message"""
    print("\n=== Testing Helper Deletion ===")
    response = requests.delete(
        f"{BASE_URL}/helpers/delete/input_boolean.test_comprehensive_helper",
        params={"commit_message": "Test: Delete helper with custom commit message"},
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Helper deletion failed: {response.text}"
    return response.json()

def test_delete_automation():
    """Test automation deletion with commit_message"""
    print("\n=== Testing Automation Deletion ===")
    response = requests.delete(
        f"{BASE_URL}/automations/delete/test_comprehensive_automation",
        params={"commit_message": "Test: Delete automation with custom commit message"},
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Automation deletion failed: {response.text}"
    return response.json()

def test_delete_script():
    """Test script deletion with commit_message"""
    print("\n=== Testing Script Deletion ===")
    response = requests.delete(
        f"{BASE_URL}/scripts/delete/test_comprehensive_script",
        params={"commit_message": "Test: Delete script with custom commit message"},
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Script deletion failed: {response.text}"
    return response.json()

def test_delete_theme():
    """Test theme deletion with commit_message"""
    print("\n=== Testing Theme Deletion ===")
    response = requests.delete(
        f"{BASE_URL}/themes/delete",
        params={
            "theme_name": "test_comprehensive_theme",
            "commit_message": "Test: Delete theme with custom commit message"
        },
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, f"Theme deletion failed: {response.text}"
    return response.json()

def test_git_history():
    """Test git history to verify commit messages"""
    print("\n=== Testing Git History ===")
    response = requests.get(
        f"{BASE_URL}/backup/history",
        params={"limit": 10},
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    history = response.json()
    print(f"Recent commits:")
    for commit in history.get("commits", [])[:5]:
        print(f"  - {commit.get('hash', '')[:8]}: {commit.get('message', '')}")
    return history

def test_find_dead_entities():
    """Test finding dead entities in Entity Registry"""
    print("\n=== Testing Find Dead Entities ===")
    response = requests.get(
        f"{BASE_URL}/registries/entities/dead",
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    assert response.status_code == 200, f"Find dead entities failed: {response.text}"
    assert result.get("success") == True, "Response should indicate success"
    assert "dead_automations" in result, "Response should contain dead_automations"
    assert "dead_scripts" in result, "Response should contain dead_scripts"
    assert "summary" in result, "Response should contain summary"
    
    summary = result.get("summary", {})
    print(f"\nSummary:")
    print(f"  - Total registry automations: {summary.get('total_registry_automations', 0)}")
    print(f"  - Total registry scripts: {summary.get('total_registry_scripts', 0)}")
    print(f"  - Total YAML automations: {summary.get('total_yaml_automations', 0)}")
    print(f"  - Total YAML scripts: {summary.get('total_yaml_scripts', 0)}")
    print(f"  - Dead automations: {summary.get('dead_automations_count', 0)}")
    print(f"  - Dead scripts: {summary.get('dead_scripts_count', 0)}")
    print(f"  - Total dead: {summary.get('total_dead', 0)}")
    
    return result

if __name__ == "__main__":
    print("Starting comprehensive API endpoint tests...")
    print("=" * 60)
    
    try:
        # Test creation endpoints
        test_create_helper()
        time.sleep(1)
        test_create_automation()
        time.sleep(1)
        test_create_script()
        time.sleep(1)
        test_create_theme()
        time.sleep(1)
        
        # Test deletion endpoints
        test_delete_script()
        time.sleep(1)
        test_delete_automation()
        time.sleep(1)
        test_delete_helper()
        time.sleep(1)
        test_delete_theme()
        time.sleep(1)
        
        # Verify git history
        test_git_history()
        time.sleep(1)
        
        # Test registry endpoints
        test_find_dead_entities()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)




