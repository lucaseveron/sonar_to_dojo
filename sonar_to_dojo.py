import requests
import json
import sys
from datetime import datetime, timedelta

# ========================
# CONFIGURACIÓN
# ========================
SONARCLOUD_ORG = "test-112"       # Tu organización en SonarCloud
SONARCLOUD_TOKEN = "986b75ac934b215a6e73ce75ff9b813b6098681e"     # Token de SonarCloud
DOJO_URL = "http://98.91.200.231:8080"             # URL base del DefectDojo (sin barra final)
DOJO_API_KEY = "1462bafcc0f69b1a840faa3c4f634b60ca0f64a0"         # Token API de DefectDojo

# ========================
# FUNCIONES AUXILIARES
# ========================

def get_all_sonar_projects():
    projects = []
    page = 1
    while True:
        url = f"https://sonarcloud.io/api/projects/search?organization={SONARCLOUD_ORG}&p={page}"
        resp = requests.get(url, auth=(SONARCLOUD_TOKEN, ""))
        if resp.status_code != 200:
            print("❌ Error al conectar con SonarCloud:", resp.text)
            break
        data = resp.json()
        components = data.get("components", [])
        projects.extend(components)
        if len(components) < 100:
            break
        page += 1
    return projects

def get_dojo_product(name):
    url = f"{DOJO_URL}/api/v2/products/?name={name}"
    headers = {"Authorization": f"Token {DOJO_API_KEY}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        results = resp.json().get("results", [])
        return results[0] if results else None
    return None

def create_dojo_product(name):
    url = f"{DOJO_URL}/api/v2/products/"
    headers = {"Authorization": f"Token {DOJO_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "name": name,
        "description": f"Proyecto importado automáticamente desde SonarCloud ({name})",
        "prod_type": 1
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code in [200, 201]:
        data = resp.json()
        return data
    return None

def create_dojo_engagement(product_id, name):
    url = f"{DOJO_URL}/api/v2/engagements/"
    headers = {"Authorization": f"Token {DOJO_API_KEY}", "Content-Type": "application/json"}
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    hora = datetime.now().strftime("%H%M%S")
    payload = {
        "name": f"Import SonarCloud - {hora}",
        "product": product_id,
        "status": "In Progress",
        "target_start": str(today),
        "target_end": str(next_week),
        "engagement_type": "CI/CD",
        "description": f"Engagement creado automáticamente desde SonarCloud para {name}"
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code in [200, 201]:
        data = resp.json()
        return data
    return None

def create_dojo_test(engagement_id, name):
    url = f"{DOJO_URL}/api/v2/tests/"
    headers = {"Authorization": f"Token {DOJO_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "title": f"Análisis SonarCloud - {name}",
        "engagement": engagement_id,
        "test_type": 1,
        "target_start": str(datetime.now().date()),
        "target_end": str(datetime.now().date())
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code in [200, 201]:
        data = resp.json()
        return data
    return None

def get_sonar_issues(project_key):
    url = f"https://sonarcloud.io/api/issues/search?componentKeys={project_key}&types=VULNERABILITY"
    resp = requests.get(url, auth=(SONARCLOUD_TOKEN, ""))
    if resp.status_code == 200:
        return resp.json().get("issues", [])
    return []

# ========================
# SUBIDA A DEFECTDOJO
# ========================

def upload_to_dojo(test_id, issues):
    url = f"{DOJO_URL}/api/v2/findings/"
    headers = {"Authorization": f"Token {DOJO_API_KEY}", "Content-Type": "application/json"}

    severity_map = {
        "INFO": ("Info", "0"),
        "MINOR": ("Low", "1"),
        "MAJOR": ("Medium", "2"),
        "BLOCKER": ("High", "3"),
        "CRITICAL": ("Critical", "4")
    }

    uploaded = 0
    for issue in issues:
        sev_tuple = severity_map.get(issue.get("severity", "MAJOR"), ("Medium", "2"))
        severity, numerical = sev_tuple

        # Mapeo de archivo, línea y key
        file_path = issue.get("component", "Desconocido")
        line = issue.get("line", "N/A")
        key = issue.get("key", "N/A")

        description = f"{issue.get('message','Sin descripción')}\n\nFile: {file_path}\nLine: {line}\nKey: {key}"

        payload = {
            "title": issue["message"],
            "severity": severity,
            "numerical_severity": numerical,
            "description": description,
            "test": test_id,
            "found_by": [1],
            "active": True,
            "verified": False
        }

        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        if resp.status_code in [200, 201]:
            uploaded += 1
        else:
            print(f"⚠️ Error al subir vulnerabilidad: {resp.text}")

    print(f"✅ {uploaded} vulnerabilidades subidas a Dojo.")

# ========================
# PROCESO PRINCIPAL
# ========================

projects = get_all_sonar_projects()
if not projects:
    print("❌ No se encontraron proyectos en SonarCloud.")
    sys.exit(1)

for project in projects:
    name = project["name"]
    key = project["key"]

    dojo_product = get_dojo_product(name)
    if not dojo_product:
        dojo_product = create_dojo_product(name)
        if not dojo_product:
            continue

    product_id = dojo_product["id"]

    engagement = create_dojo_engagement(product_id, name)
    if not engagement:
        continue

    test = create_dojo_test(engagement["id"], name)
    if not test:
        continue

    issues = get_sonar_issues(key)
    if not issues:
        continue

    upload_to_dojo(test["id"], issues)

print("\n✅ Proceso finalizado para todos los proyectos.")
