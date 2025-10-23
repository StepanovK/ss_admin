# db_transfer.py
import datetime
import json
import os
import shutil
import tempfile
import zipfile
from decimal import Decimal
from typing import List, Type, Dict, Any

from peewee import (
    Model,
    ForeignKeyField,
    DateTimeField,
    DateField,
    DoesNotExist,
    IntegrityError
)

# --- Параметры импорта ---
"""
Здесь max_passes — это максимальное число итераций, за которые импорт проходит по всем моделям,
чтобы разрешить зависимости между ними (ForeignKey).
Иными словами — сколько раз мы делаем “проход по всем таблицам”,
пытаясь вставить те записи, которые раньше нельзя было вставить (из-за ещё не загруженных FK).

Пример
Предположим:
- у нас 5 моделей (pending содержит 5 элементов),
- в некоторых из них ссылки на другие (FK).
Тогда len(pending) * 3 = 15, значит максимум 15 проходов:
1. Вставляются независимые таблицы (без FK);
2. В следующем проходе — таблицы, у которых ссылки уже разрешены;
3. И так далее, пока всё не загрузится или лимит не исчерпан.
А max(10, ...) гарантирует, что даже если моделей мало (1–2),
цикл всё равно даст минимум 10 попыток разрешить зависимости (на случай, если есть цепочки вложенных FK).
"""
MIN_PASSES = 10  # Минимальное количество попыток пройти по всем моделям
PASSES_PER_MODEL = 3  # Умножитель для дополнительных попыток при множестве моделей


# ============================================================
# === Утилиты ===============================================
# ============================================================

