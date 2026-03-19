---
name: client-onboard
description: Onboarding completo de un cliente nuevo post-venta. /client-onboard "empresa" "plan"
context: fork
disable-model-invocation: false
---
Flujo post-venta para activar un cliente:

1. Crear tenant via API: POST /api/v1/onboarding/start
   - Datos: company_name, admin_email, plan

2. Seed de datos demo: POST /api/v1/onboarding/seed-demo

3. Si el cliente tiene datos existentes:
   - Importar leads via /api/v1/leads/import o /api/v1/crm/import
   - Importar tickets si aplica

4. Configurar módulos según plan y requerimientos del PRD:
   - Activar features correspondientes al plan
   - Configurar territorios si es Enterprise
   - Configurar outreach sequences
   - Configurar automation rules personalizadas

5. Verificar setup:
   - GET /api/v1/tenant/usage — verificar que todo funciona
   - GET /api/v1/dashboard — verificar que hay datos
   - GET /api/v1/onboarding/checklist — verificar pasos completados

6. Reportar al usuario:
   - Tenant creado con ID
   - URL de acceso
   - Credenciales del admin
   - Checklist de onboarding
   - Próximos pasos para el equipo del cliente
