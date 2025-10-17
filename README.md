# sonar_to_dojo
Este script en python se encarga de llevar las vulnerabilidades de SonarCloud a Defectdojo.

El script valida el proyecto en SonarCloud, asegura la existencia del Producto en Dojo, crea un Engagement y un Test, y registra cada vulnerabilidad como Finding mapeando severidades al estándar de Dojo. Quedó listo para pipeline CI/CD con manejo de errores y trazabilidad paso a paso.
