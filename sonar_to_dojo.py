import requests
import json
import sys
from datetime import datetime, timedelta

# ========================
# CONFIGURACIÓN
# ========================
SONARCLOUD_ORG = ""       # Tu organización
SONARCLOUD_TOKEN = ""     # Token SonarCloud
DOJO_URL = ""             # URL del DefectDojo
DOJO_API_KEY = ""         # Token API DefectDojo
PROJECT_NAME = ""         # Proyecto a verificar

# ========================
# FUNCIONES AUXILIARES
# ========================

def get_sonar_project(name):
    """Verifica si existe un proyecto en SonarCloud"""
    url = f"https://sonarcloud.io/api/projects/search?organization={SONARCLOUD_ORG}&q={name}"
    resp = requests.get(url, auth=(SONARCLOUD_TOKEN, ""))
    if resp.status_code == 200:
        data = resp.json().get("components", [])
        return data[0] if data else None
    else:
        print("❌ Error al conectar con SonarCloud:", resp.text)
        return None


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
        "prod_type": 1  # ID del tipo de producto (ajustar si tu Dojo usa otros)
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
    """Crea un engagement en Dojo con fechas obligatorias"""
    url = f"{DOJO_URL}/api/v2/engagements/"
    headers = {
        "Authorization": f"Token {DOJO_API_KEY}",
        "Content-Type": "application/json"
    }

    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    fecha = datetime.now().time()
    formateo_fecha = fecha.strftime("%H%M%S")

    payload = {
        "name": f"Import Sonarcloud - {formateo_fecha} ",
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
        "test_type": 1,  # ID del tipo de test (1 suele ser 'Manual' o 'Generic')
        "target_start": str(datetime.now().date()),
        "target_end": str(datetime.now().date())
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code in [200, 201]:
        data = resp.json()
        print(f"✅ Test creado para engagement {engagement_id} (ID: {data['id']})")
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
    """Carga las vulnerabilidades a DefectDojo"""
    url = f"{DOJO_URL}/api/v2/findings/"
    headers = {
        "Authorization": f"Token {DOJO_API_KEY}",
        "Content-Type": "application/json"
    }

    # Mapeo entre severidad textual y numérica según DefectDojo
    severity_map = {
        "INFO": "Info",
        "MINOR": "Low",
        "MAJOR": "Medium",
        "CRITICAL": "Critical",
        "BLOCKER": "High"
    }

    numerical_map = {
        "Info": "0",
        "Low": "1",
        "Medium": "2",
        "High": "3",
        "Critical": "4"
    }

    count = 0
    for issue in issues:
        severity = severity_map.get(issue.get("severity", "MAJOR"), "Medium")
        numerical = numerical_map[severity]

        payload = {
            "title": issue["message"],
            "severity": severity,
            "numerical_severity": numerical,
            "description": issue.get("message", "Sin descripción"),
            "test": test_id,
            "found_by": [1],  # ID del tipo de test (1 suele ser 'Manual' o 'Generic')
            "active": True,
            "verified": False
        }

        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        if resp.status_code in [200, 201]:
            count += 1
        else:
            print(f"⚠️ Error al subir vulnerabilidad: {resp.text}")

    print(f"✅ {count} vulnerabilidades subidas a Dojo.")



# ========================
# PROCESO PRINCIPAL
# ========================

print(f"🔍 Verificando proyecto {PROJECT_NAME} en SonarCloud...")
sonar_project = get_sonar_project(PROJECT_NAME)

if not sonar_project:
    print("❌ No existe el proyecto en SonarCloud.")
    sys.exit(1)

print(f"✅ Proyecto SonarCloud encontrado: {sonar_project['name']}")

print(f"🔍 Verificando producto en DefectDojo...")
dojo_product = get_dojo_product(PROJECT_NAME)

if not dojo_product:
    dojo_product = create_dojo_product(PROJECT_NAME)
    if not dojo_product:
        print("❌ No se pudo crear ni obtener el producto en Dojo.")
        sys.exit(1)

product_id = dojo_product["id"]

print("📦 Creando engagement...")
engagement = create_dojo_engagement(product_id, PROJECT_NAME)
if not engagement:
    print("❌ No se pudo crear el engagement en Dojo.")
    sys.exit(1)

engagement_id = engagement["id"]

print("🧪 Creando test en el engagement...")
dojo_test = create_dojo_test(engagement_id, PROJECT_NAME)
if not dojo_test:
    print("❌ No se pudo crear el test en Dojo.")
    sys.exit(1)

test_id = dojo_test["id"]

print("📤 Extrayendo vulnerabilidades de SonarCloud...")
issues = get_sonar_issues(sonar_project["key"])

print("📥 Subiendo vulnerabilidades a DefectDojo...")
upload_to_dojo(test_id, issues)

print("✅ Proceso completado correctamente.")
