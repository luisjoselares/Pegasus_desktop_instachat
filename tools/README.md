# Pegasus Lab

Herramienta de simulación visual para el motor de IA y la lógica de mensajes de Pegasus.

## Uso

Desde la raíz del proyecto (`c:\Users\Luis\Documents\Pegasus_desktop_instachat`):

```powershell
.\venv\Scripts\python.exe tools\pegasus_lab.py
```

## Qué prueba

- Message batching con buffer de 4 segundos
- Time context (`CONTINUOUS`, `RE_ENCOUNTER`, `NEW_SESSION`)
- Handoff simulado al detectar WhatsApp en la respuesta
- Modo manual visual cuando ocurre un handoff
- Stress test de cola y cambio de rol en BD

## Paneles

- Panel izquierdo: chat simulado
- Panel derecho: log de auditoría + controles

## Notas

- El archivo añade la raíz del proyecto a `sys.path` para poder importar `core` y `services` desde `tools/`.
- Está diseñado para ejecutarse sin conexión a Instagram.
