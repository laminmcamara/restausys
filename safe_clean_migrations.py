import os

APPS = ["core"]  # Add other app names if needed

for app in APPS:
    path = os.path.join(app, "migrations")
    if os.path.exists(path):
        for f in os.listdir(path):
            if f != "__init__.py" and f.endswith(".py"):
                full_path = os.path.join(path, f)
                print("Deleting:", full_path)
                os.remove(full_path)