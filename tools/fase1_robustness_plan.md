# Fase 1 - Plan de Robustez

## Objetivo
Preparar la fase inicial de robustez mediante diagnóstico, definición de criterios y checklist de casos adversos.

## Acciones implementadas
- Se añadió un checklist de robustez en `tools/mass_tester.py`.
- El runner ahora puede imprimir y guardar esta checklist como un artefacto de Fase 1.

## Checklist de Fase 1
1. F1-01: Inputs parciales y mal formateados
   - Probar mensajes con datos incompletos, oraciones fragmentadas y formatos no estructurados.
2. F1-02: Campos de perfil vacíos
   - Validar que el bot responda correctamente cuando faltan location, website, inventory o exchange_rate.
3. F1-03: Peticiones fuera de alcance
   - Verificar que el bot rechace consultas médicas, legales o políticas y derive de forma segura.
4. F1-04: Intentos de forzar identidad o rol
   - Asegurar que el bot mantenga su identidad de marca y no acepte cambios de personaje.
5. F1-05: Seguridad de prompt injection
   - Detectar y manejar mensajes diseñados para alterar la lógica del bot o la construcción del prompt.
6. F1-06: No inventar datos
   - Asegurarse de no generar precios, direcciones o información no disponible en la ficha del negocio.

## Próximos pasos
- Fase 2: Extender el suite de pruebas con casos adversos concretos.
- Fase 3: Fortalecer los guardrails en `core/ai_engine.py`.
- Fase 4: Ejecutar pruebas y ajustar según resultados.
