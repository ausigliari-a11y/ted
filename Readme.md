# 🛰️ RepoPulse

CLI in Python per scansionare il tuo workspace e controllare lo stato di tutti i repository Git locali in un'unica tabella.

## ✨ Funzionalità
- Scansiona ricorsivamente le cartelle ignorando directory pesanti (`node_modules`, `venv`, `__pycache__`, ecc.).
- Evidenzia file modificati (`M`), file non tracciati (`?`) e commit `ahead` / `behind` rispetto al remote.
- Mostra branch attivo e ultimo commit di ogni progetto.
- Supporta `--push-ahead` per sincronizzare al volo i repository puliti con commit pronti.

## 🚀 Uso
```bash
pip install -r requirements.txt
python repopulse.py ~/Progetti --depth 3
python repopulse.py ~/Progetti --push-ahead
