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
    """Obtiene todos los proyectos de la organización en SonarCloud"""
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

        if len(components) < 100:  # Última página
            break
        page += 1

    print(f"📊 Total de proyectos encontrados en SonarCloud: {len(projects)}")
    return projects


def get_dojo_product(name):
    """Verifica si existe un producto en DefectDojo"""
    url = f"{DOJO_URL}/api/v2/products/?name={name}"
    headers = {"Authorization": f"Token {DOJO_API_KEY}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        results = resp.json().get("results", [])
        return results[0] if results else None
    else:
        print("❌ Error al conectar con DefectDojo:", resp.text)
        return None


def create_dojo_product(name):
    """Crea un producto si no existe"""
    url = f"{DOJO_URL}/api/v2/products/"
    headers = {
        "Authorization": f"Token {DOJO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "description": f"Proyecto importado automáticamente desde SonarCloud ({name})",
        "prod_type": 1
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code in [200, 201]:
        data = resp.json()
        print(f"✅ Producto creado: {name} (ID: {data['id']})")
        return data
    else:
        print(f"❌ Error al crear producto ({resp.status_code}): {resp.text}")
        return None


def create_dojo_engagement(product_id, name):
    """Crea un engagement en DefectDojo"""
    url = f"{DOJO_URL}/api/v2/engagements/"
    headers = {
        "Authorization": f"Token {DOJO_API_KEY}",
        "Content-Type": "application/json"
    }
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
        print(f"✅ Engagement creado para {name} (ID: {data['id']})")
        return data
    else:
        print(f"❌ Error al crear engagement ({resp.status_code}): {resp.text}")
        return None


def create_dojo_test(engagement_id, name):
    """Crea un test dentro del engagement"""
    url = f"{DOJO_URL}/api/v2/tests/"
    headers = {
        "Authorization": f"Token {DOJO_API_KEY}",
        "Content-Type": "application/json"
    }

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
        print(f"✅ Test creado (ID: {data['id']})")
        return data
    else:
        print(f"❌ Error al crear test ({resp.status_code}): {resp.text}")
        return None


def get_sonar_issues(project_key):
    """Obtiene vulnerabilidades desde SonarCloud"""
    url = f"https://sonarcloud.io/api/issues/search?componentKeys={project_key}&types=VULNERABILITY"
    resp = requests.get(url, auth=(SONARCLOUD_TOKEN, ""))
    if resp.status_code == 200:
        return resp.json().get("issues", [])
    else:
        print("❌ Error obteniendo vulnerabilidades:", resp.text)
        return []


def upload_to_dojo(test_id, issues):
    """Carga vulnerabilidades a DefectDojo"""
    url = f"{DOJO_URL}/api/v2/findings/"
    headers = {
        "Authorization": f"Token {DOJO_API_KEY}",
        "Content-Type": "application/json"
    }

    severity_map = {
        "INFO": "Info",
        "MINOR": "Low",
        "MAJOR": "Medium",
        "CRITICAL": "Critical",
        "BLOCKER": "High"
    }

    uploaded = 0
    for issue in issues:
        severity = severity_map.get(issue.get("severity", "MAJOR"), "Medium")

        payload = {
            "title": issue["message"],
            "severity": severity,
            "description": issue.get("message", "Sin descripción"),
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

print("🚀 Iniciando sincronización SonarCloud → DefectDojo...\n")
projects = get_all_sonar_projects()

if not projects:
    print("❌ No se encontraron proyectos en SonarCloud.")
    sys.exit(1)

for project in projects:
    name = project["name"]
    key = project["key"]

    print(f"\n🔍 Procesando proyecto: {name}")

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
        print("ℹ️ No hay vulnerabilidades para este proyecto.")
        continue

    upload_to_dojo(test["id"], issues)

print("\n✅ Proceso finalizado para todos los proyectos.")