def _serialize_value(value):
    """Приводит типы Peewee-полей к сериализуемым для JSON."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, datetime.date):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, Decimal):
        return str(value)
    return value


# ============================================================
# === ЭКСПОРТ ===============================================
# ============================================================

def export_models(models: List[Type[Model]], out_dir: str = None) -> str:
    """
    Экспортирует указанные модели в JSON-файлы, затем упаковывает их в zip.
    :param models: список классов peewee.Model
    :param out_dir: директория, куда сохранить zip (по умолчанию cwd)
    :return: путь к архиву .zip
    """
    tmp_dir = tempfile.mkdtemp(prefix='peewee_export_')
    try:
        for model_cls in models:
            filename = f"{model_cls.__name__}.json"
            filepath = os.path.join(tmp_dir, filename)

            fields = model_cls._meta.fields
            rows = []
            for record in model_cls.select().dicts().iterator():
                serialized = {}
                for name, field in fields.items():
                    value = record.get(name)
                    if value is None and isinstance(field, ForeignKeyField):
                        value = record.get(f"{name}_id")
                    serialized[name] = _serialize_value(value)
                rows.append(serialized)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)

        zip_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".zip"
        zip_path = os.path.join(out_dir or os.getcwd(), zip_name)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmp_dir):
                zf.write(os.path.join(tmp_dir, fname), arcname=fname)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return zip_path


# ============================================================
# === ИМПОРТ ================================================
# ============================================================

def import_from_zip(zip_path: str, available_models: List[Type[Model]]) -> Dict[str, Any]:
    """
    Импортирует данные из архива .zip, содержащего JSON-файлы по именам моделей.
    :param zip_path: путь к zip-файлу
    :param available_models: список всех доступных peewee моделей
    :return: словарь с отчётом (inserted, updated, skipped, errors)
    """
    tmp_dir = tempfile.mkdtemp(prefix='peewee_import_')
    result = {"models": {}, "errors": []}

    try:
        # --- Распаковка архива ---
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)
            filelist = zf.namelist()

        # Сопоставление имён файлов с моделями
        model_classes = {cls.__name__: cls for cls in available_models}

        # --- Чтение JSON-файлов ---
        files_data: Dict[str, List[Dict[str, Any]]] = {}
        for fname in filelist:
            if not fname.endswith(".json"):
                continue
            model_name = os.path.splitext(fname)[0]
            path = os.path.join(tmp_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                files_data[model_name] = data
            except Exception as ex:
                result["errors"].append(f"Ошибка чтения {fname}: {ex}")

        # --- Подготовка данных ---
        pending = {}
        for model_name, rows in files_data.items():
            cls = model_classes.get(model_name)
            if not cls:
                result["errors"].append(f"Модель {model_name} не найдена среди доступных, файл пропущен.")
                continue
            pending[model_name] = rows
            result["models"][model_name] = {"inserted": 0, "updated": 0, "skipped": 0}

        # --- Основной импорт (итерационно, с учётом зависимостей) ---
        max_passes = max(MIN_PASSES, len(pending) * PASSES_PER_MODEL)
        for attempt in range(max_passes):
            progress = False
            for model_name, rows in list(pending.items()):
                cls = model_classes.get(model_name)
                if not cls:
                    continue
                fields = cls._meta.fields
                pk_field = cls._meta.primary_key
                pk_name = pk_field.name if pk_field else None
                new_pending = []

                for record in rows:
                    kwargs = {}
                    fk_ok = True
                    for name, field in fields.items():
                        if name not in record:
                            continue
                        value = record[name]
                        if isinstance(field, ForeignKeyField):
                            if value is None:
                                kwargs[f"{name}_id"] = None
                            else:
                                ref_model = field.rel_model
                                try:
                                    ref_model.get(ref_model._meta.primary_key == value)
                                    kwargs[f"{name}_id"] = value
                                except DoesNotExist:
                                    if ref_model.__name__ in pending:
                                        fk_ok = False
                                    else:
                                        fk_ok = False
                        elif isinstance(field, DateTimeField):
                            if value:
                                try:
                                    kwargs[name] = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                except Exception:
                                    try:
                                        kwargs[name] = datetime.datetime.fromisoformat(value)
                                    except Exception:
                                        kwargs[name] = None
                            else:
                                kwargs[name] = None
                        elif isinstance(field, DateField):
                            if value:
                                try:
                                    kwargs[name] = datetime.datetime.strptime(value, '%Y-%m-%d').date()
                                except Exception:
                                    try:
                                        kwargs[name] = datetime.date.fromisoformat(value)
                                    except Exception:
                                        kwargs[name] = None
                            else:
                                kwargs[name] = None
                        else:
                            kwargs[name] = value

                    if not fk_ok:
                        new_pending.append(record)
                        continue

                    # === Определяем стратегию поиска ===
                    instance = None
                    try:
                        # 1️⃣ Есть явный primary_key (например, id или parameter)
                        if pk_field is not None and not pk_field.sequence:
                            pk_val = record.get(pk_name)
                            if pk_val is not None:
                                try:
                                    instance = cls.get(pk_field == pk_val)
                                except DoesNotExist:
                                    instance = None
                                if instance:
                                    changed = False
                                    for k, v in kwargs.items():
                                        if getattr(instance, k) != v:
                                            setattr(instance, k, v)
                                            changed = True
                                    if changed:
                                        instance.save()
                                        result["models"][model_name]["updated"] += 1
                                    else:
                                        result["models"][model_name]["skipped"] += 1
                                    progress = True
                                    continue
                                else:
                                    cls.create(**kwargs)
                                    result["models"][model_name]["inserted"] += 1
                                    progress = True
                                    continue

                        # 2️⃣ Нет явного PK, но есть FK-поля — поиск по ним
                        fk_fields = [f for f, fld in fields.items() if isinstance(fld, ForeignKeyField)]
                        if fk_fields:
                            lookup = {f"{f}_id": record.get(f) for f in fk_fields if record.get(f) is not None}
                            if lookup:
                                try:
                                    instance = cls.get(**lookup)
                                except DoesNotExist:
                                    instance = None
                                except Exception:
                                    instance = None
                            if instance:
                                changed = False
                                for k, v in kwargs.items():
                                    if getattr(instance, k) != v:
                                        setattr(instance, k, v)
                                        changed = True
                                if changed:
                                    instance.save()
                                    result["models"][model_name]["updated"] += 1
                                else:
                                    result["models"][model_name]["skipped"] += 1
                                progress = True
                                continue
                            else:
                                cls.create(**kwargs)
                                result["models"][model_name]["inserted"] += 1
                                progress = True
                                continue

                        # 3️⃣ Нет PK и FK — поиск по всем полям
                        try:
                            instance = cls.get(**kwargs)
                        except DoesNotExist:
                            instance = None
                        except Exception:
                            instance = None
                        if instance:
                            result["models"][model_name]["skipped"] += 1
                        else:
                            cls.create(**kwargs)
                            result["models"][model_name]["inserted"] += 1
                            progress = True

                    except IntegrityError as ie:
                        result["errors"].append(f"IntegrityError в {model_name}: {ie}")
                        new_pending.append(record)
                    except Exception as ex:
                        result["errors"].append(f"Ошибка обработки {model_name}: {ex}")
                        new_pending.append(record)

                pending[model_name] = new_pending

            if not progress:
                break

        # --- Остатки ---
        for model_name, pend in pending.items():
            if pend:
                result["errors"].append(
                    f"Не обработано {len(pend)} записей модели {model_name} (зависимости или ошибки)."
                )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


# ============================================================
# === Пример использования ==================================
# ============================================================

if __name__ == "__main__":
    # from Models.Posts import Post
    # from Models.Users import User
    # from Models.PostsLike import PostsLike
    # from Models.ServiceData import ServiceData
    #
    # # Экспорт:
    # zip_file = export_models([User, Post, PostsLike, ServiceData])
    # print("Создан архив:", zip_file)
    #
    # # Импорт:
    # result = import_from_zip(zip_file, [User, Post, PostsLike, ServiceData])
    # print(json.dumps(result, indent=2, ensure_ascii=False))
    pass
