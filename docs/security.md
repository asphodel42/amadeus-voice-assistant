# Модель безпеки Amadeus

## Огляд

Amadeus використовує модель **Zero-Trust** для всіх операцій.
Жодна дія не виконується без явної авторизації.

## STRIDE Threat Model

| Загроза | Компонент | Сценарій | Захід |
|---------|-----------|----------|-------|
| **Spoofing** | Wake Word | Відтворення записаного голосу | Push-to-Talk fallback; Voice fingerprinting (майбутнє) |
| **Tampering** | Plugin Loader | Модифікація скрипта навички | Ed25519 підписи; Hash verification |
| **Repudiation** | Executor | "Я не видаляв файл" | Append-only audit log з hash chain |
| **Info Disclosure** | Logs | Витік чутливих даних | Redaction; Local-only storage |
| **DoS** | Planner | Infinite loop через malformed input | Timeouts; Resource limits |
| **EoP** | Plugins | Доступ до системних файлів | Capability manifests; Rust sandbox |

## Capability System

### Manifest Schema

```json
{
  "skill_id": "com.amadeus.filesystem",
  "version": "1.0.0",
  "publisher_id": "trusted-publisher",
  "capabilities": [
    {
      "scope": "fs.read",
      "constraints": {
        "allowed_paths": ["~/Documents", "~/Downloads"]
      }
    },
    {
      "scope": "fs.write",
      "risk": "HIGH",
      "constraints": {
        "max_size_mb": 10
      }
    }
  ],
  "signature": "base64-encoded-signature"
}
```

### Scopes

| Scope | Опис | Risk Level |
|-------|------|------------|
| `fs.read` | Читання файлів | SAFE |
| `fs.write` | Запис файлів | HIGH |
| `fs.delete` | Видалення файлів | DESTRUCTIVE |
| `fs.create` | Створення файлів | HIGH |
| `process.launch` | Запуск додатків | SAFE* |
| `net.browser` | Відкриття URL | MEDIUM |
| `system.info` | Системна інформація | SAFE |

*Тільки з білого списку

## Рівні ризику

### SAFE
- Не потребує підтвердження
- Приклади: list_dir, system_info, read_file

### MEDIUM
- Інформаційне попередження
- Приклади: open_url (non-HTTPS)

### HIGH
- Потребує Yes/No підтвердження
- Приклади: create_file, write_file

### DESTRUCTIVE
- Потребує typed confirmation
- Приклади: delete_file, overwrite_file
- Користувач вводить: "DELETE filename"

## Enforcement Points

### 1. Planning Time
```python
# Planner перевіряє capability scope
if not has_capability(CapabilityScope.FS_DELETE):
    return denied_action("Missing fs.delete capability")
```

### 2. Policy Evaluation
```python
# PolicyEngine оцінює ризик
decision = policy_engine.evaluate(plan, capabilities)
if decision.requires_confirmation:
    return await_confirmation(decision.confirmation_type)
```

### 3. Pre-Execution
```python
# Validator перевіряє перед виконанням
if is_blocked_path(action.args["path"]):
    return ExecutionResult(status=DENIED)
```

## Audit Log

### Event Structure
```python
AuditEvent(
    event_id="uuid",
    timestamp="2024-01-15T10:30:00Z",
    event_type="execution",
    actor="user",
    command_request=CommandRequest(...),
    plan=ActionPlan(...),
    result=ExecutionResult(...),
    previous_hash="sha256-of-previous-event"
)
```

### Hash Chain
Кожна подія містить хеш попередньої:
```
Event1 → hash1
Event2 → hash2 = SHA256(Event2 + hash1)
Event3 → hash3 = SHA256(Event3 + hash2)
```

### Integrity Verification
```python
audit.verify_integrity()  # True/False
```

## Blocked Paths

За замовчуванням заблоковані:
- `/` (root)
- `/etc`, `/usr`, `/bin`, `/sbin`, `/boot`
- `C:\Windows`, `C:\Windows\System32`
- `C:\Program Files`, `C:\Program Files (x86)`

## Allowed Directories

За замовчуванням дозволені:
- `~/Documents`
- `~/Downloads`
- `~/Desktop`

Можна налаштувати через API:
```python
os_adapter.add_allowed_directory("~/Projects")
```

## Plugin Signing

### Workflow
1. Розробник підписує manifest приватним ключем
2. Публічний ключ додається до trust store
3. При завантаженні перевіряється підпис
4. Unsigned plugins блокуються (крім dev mode)

### Implementation
```python
signature_port.verify_manifest(manifest)  # True/False
```

## Best Practices

1. **Мінімальні привілеї**: Запитуйте тільки необхідні capabilities
2. **Explicit confirmation**: Для будь-якої деструктивної дії
3. **Dry run first**: Тестуйте плани без виконання
4. **Audit review**: Періодично перевіряйте логи
5. **Update trust store**: Видаляйте скомпрометовані ключі
